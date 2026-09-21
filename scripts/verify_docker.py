"""Build both recipes, test two fresh containers, and export Lab 3 evidence."""
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports/lab3'


def command(*args, log=None):
    if log:
        with (REPORTS / log).open('w', encoding='utf-8') as stream:
            result = subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f'{args[0]} failed; see {REPORTS / log}')
        return ''
    return subprocess.check_output(args, cwd=ROOT, text=True, encoding='utf-8').strip()


def wait_for_health():
    for _ in range(90):
        try:
            if requests.get('http://127.0.0.1:8002/health', timeout=3).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError('Container failed readiness; inspect docker logs')


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    print('Building final multi-stage image (cached dependencies)...', flush=True)
    command('docker', 'build', '--progress', 'plain', '-t', 'food11-api:latest', '.', log='build-multi.txt')
    print('Building single-stage comparison...', flush=True)
    command('docker', 'build', '--progress', 'plain', '-f', 'Dockerfile.single', '-t', 'food11-api:single', '.', log='build-single.txt')
    images = []
    for tag, label in [('food11-api:latest', 'multi'), ('food11-api:single', 'single')]:
        details = json.loads(command('docker', 'image', 'inspect', tag))[0]
        images.append({'tag': tag, 'id': details['Id'], 'bytes': details['Size'],
                       'platform': details['Os'] + '/' + details['Architecture']})
        command('docker', 'history', '--no-trunc', '--format', '{{json .}}', tag, log=f'history-{label}.txt')
    (REPORTS / 'docker-images.json').write_text(json.dumps(images, indent=2), encoding='utf-8')
    image_id = images[0]['id']
    layout = command('docker', 'run', '--rm', '--entrypoint', 'python', image_id,
                     '-c', "import json,sys; from pathlib import Path; excluded=['data','mlruns','mlartifacts','mlflow.db','.git']; assert all(not (Path('/app')/p).exists() for p in excluded); print(json.dumps({'platform':sys.platform,'excluded_paths_absent':excluded}))")
    (REPORTS / 'image-content-check.json').write_text(layout + '\n', encoding='utf-8')
    containers = []
    for name, label in [('food11-api-lab3-first', 'first'), ('food11-api', 'restarted')]:
        print(f'Starting fresh container {name}...', flush=True)
        container_id = command('docker', 'run', '-d', '--name', name,
                               '-p', '127.0.0.1:8002:8000', '-e',
                               'MLFLOW_TRACKING_URI=http://host.docker.internal:5002', image_id)
        try:
            wait_for_health()
            command(sys.executable, 'scripts/test_serving.py', '--url', 'http://127.0.0.1:8002',
                    '--output', f'reports/lab3/container-{label}.json')
        finally:
            command('docker', 'logs', name, log=f'container-{label}.log')
        details = json.loads(command('docker', 'inspect', name))[0]
        assert not details['Mounts'], 'Test must run without mounted weights or data'
        containers.append({'id': container_id, 'name': name, 'image': details['Image'],
                           'mounts': details['Mounts']})
        if label == 'first':
            command('docker', 'stop', name)
    assert containers[0]['image'] == containers[1]['image']
    local = json.loads((REPORTS / 'local-api-tests.json').read_text())
    first = json.loads((REPORTS / 'container-first.json').read_text())
    second = json.loads((REPORTS / 'container-restarted.json').read_text())
    assert first['predictions'] == second['predictions']
    for a, b in zip(local['predictions'], first['predictions'], strict=True):
        assert a['image'] == b['image'] and a['category'] == b['category']
        assert abs(a['confidence'] - b['confidence']) < 1e-5
    evidence = {'containers': containers, 'same_image': True, 'identical_restart_predictions': True,
                'local_vs_docker_max_confidence_difference': max(
                    abs(a['confidence'] - b['confidence'])
                    for a, b in zip(local['predictions'], first['predictions'], strict=True))}
    (REPORTS / 'restart-check.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('PASS: both images built; local and container predictions agree; fresh restart passed.', flush=True)


if __name__ == '__main__':
    main()

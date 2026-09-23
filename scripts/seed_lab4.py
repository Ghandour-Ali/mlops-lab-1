"""Copy an exported MLflow model into the isolated Lab 4 registry (no training)."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import mlflow
import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', required=True, type=Path)
    parser.add_argument('--class-map', required=True, type=Path)
    parser.add_argument('--tracking-uri', default='http://127.0.0.1:5500')
    parser.add_argument('--output', type=Path, default=Path('reports/lab4/seed.json'))
    args = parser.parse_args()
    mlflow.set_tracking_uri(args.tracking_uri)
    client = mlflow.MlflowClient()
    existing = client.search_registered_models(filter_string="name = 'food11'")
    if existing:
        raise SystemExit('food11 already exists: refusing to overwrite its alias; use the promotion exercise instead.')
    original = yaml.safe_load((args.model_dir / 'MLmodel').read_text())
    mlflow.set_experiment('food11-lab4')
    with tempfile.TemporaryDirectory() as tmp, mlflow.start_run(run_name='copy-lab3-champion') as run:
        target = Path(tmp) / 'model'
        shutil.copytree(args.model_dir, target)
        metadata = dict(original)
        metadata['run_id'] = run.info.run_id
        metadata.pop('model_id', None)
        metadata['artifact_path'] = 'model'
        (target / 'MLmodel').write_text(yaml.safe_dump(metadata), encoding='utf-8')
        hashes = {str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (target / 'data').rglob('*') if p.is_file()}
        for relative, digest in hashes.items():
            assert hashlib.sha256((args.model_dir / relative).read_bytes()).hexdigest() == digest
        mlflow.set_tags({'source_run_id': original['run_id'], 'purpose': 'Lab 4 isolated copy; no retraining'})
        mlflow.log_dict(json.loads(args.class_map.read_text()), 'class_to_idx.json')
        mlflow.log_artifacts(str(target), 'model')
        version = mlflow.register_model(f'runs:/{run.info.run_id}/model', 'food11')
        client.set_registered_model_alias('food11', 'champion', version.version)
        evidence = {'source_run_id': original['run_id'], 'run_id': run.info.run_id,
                    'version': version.version, 'alias': 'champion', 'identical_weight_sha256': hashes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()

"""Exercise a running API and save reproducible HTTP test evidence."""
import argparse
import json
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8002')
    parser.add_argument('--images', type=Path, default=Path('data_preview'))
    parser.add_argument('--output', type=Path, default=Path('reports/lab3/api-tests.json'))
    args = parser.parse_args()
    session = requests.Session()
    response = session.get(args.url + '/health', timeout=15)
    assert response.status_code == 200 and response.json() == {'status': 'ok'}
    results = {'url': args.url, 'health': response.json(), 'predictions': []}
    images = sorted(args.images.rglob('*.jpg'))
    assert images, 'No test images found'
    for image in images[:11]:
        with image.open('rb') as stream:
            response = session.post(args.url + '/predict', files={'file': (image.name, stream, 'image/jpeg')}, timeout=60)
        assert response.status_code == 200, response.text
        prediction = response.json()
        assert isinstance(prediction['category'], str) and 0 <= prediction['confidence'] <= 1
        results['predictions'].append({'image': image.name, **prediction})
    for name, data, status in [('invalid.txt', b'not an image', 400),
                               ('empty.jpg', b'', 400),
                               ('oversized.jpg', b'x' * (10 * 1024 * 1024 + 1), 413)]:
        response = session.post(args.url + '/predict', files={'file': (name, data)}, timeout=30)
        assert response.status_code == status, response.text
        results[name] = response.status_code
    response = session.post(args.url + '/predict', timeout=15)
    assert response.status_code == 422
    results['missing_file'] = response.status_code
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(f'PASS: health, {len(results["predictions"])} image predictions, four invalid requests')


if __name__ == '__main__':
    main()

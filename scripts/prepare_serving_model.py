"""Publish existing champion weights through HTTP artifacts; no retraining."""
import argparse
import json
from pathlib import Path

import mlflow
import mlflow.pytorch
import numpy as np
import torch
from mlflow import MlflowClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tracking-uri', default='http://127.0.0.1:5002')
    args = parser.parse_args()
    mlflow.set_tracking_uri(args.tracking_uri)
    client = MlflowClient()
    original = client.get_model_version_by_alias('food11', 'champion')
    if original.tags.get('artifact_delivery') == 'http-proxy':
        print(f'food11 version {original.version} already prepared')
        return
    model = mlflow.pytorch.load_model(f'models:/food11/{original.version}', map_location='cpu')
    model.eval()
    mapping = client.download_artifacts(original.run_id, 'class_to_idx.json')
    mlflow.set_experiment('food11-serving')
    with mlflow.start_run(run_name='package-lab2-champion-for-docker') as run:
        mlflow.set_tags({'source_training_run': original.run_id,
                         'source_model_version': original.version,
                         'purpose': 'HTTP artifact delivery, identical weights; no training'})
        mlflow.log_dict(json.loads(Path(mapping).read_text()), 'class_to_idx.json')
        info = mlflow.pytorch.log_model(
            model, name='model', input_example=np.zeros((1, 3, 224, 224), dtype=np.float32),
            serialization_format='pickle')
        restored = mlflow.pytorch.load_model(info.model_uri, map_location='cpu')
        assert model.state_dict().keys() == restored.state_dict().keys()
        assert all(torch.equal(value, restored.state_dict()[key])
                   for key, value in model.state_dict().items()), 'Model weights changed'
        version = mlflow.register_model(info.model_uri, 'food11')
        client.set_model_version_tag('food11', version.version, 'artifact_delivery', 'http-proxy')
        client.set_model_version_tag('food11', version.version, 'source_training_run', original.run_id)
        client.set_registered_model_alias('food11', 'champion', version.version)
        print(json.dumps({'name': 'food11', 'version': version.version, 'alias': 'champion',
                          'source_training_run': original.run_id, 'packaging_run': run.info.run_id,
                          'model_uri': info.model_uri}, indent=2))


if __name__ == '__main__':
    main()

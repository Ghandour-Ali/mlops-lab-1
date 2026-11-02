"""Re-evaluate the incumbent and train two real candidates on the cleaned dataset."""
import json
import os
import subprocess
import sys
from pathlib import Path

import mlflow
import mlflow.pytorch
import torch
from mlflow import MlflowClient

from src.food11.promote import promote
from src.food11.train import evaluate, make_loaders
from src.food11.validate_data import dataset_fingerprint, validate_dataset

ROOT = Path(__file__).resolve().parents[1]
URI = "http://127.0.0.1:5500"
GROUP = "lab5-2026-11-02"
OUT = ROOT / "reports/lab5"
DATA = ROOT / "data/lab5/food11_processed_mini"


def main():
    os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    assert validate_dataset(DATA)["passed"]
    torch.set_num_threads(4)
    mlflow.set_tracking_uri(URI)
    client = MlflowClient()
    experiment = mlflow.set_experiment("food11-lab5")
    fingerprint = dataset_fingerprint(DATA)
    runs = client.search_runs([experiment.experiment_id], filter_string=f"tags.comparison_group = '{GROUP}'")
    baseline = next((r for r in runs if r.data.tags.get("purpose") == "incumbent-clean-evaluation" and r.info.status == "FINISHED"), None)
    if baseline is None:
        original = client.get_model_version_by_alias("food11", "champion")
        network = mlflow.pytorch.load_model(f"models:/food11/{original.version}", map_location="cpu")
        loaders = make_loaders(DATA, 32, 0)
        loss, accuracy = evaluate(network, loaders[2], torch.device("cpu"))
        with mlflow.start_run(run_name="incumbent-on-clean-holdout") as run:
            mlflow.set_tags({"comparison_group": GROUP, "purpose": "incumbent-clean-evaluation",
                             "source_model_version": original.version})
            mlflow.log_params({"dataset_sha256": fingerprint, "test_images": len(loaders[2].dataset)})
            mlflow.log_metrics({"test_accuracy": accuracy, "test_loss": loss})
            mlflow.log_dict(loaders[0].dataset.class_to_idx, "class_to_idx.json")
            info = mlflow.pytorch.log_model(network, name="model", serialization_format="pickle",
                                           input_example=torch.zeros(1, 3, 224, 224).numpy())
            version = mlflow.register_model(info.model_uri, "food11")
            mlflow.set_tag("registered_version", version.version)
            client.set_registered_model_alias("food11", "champion", version.version)
            baseline = client.get_run(run.info.run_id)
        print(f"Baseline version {version.version}: accuracy={accuracy:.6f}", flush=True)
    decisions = []
    for lr in (0.000001, 0.0001):
        runs = client.search_runs([experiment.experiment_id], filter_string=f"tags.comparison_group = '{GROUP}'")
        candidate = next((r for r in runs if r.info.status == "FINISHED" and r.data.params.get("lr") == str(lr)), None)
        if candidate is None:
            command = [sys.executable, "-m", "src.food11.train", "--data-root", "data/lab5",
                       "--dataset", "mini", "--epochs", "5", "--lr", str(lr), "--batch-size", "32",
                       "--tracking-uri", URI, "--experiment", "food11-lab5", "--comparison-group", GROUP]
            print("Training candidate: " + " ".join(command), flush=True)
            subprocess.run(command, cwd=ROOT, check=True)
            runs = client.search_runs([experiment.experiment_id], filter_string=f"tags.comparison_group = '{GROUP}'")
            candidate = next(r for r in runs if r.info.status == "FINISHED" and r.data.params.get("lr") == str(lr))
        registered = candidate.data.tags.get("registered_version")
        if registered is None:
            models = client.search_logged_models(experiment_ids=[experiment.experiment_id],
                                                 filter_string=f"source_run_id = '{candidate.info.run_id}'")
            assert len(models) == 1
            version = mlflow.register_model(f"models:/{models[0].model_id}", "food11")
            registered = version.version
            client.set_tag(candidate.info.run_id, "registered_version", registered)
        decision = promote(client, "food11", registered)
        decision["run_id"] = candidate.info.run_id
        decision["lr"] = lr
        decisions.append(decision)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "promotion-results.json").write_text(json.dumps({
            "baseline_run_id": baseline.info.run_id,
            "baseline_version": baseline.data.tags.get("registered_version"),
            "candidates": decisions}, indent=2), encoding="utf-8")
        print(json.dumps(decision, indent=2), flush=True)


if __name__ == "__main__":
    main()

"""Run the lab's controlled comparison and verify metrics and saved models."""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.pytorch
import numpy as np
import torch
from mlflow import MlflowClient

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--data-root", type=Path, default=Path("data"))
parser.add_argument("--tracking-uri", default="http://127.0.0.1:5000")
parser.add_argument("--group", default="lab2-comparison")
parser.add_argument("--epochs", type=int, default=5)
parser.add_argument("--run-missing", action="store_true")
args = parser.parse_args()
mlflow.set_tracking_uri(args.tracking_uri)
client = MlflowClient()
experiment = client.get_experiment_by_name("food11")
if experiment is None:
    experiment_id = client.create_experiment("food11")
else:
    experiment_id = experiment.experiment_id

def find_runs():
    return client.search_runs([experiment_id],
        filter_string=f"tags.comparison_group = '{args.group}'", max_results=100)

def matching(run, lr, batch):
    p = run.data.params
    return (float(p.get("lr", -1)) == lr and int(p.get("batch_size", -1)) == batch
            and int(p.get("epochs", -1)) == args.epochs and p.get("seed") == "42"
            and p.get("dataset") == "mini")

configs = [(0.001, 32), (0.01, 32), (0.0001, 32), (0.001, 64)]
for lr, batch in configs:
    matches = [r for r in find_runs() if matching(r, lr, batch)]
    if any(r.info.status == "RUNNING" for r in matches):
        raise RuntimeError(f"A matching run is still running: lr={lr}, batch={batch}")
    if any(r.info.status == "FINISHED" for r in matches):
        continue
    if not args.run_missing:
        raise RuntimeError(f"Missing successful run: lr={lr}, batch={batch}")
    subprocess.run([
        sys.executable, "-u", str(Path(__file__).with_name("train.py")),
        "--data-root", str(args.data_root.resolve()), "--dataset", "mini",
        "--epochs", str(args.epochs), "--lr", str(lr), "--batch-size", str(batch),
        "--tracking-uri", args.tracking_uri, "--comparison-group", args.group,
    ], check=True)

digest = hashlib.sha256()
mini = args.data_root / "food11_processed_mini"
for path in sorted(mini.rglob("*.jpg")):
    digest.update(path.relative_to(mini).as_posix().encode())
    digest.update(hashlib.sha256(path.read_bytes()).digest())
fingerprint = digest.hexdigest()
rows = []
torch.set_num_threads(4)
for lr, batch in configs:
    run = next(r for r in find_runs() if matching(r, lr, batch) and r.info.status == "FINISHED")
    rid = run.info.run_id
    for name in ("train_loss", "val_loss", "val_accuracy"):
        history = client.get_metric_history(rid, name)
        assert sorted(m.step for m in history) == list(range(args.epochs)), (rid, name)
        assert all(math.isfinite(m.value) for m in history)
    assert 0 <= run.data.metrics["test_accuracy"] <= 1
    assert 0 <= run.data.metrics["val_accuracy"] <= 1
    assert run.outputs and run.outputs.model_outputs, f"No model for {rid}"
    model_id = run.outputs.model_outputs[0].model_id
    saved = client.get_logged_model(model_id)
    model = mlflow.pytorch.load_model(f"models:/{model_id}", map_location="cpu")
    model.eval()
    with torch.no_grad():
        predictions = model(torch.zeros(1, 3, 224, 224))
    assert predictions.shape == (1, 11) and torch.isfinite(predictions).all()
    client.log_param(rid, "mini_dataset_sha256", fingerprint)
    rows.append({"run_id": rid, "lr": lr, "batch_size": batch,
                 "val_accuracy": run.data.metrics["val_accuracy"],
                 "test_accuracy": run.data.metrics["test_accuracy"],
                 "model_id": model_id, "artifact_location": saved.artifact_location})
    del model

rows.sort(key=lambda row: row["val_accuracy"], reverse=True)
output = Path("local_results")
output.mkdir(exist_ok=True)
(output / "comparison.json").write_text(json.dumps({"group": args.group,
    "experiment_id": experiment_id, "dataset_sha256": fingerprint, "runs": rows}, indent=2))

# Parallel coordinates: log10 learning rate and individually normalized axes.
values = np.array([[math.log10(r["lr"]), r["batch_size"], r["val_accuracy"]] for r in rows])
lo, hi = values.min(axis=0), values.max(axis=0)
normalized = (values - lo) / np.where(hi == lo, 1, hi - lo)
fig, ax = plt.subplots(figsize=(9, 5))
for row, points in zip(rows, normalized):
    ax.plot(range(3), points, "o-", label=f"{row['run_id'][:8]}: lr={row['lr']}, batch={row['batch_size']}")
ax.set_xticks(range(3), ["Learning rate (log10)", "Batch size", "Validation accuracy"])
ax.set_ylabel("Position within each axis range (0=min, 1=max)")
ax.set_title("Food-11: four complete runs, five epochs, seed 42")
ax.legend(fontsize=8, loc="best")
fig.tight_layout()
fig.savefig(output / "parallel_coordinates.png", dpi=160)
plt.close(fig)
client.log_artifact(rows[0]["run_id"], str(output / "parallel_coordinates.png"), "comparison")
client.log_artifact(rows[0]["run_id"], str(output / "comparison.json"), "comparison")
print(json.dumps({"best": rows[0], "verified_runs": len(rows)}, indent=2), flush=True)

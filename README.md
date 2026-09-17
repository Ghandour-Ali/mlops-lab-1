# Food-11 — Lab 2: training and MLflow tracking

See [the lab 2 report](Labs.md/lab2.md) for the nine answers and experiment results.

## Prepare the environment and data

```powershell
uv sync --locked
uv run python src/food11/prepare_mini.py --source data/food11_raw --output data/food11_processed_mini
```

The source must contain the original `training`, `validation`, and `evaluation`
splits. The preparation script selects up to 100 images per category per split,
converts to RGB, resizes to 128x128, and uses named category folders. It requires
an empty destination to preserve existing data. If a 128x128 RGB mini dataset
with named category folders is already prepared, skip this command. For older
datasets, choose a new output folder instead of overwriting them.
ResNet's pretrained input transform then produces
normalized 224x224 tensors during training.

## Start MLflow in a separate terminal

```powershell
uv run mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --workers 1
```

Open http://127.0.0.1:5000 and select the `food11` experiment.

## Train and compare

```powershell
uv run python src/food11/train.py --dataset mini --epochs 5 --lr 0.001 --batch-size 32
uv run python src/food11/compare_runs.py --group lab2-comparison --epochs 5 --run-missing
```

The comparison runs four configurations: learning rates 0.01, 0.001 and 0.0001
at batch size 32, then learning rate 0.001 at batch size 64. All use seed 42 and
the same dataset. Existing finished runs in the selected group are reused.
Use `--data-root PATH` when the dataset lives outside this checkout.

The comparison script verifies all five epochs of each metric, reloads every
saved model, tests its 11 outputs, and records the mini-dataset fingerprint.
It saves a local summary and parallel-coordinates plot under `local_results/`
and logs them as comparison artifacts on the best run (selected by final
validation accuracy). Test accuracy does not determine model selection.

In MLflow, select the four runs and click **Compare** to inspect their metric
curves and parallel coordinates (`lr`, `batch_size`, `val_accuracy`).

Code, dependency files and the written report are tracked by Git. `mlflow.db`,
`mlruns/`, `.venv/`, and `local_results/` remain local and ignored. They are not
DVC outputs. Keep the MLflow database and artifacts together for later labs.

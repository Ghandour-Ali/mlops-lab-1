"""Serve the registered Food-11 champion through FastAPI."""

import io
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import mlflow
import mlflow.pyfunc
import numpy as np
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from torchvision.models import ResNet18_Weights

MODEL_URI = "models:/food11@champion"
MAX_IMAGE_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    torch.set_num_threads(4)
    version = mlflow.MlflowClient().get_model_version_by_alias("food11", "champion")
    # Pin the resolved version for this process; a restart resolves the alias again.
    model = mlflow.pyfunc.load_model(f"models:/food11/{version.version}")
    app.state.model_version = str(version.version)
    # Read labels from the loaded model's actual training run, not an assumed order.
    run_id = model.metadata.run_id
    if not run_id:
        raise RuntimeError("The registered model has no training run ID")
    mapping_path = mlflow.artifacts.download_artifacts(
        run_id=run_id, artifact_path="class_to_idx.json"
    )
    mapping = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    if len(mapping) != 11 or sorted(mapping.values()) != list(range(11)):
        raise RuntimeError("Invalid Food-11 class mapping")
    app.state.classes = [name for name, index in sorted(mapping.items(), key=lambda item: item[1])]
    app.state.model = model
    app.state.transform = ResNet18_Weights.DEFAULT.transforms()
    logging.getLogger('uvicorn.error').info(
        'Loaded %s from run %s with %d classes', MODEL_URI, run_id, len(mapping)
    )
    yield


app = FastAPI(title="Food-11 prediction API", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/model")
def model_info():
    return {"name": "food11", "alias": "champion", "loaded_version": app.state.model_version}


@app.post("/predict")
def predict(file: UploadFile = File(...)):
    contents = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 10 MiB")
    try:
        with Image.open(io.BytesIO(contents)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            # Reproduce Lab 1 resizing, then Lab 2's pretrained input transform.
            image = image.resize((128, 128), Image.Resampling.LANCZOS)
            inputs = app.state.transform(image).unsqueeze(0).numpy()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=400, detail="Upload a valid image") from exc

    logits = np.asarray(app.state.model.predict(inputs))
    if logits.shape != (1, 11) or not np.isfinite(logits).all():
        raise HTTPException(status_code=500, detail="Invalid model output")
    scores = np.exp(logits[0] - logits[0].max())
    probabilities = scores / scores.sum()
    index = int(probabilities.argmax())
    return {"category": app.state.classes[index], "confidence": float(probabilities[index])}

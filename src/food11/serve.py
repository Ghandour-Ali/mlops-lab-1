"""Serve Food-11; SKIP_MODEL enables offline tests without Torch or MLflow."""
import io
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from .data import CLASSES, resize_image

MODEL_URI = "models:/food11@champion"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
model = None


def preprocess_image(image: Image.Image) -> np.ndarray:
    """Lab 1 resize, then ResNet18 DEFAULT PIL resize/crop/normalization."""
    image = resize_image(image).resize((256, 256), Image.Resampling.BILINEAR)
    image = image.crop((16, 16, 240, 240))
    tensor = np.asarray(image, dtype=np.float32).transpose(2, 0, 1) / 255.0
    mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)[:, None, None]
    std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)[:, None, None]
    return ((tensor - mean) / std)[None, ...]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    model = None
    app.state.model_version = None
    app.state.classes = list(CLASSES)
    if not os.environ.get("SKIP_MODEL"):
        import mlflow.pyfunc
        import torch

        import mlflow

        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
        torch.set_num_threads(4)
        version = mlflow.MlflowClient().get_model_version_by_alias("food11", "champion")
        loaded = mlflow.pyfunc.load_model(f"models:/food11/{version.version}")
        run_id = loaded.metadata.run_id
        if not run_id:
            raise RuntimeError("The registered model has no training run ID")
        mapping_path = mlflow.artifacts.download_artifacts(
            run_id=run_id, artifact_path="class_to_idx.json"
        )
        mapping = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
        if set(mapping) != set(CLASSES) or sorted(mapping.values()) != list(range(11)):
            raise RuntimeError("Invalid Food-11 class mapping")
        app.state.classes = [name for name, index in sorted(mapping.items(), key=lambda item: item[1])]
        app.state.model_version = str(version.version)
        model = loaded
        logging.getLogger("uvicorn.error").info("Loaded %s version %s", MODEL_URI, version.version)
    try:
        yield
    finally:
        model = None


app = FastAPI(title="Food-11 prediction API", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/model")
def model_info():
    return {"name": "food11", "alias": "champion", "loaded_version": app.state.model_version}


@app.post("/predict")
def predict(file: Annotated[UploadFile, File()]):
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")
    contents = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 10 MiB")
    try:
        with Image.open(io.BytesIO(contents)) as image:
            inputs = preprocess_image(image)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=400, detail="Upload a valid image") from exc
    logits = np.asarray(model.predict(inputs))
    if logits.shape != (1, 11) or not np.isfinite(logits).all():
        raise HTTPException(status_code=500, detail="Invalid model output")
    scores = np.exp(logits[0] - logits[0].max())
    probabilities = scores / scores.sum()
    index = int(probabilities.argmax())
    return {"category": app.state.classes[index], "confidence": float(probabilities[index])}

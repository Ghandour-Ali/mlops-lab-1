import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from src.food11.data import CLASSES
from src.food11.validate_data import validate_dataset


@pytest.fixture
def dataset(tmp_path):
    for split_index, split in enumerate(("training", "validation", "evaluation")):
        for class_index, name in enumerate(CLASSES):
            folder = tmp_path / split / name
            folder.mkdir(parents=True)
            Image.new("RGB", (128, 128), (split_index * 60, class_index * 20, 50)).save(folder / "image.png")
    return tmp_path


def test_good_contract(dataset):
    assert validate_dataset(dataset, min_per_class=1)["passed"]


def test_duplicate_between_splits(dataset):
    shutil.copyfile(dataset / "training/Bread/image.png", dataset / "evaluation/Bread/copied.png")
    report = validate_dataset(dataset, min_per_class=1)
    assert not report["passed"]
    assert not report["checks"]["cross_split_duplicates"]["passed"]


@pytest.mark.parametrize("kind", ["corrupt", "grayscale", "wrong_size"])
def test_bad_image(dataset, kind):
    path = dataset / "training/Bread/image.png"
    if kind == "corrupt":
        path.write_bytes(b"corrupt")
    else:
        Image.new("L" if kind == "grayscale" else "RGB", (128, 128) if kind == "grayscale" else (64, 64)).save(path)
    assert not validate_dataset(dataset, 1)["checks"]["images_rgb_128"]["passed"]


def test_unexpected_class_and_minimum(dataset):
    (dataset / "training/Unexpected").mkdir()
    report = validate_dataset(dataset, min_per_class=2)
    assert not report["checks"]["class_folders"]["passed"]
    assert not report["checks"]["minimum_counts"]["passed"]


def test_balance(dataset):
    source = dataset / "training/Bread/image.png"
    for i in range(10):
        shutil.copyfile(source, source.with_name(f"extra-{i}.png"))
    assert not validate_dataset(dataset, 1)["checks"]["class_balance"]["passed"]


def test_missing_dataset(tmp_path):
    assert not validate_dataset(tmp_path / "missing")["passed"]


def test_cli_exit_code(dataset):
    script = Path(__file__).parents[1] / "src/food11/validate_data.py"
    command = [sys.executable, str(script), str(dataset), "--min-per-class", "1"]
    assert subprocess.run(command, capture_output=True, check=False).returncode == 0
    shutil.copyfile(dataset / "training/Bread/image.png", dataset / "evaluation/Bread/copied.png")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "FAIL cross_split_duplicates" in result.stdout

"""Prepare Food-11 as RGB ImageFolder datasets, preserving the official splits."""

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageOps

CATEGORIES = (
    "Bread", "Dairy product", "Dessert", "Egg", "Fried food", "Meat",
    "Noodles-Pasta", "Rice", "Seafood", "Soup", "Vegetable-Fruit",
)
SPLITS = ("training", "evaluation", "validation")
CLASSES = list(CATEGORIES)


def category_from_filename(filename: str) -> str:
    """Map a Food-11 numeric filename prefix to its category."""
    prefix, separator, suffix = Path(filename).name.partition("_")
    if not separator or not suffix or not prefix.isdecimal():
        raise ValueError(f"Invalid Food-11 filename: {filename}")
    label = int(prefix)
    if not 0 <= label < len(CLASSES):
        raise ValueError(f"Invalid Food-11 category: {filename}")
    return CLASSES[label]


def resize_image(img: Image.Image, size: int = 128) -> Image.Image:
    """Return a new RGB square image without modifying the input."""
    if size < 1:
        raise ValueError("size must be positive")
    return ImageOps.exif_transpose(img).convert("RGB").resize(
        (size, size), Image.Resampling.LANCZOS
    )


def prepare(root: Path, mini_limit: int = 100) -> dict:
    if mini_limit < 1:
        raise ValueError("mini-limit must be positive")
    raw = root / "food11_raw"
    sources = {}
    for split in SPLITS:
        files = sorted((raw / split).glob("*.jpg"))
        if not files:
            raise ValueError(f"No JPEG images in {raw / split}")
        for path in files:
            label = int(path.stem.split("_")[0])
            if not 0 <= label < len(CATEGORIES):
                raise ValueError(f"Invalid category: {path}")
        sources[split] = files
    processed = root / "food11_processed"
    mini = root / "food11_processed_mini"
    # Preserve existing datasets; choose a fresh data directory to rebuild.
    for destination in (processed, mini):
        if destination.is_symlink() or (destination.exists() and any(destination.iterdir())):
            raise ValueError(f"Destination must be empty: {destination}")
    for destination in (processed, mini):
        for split in SPLITS:
            for category in CATEGORIES:
                (destination / split / category).mkdir(parents=True)
    counts = {}
    for split, files in sources.items():
        counts[split] = {category: 0 for category in CATEGORIES}
        for source in files:
            category = category_from_filename(source.name)
            destination = processed / split / category / source.name
            with Image.open(source) as image:
                resize_image(image).save(destination, quality=95)
            if counts[split][category] < mini_limit:
                shutil.copyfile(destination, mini / split / category / source.name)
            counts[split][category] += 1
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[2] / "data")
    parser.add_argument("--mini-limit", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(prepare(args.data_dir.resolve(), args.mini_limit), indent=2))

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
            category = CATEGORIES[int(source.stem.split("_")[0])]
            destination = processed / split / category / source.name
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.resize((128, 128), Image.Resampling.LANCZOS).save(destination, quality=95)
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

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


SPLITS = ("training", "validation", "evaluation")
CATEGORIES = ("Bread", "Dairy product", "Dessert", "Egg", "Fried food", "Meat",
              "Noodles-Pasta", "Rice", "Seafood", "Soup", "Vegetable-Fruit")


def prepare_dataset(source_root: Path, output_root: Path, limit_per_class: int) -> None:
    if limit_per_class < 1:
        raise ValueError("limit-per-class must be positive")
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError("Use an empty output folder; existing images are preserved")
    selected = {}
    for split in SPLITS:
        source_split = source_root / split
        files_by_class: dict[str, list[Path]] = {str(label): [] for label in range(11)}

        for image_path in sorted(source_split.glob("*.jpg")):
            class_name = image_path.stem.split("_", maxsplit=1)[0]
            if class_name in files_by_class and len(files_by_class[class_name]) < limit_per_class:
                files_by_class[class_name].append(image_path)
        if not all(files_by_class.values()):
            raise ValueError(f"Expected images for all 11 classes in {source_split}")
        selected[split] = files_by_class

    for split, files_by_class in selected.items():
        for class_name, image_paths in files_by_class.items():
            output_class = output_root / split / CATEGORIES[int(class_name)]
            output_class.mkdir(parents=True, exist_ok=True)
            for image_path in image_paths:
                with Image.open(image_path) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.resize((128, 128), Image.Resampling.LANCZOS).save(
                        output_class / image_path.name, quality=95)

        total = sum(len(images) for images in files_by_class.values())
        print(f"{split}: {total} images")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a small ImageFolder-compatible Food-11 dataset.")
    parser.add_argument("--source", type=Path, default=Path("data/food11_raw"))
    parser.add_argument("--output", type=Path, default=Path("data/food11_processed_mini"))
    parser.add_argument("--limit-per-class", type=int, default=100)
    args = parser.parse_args()
    prepare_dataset(args.source, args.output, args.limit_per_class)


if __name__ == "__main__":
    main()

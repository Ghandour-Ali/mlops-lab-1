from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


SPLITS = ("training", "validation", "evaluation")


def link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except (FileExistsError, OSError):
        shutil.copy2(source, destination)


def prepare_dataset(source_root: Path, output_root: Path, limit_per_class: int) -> None:
    for split in SPLITS:
        source_split = source_root / split
        output_split = output_root / split
        files_by_class: dict[str, list[Path]] = {str(label): [] for label in range(11)}

        for image_path in sorted(source_split.glob("*.jpg")):
            class_name = image_path.stem.split("_", maxsplit=1)[0]
            if class_name in files_by_class and len(files_by_class[class_name]) < limit_per_class:
                files_by_class[class_name].append(image_path)

        for class_name, image_paths in files_by_class.items():
            for image_path in image_paths:
                link_or_copy(image_path, output_split / class_name / image_path.name)

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

"""Validate the Food-11 contract without changing dataset files."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

if __package__:
    from .data import CLASSES
else:
    from data import CLASSES

SPLITS = ("training", "validation", "evaluation")


def dataset_fingerprint(root: Path) -> str:
    """Fingerprint relative paths and content; independent of host directory."""
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob("*.jpg")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def validate_dataset(root: Path, min_per_class: int = 50, tau: float = 0.05) -> dict:
    if min_per_class < 1 or not math.isfinite(tau) or not 0 <= tau <= 1:
        raise ValueError("min-per-class must be positive; tau must be between 0 and 1")
    root = Path(root)
    errors = {name: [] for name in ("class_folders", "images_rgb_128", "minimum_counts", "cross_split_duplicates", "class_balance")}
    counts = {split: {name: 0 for name in CLASSES} for split in SPLITS}
    seen = {}
    for split in SPLITS:
        folder = root / split
        children = list(folder.iterdir()) if folder.is_dir() else []
        directories = {p.name for p in children if p.is_dir()}
        if directories != set(CLASSES) or any(p.is_file() for p in children):
            errors["class_folders"].append(f"{split}: expected exactly 11 class directories")
        for category in CLASSES:
            class_dir = folder / category
            files = sorted(class_dir.rglob("*")) if class_dir.is_dir() else []
            for path in files:
                if not path.is_file():
                    errors["images_rgb_128"].append(f"Unexpected nested directory: {path.relative_to(root)}")
                    continue
                relative = path.relative_to(root).as_posix()
                try:
                    digest = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
                    if digest in seen and seen[digest][0] != split:
                        errors["cross_split_duplicates"].append([seen[digest][1], relative])
                    else:
                        seen.setdefault(digest, (split, relative))
                    with Image.open(path) as image:
                        image.load()
                        if image.mode != "RGB" or image.size != (128, 128):
                            raise ValueError(f"mode={image.mode}, size={image.size}")
                    counts[split][category] += 1
                except (OSError, ValueError, Image.DecompressionBombError) as exc:
                    errors["images_rgb_128"].append(f"{relative}: {exc}")
            if counts[split][category] < min_per_class:
                errors["minimum_counts"].append(f"{split}/{category}: {counts[split][category]} < {min_per_class}")
    train_total = sum(counts["training"].values())
    val_total = sum(counts["validation"].values())
    differences = {}
    if not train_total or not val_total:
        errors["class_balance"].append("Empty training or validation split")
    else:
        for category in CLASSES:
            difference = abs(counts["training"][category] / train_total - counts["validation"][category] / val_total)
            differences[category] = difference
            if difference > tau:
                errors["class_balance"].append(f"{category}: difference={difference:.6f} > {tau}")
    return {"passed": not any(errors.values()), "min_per_class": min_per_class, "tau": tau,
            "counts": counts, "share_differences": differences,
            "checks": {name: {"passed": not problems, "errors": problems} for name, problems in errors.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--min-per-class", type=int, default=50)
    parser.add_argument("--tau", type=float, default=0.05)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = validate_dataset(args.dataset, args.min_per_class, args.tau)
    except ValueError as exc:
        parser.error(str(exc))
    for name, result in report["checks"].items():
        print(f"{'PASS' if result['passed'] else 'FAIL'} {name}: {len(result['errors'])} error(s)")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

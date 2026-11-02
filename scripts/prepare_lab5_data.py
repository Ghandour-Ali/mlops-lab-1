"""Copy the mini dataset, removing cross-split duplicates without changing DVC data."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from src.food11.validate_data import validate_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/food11_processed_mini"))
    parser.add_argument("--output", type=Path, default=Path("data/lab5/food11_processed_mini"))
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists: refusing to overwrite data")
    seen = {}
    removed = []
    # Keep training unchanged; remove overlaps from validation and held-out evaluation.
    for split in ("training", "validation", "evaluation"):
        for category in sorted((args.source / split).iterdir()):
            target = args.output / split / category.name
            target.mkdir(parents=True, exist_ok=True)
            for source in sorted(category.glob("*.jpg")):
                digest = hashlib.md5(source.read_bytes(), usedforsecurity=False).hexdigest()
                relative = source.relative_to(args.source).as_posix()
                if digest in seen and seen[digest][0] != split:
                    removed.append({"removed": relative, "kept": seen[digest][1], "md5": digest})
                    continue
                seen.setdefault(digest, (split, relative))
                shutil.copyfile(source, target / source.name)
    report = validate_dataset(args.output)
    assert report["passed"], report
    out = Path("reports/lab5")
    out.mkdir(parents=True, exist_ok=True)
    (out / "data-cleanup.json").write_text(json.dumps({"removed": removed, "source_unchanged": True}, indent=2))
    (out / "data-contract-clean.json").write_text(json.dumps(report, indent=2))
    print(f"Removed {len(removed)} cross-split copies from the new dataset; original untouched.")


if __name__ == "__main__":
    main()

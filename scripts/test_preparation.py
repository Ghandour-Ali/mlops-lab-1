"""Check resizing, labels, split isolation, and the 100-image cutoff on fixtures."""
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "food11"))
from data import CATEGORIES, SPLITS, prepare


class PreparationTest(unittest.TestCase):
    def test_preparation_and_repeatability(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for split in SPLITS:
                raw = root / "food11_raw" / split
                raw.mkdir(parents=True)
                for label in range(11):
                    Image.new("L", (37, 55), label * 20).save(raw / f"{label}_0.jpg")
                for index in range(1, 101):
                    Image.new("RGB", (20, 30), (index, 20, 30)).save(raw / f"0_{index}.jpg")
            original = (root / "food11_raw/training/0_0.jpg").read_bytes()
            counts = prepare(root)
            self.assertEqual(counts["training"]["Bread"], 101)
            for split in SPLITS:
                for category in CATEGORIES:
                    full = root / "food11_processed" / split / category
                    mini = root / "food11_processed_mini" / split / category
                    files = sorted(full.glob("*.jpg"))
                    selected = sorted(mini.glob("*.jpg"))
                    self.assertEqual([p.name for p in selected], [p.name for p in files[:100]])
                    for path in files:
                        with Image.open(path) as image:
                            self.assertEqual(image.size, (128, 128))
                            self.assertEqual(image.mode, "RGB")
                    for path in selected:
                        self.assertEqual(path.read_bytes(), (full / path.name).read_bytes())
            self.assertEqual(original, (root / "food11_raw/training/0_0.jpg").read_bytes())
            with self.assertRaises(ValueError):
                prepare(root, mini_limit=2)
            self.assertEqual(len(list((root / "food11_processed_mini/training/Bread").glob("*.jpg"))), 100)


if __name__ == "__main__":
    unittest.main()

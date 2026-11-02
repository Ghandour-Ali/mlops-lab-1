from pathlib import Path

import pytest
from PIL import Image

from src.food11.data import CLASSES, category_from_filename, resize_image


@pytest.mark.parametrize(("filename", "category"), [("0_12.jpg", "Bread"), ("3_120.jpg", "Egg"), ("10_3.jpg", "Vegetable-Fruit")])
def test_category_from_filename(filename, category):
    assert category_from_filename(filename) == category


@pytest.mark.parametrize("filename", ["-1_0.jpg", "11_0.jpg", "bread.jpg", "x_3.jpg", "0_"])
def test_invalid_category(filename):
    with pytest.raises(ValueError):
        category_from_filename(filename)


def test_resize_image_shape_and_mode():
    original = Image.new("L", (512, 384))
    result = resize_image(original)
    assert result.size == (128, 128)
    assert result.mode == "RGB"
    assert original.size == (512, 384)
    assert original.mode == "L"


def test_custom_resize_and_invalid_size():
    assert resize_image(Image.new("RGBA", (20, 30)), 64).size == (64, 64)
    with pytest.raises(ValueError):
        resize_image(Image.new("RGB", (20, 30)), 0)


def test_eleven_classes_and_fixture():
    assert len(set(CLASSES)) == 11
    with Image.open(Path(__file__).parent / "fixtures/bread.jpg") as image:
        assert image.size == (128, 128) and image.mode == "RGB"

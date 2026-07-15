from __future__ import annotations

import sys

from etsytools.paths import PROJECT_ROOT

IMAGE_ASSIST_DIR = PROJECT_ROOT / "ImageAssist"
if str(IMAGE_ASSIST_DIR) not in sys.path:
    sys.path.append(str(IMAGE_ASSIST_DIR))

from processor import (  # noqa: E402
    auto_process_sheet,
    color_shift_interactive,
    create_showcase_mockup,
    crop_images,
    format_clipart_batch,
    remove_background,
    resize_images,
    split_image,
)

__all__ = [
    "auto_process_sheet",
    "color_shift_interactive",
    "create_showcase_mockup",
    "crop_images",
    "format_clipart_batch",
    "remove_background",
    "resize_images",
    "split_image",
]


"""Shared helpers for visual regression tests."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image
from qtpy.QtWidgets import QWidget


def capture_widget(widget: QWidget) -> bytes:
    """Render widget to PNG bytes suitable for image_regression.check().

    Uses widget.grab() which works under offscreen rendering without needing
    a visible window handle.
    """
    pixmap = widget.grab()
    image = pixmap.toImage().convertToFormat(
        pixmap.toImage().Format.Format_RGBA8888
    )
    width, height = image.width(), image.height()
    ptr = image.bits()
    # PySide6 bits() returns a memoryview; convert to bytes.
    if hasattr(ptr, "tobytes"):
        data = ptr.tobytes()
    else:
        ptr.setsize(height * width * 4)
        data = bytes(ptr)
    arr = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))
    pil_image = Image.fromarray(arr)
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()

"""Shared helpers for visual regression tests."""

from __future__ import annotations

import io
from functools import partial

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


def copy_result_to_refs(obtained_path: str, ref_path: str, w: QWidget) -> None:
    """Copy obtained image to reference path, for quick acceptance of new results."""
    import shutil

    print(f"Accepting new result: {obtained_path} to {ref_path}")
    shutil.copy(obtained_path, ref_path)
    w.setEnabled(False)


def show_images(*images: tuple[str, str, str]) -> None:
    """Show failed test images in a simple window for debugging.

    This is intended to be called from a subprocess after the test run, with
    paths to the obtained and reference images. It creates a simple Qt
    application that allows the user to view the obtained and reference images
    and optionally copy the obtained image to the reference location to accept
    the new result.

    Args:
        images: A list of tuples containing the test name, obtained image path,
            and reference image path.

    """
    import os

    from qtpy.QtCore import Qt
    from qtpy.QtGui import QPixmap
    from qtpy.QtWidgets import QApplication, QStackedWidget, QLabel

    from ayon_ui_qt.components.container import AYContainer
    from ayon_ui_qt.components.label import AYLabel
    from ayon_ui_qt.components.buttons import AYButton
    from ayon_ui_qt.components.check_box import AYCheckBox
    from ayon_ui_qt.components.scroll_area import AYScrollArea

    app = QApplication.instance() or QApplication([])

    window = AYScrollArea()
    window.setWindowTitle("Image Comparison")
    window.setWidgetResizable(True)

    root = AYContainer(
        variant=AYContainer.Variants.Low,
        layout=AYContainer.Layout.VBox,
        layout_margin=10,
        layout_spacing=10,
    )

    for test_name, test_img_path, ref_img_path in images:
        lyt = AYContainer(
            variant=AYContainer.Variants.Low_Framed_Thin,
            layout=AYContainer.Layout.VBox,
            layout_margin=10,
            layout_spacing=10,
        )

        btn_lyt = AYContainer(
            variant=AYContainer.Variants.Low,
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=10,
        )
        label = AYLabel(f"{test_name}")
        label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        btn_lyt.add_widget(label, stretch=1)
        show_ref_btn = AYCheckBox("Show reference")
        show_ref_btn.setChecked(False)
        accept_btn = AYButton("Accept test", variant=AYButton.Variants.Danger)
        btn_lyt.add_widget(show_ref_btn)
        btn_lyt.add_widget(accept_btn)
        lyt.add_widget(btn_lyt)

        stack = QStackedWidget()
        for img_path in (test_img_path, ref_img_path):
            pixmap = QPixmap(img_path)
            lbl = QLabel()
            lbl.setPixmap(pixmap)
            stack.addWidget(lbl)
        lyt.add_widget(stack)
        stack.setCurrentIndex(0)
        root.add_widget(lyt)

        show_ref_btn.stateChanged.connect(
            lambda state, s=stack: s.setCurrentIndex(1)
            if state == Qt.CheckState.Checked.value
            else s.setCurrentIndex(0)
        )
        repo_ref = os.path.join(
            os.getcwd(), "tests", "test_visual", os.path.basename(ref_img_path)
        )
        accept_btn.clicked.connect(
            lambda _,
            p=test_img_path,
            r=repo_ref,
            w=accept_btn: copy_result_to_refs(p, r, w)
        )
    root._layout.addStretch(1)

    window.setWidget(root)
    window.show()
    app.exec()


if __name__ == "__main__":
    import json
    import sys

    if sys.argv[1:]:
        show_images(*json.loads(sys.argv[1]))
    else:
        imgs = [
            [
                "checkbox initial",
                "./tests/foo/CheckBoxTest_00_initial.obtained.png",
                "./tests/foo/CheckBoxTest_00_initial.png",
            ],
        ]
        show_images(*imgs)

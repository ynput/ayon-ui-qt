"""Shared helpers for visual regression tests."""

from __future__ import annotations

import io
import os
from pathlib import Path

import numpy as np
from PIL import Image
from qtpy.QtGui import QImage
from qtpy.QtWidgets import QWidget


def capture_widget(widget: QWidget) -> bytes:
    """Render widget to PNG bytes suitable for image_regression.check().

    Uses widget.grab() which works under offscreen rendering without needing
    a visible window handle.
    """
    pixmap = widget.grab()
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
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


def _make_image_card(test_name: str, test_img_path: str, ref_img_path: str):
    """Build one comparison card for show_images()."""
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QPixmap
    from qtpy.QtWidgets import QLabel, QStackedWidget

    from ayon_ui_qt.components.buttons import AYButton
    from ayon_ui_qt.components.check_box import AYCheckBox
    from ayon_ui_qt.components.container import AYContainer
    from ayon_ui_qt.components.label import AYLabel

    card = AYContainer(
        variant=AYContainer.Variants.Low_Framed_Thin,
        layout=AYContainer.Layout.VBox,
        layout_margin=10,
        layout_spacing=10,
    )

    header = AYContainer(
        variant=AYContainer.Variants.Low,
        layout=AYContainer.Layout.HBox,
        layout_margin=0,
        layout_spacing=10,
    )
    title = AYLabel(test_name)
    title.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    show_ref_cb = AYCheckBox("Show reference")
    accept_btn = AYButton("Accept test", variant=AYButton.Variants.Danger)
    header.add_widget(title, stretch=1)
    header.add_widget(show_ref_cb)
    header.add_widget(accept_btn)
    card.add_widget(header)

    stack = QStackedWidget()
    for img_path in (test_img_path, ref_img_path):
        lbl = QLabel()
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            lbl.setText(f"[missing: {os.path.basename(img_path)}]")
        else:
            lbl.setPixmap(pixmap)
        stack.addWidget(lbl)
    card.add_widget(stack)

    is_same = test_img_path == ref_img_path
    show_ref_cb.setChecked(is_same)
    show_ref_cb.setEnabled(not is_same)
    accept_btn.setEnabled(not is_same)
    if is_same:
        accept_btn.setToolTip("Test and reference images are the same.")
    else:
        show_ref_cb.checkStateChanged.connect(
            lambda state, s=stack: s.setCurrentIndex(
                1 if state == Qt.CheckState.Checked else 0
            )
        )
        dest_ref = str(
            Path(__file__).parent
            / "test_visual"
            / os.path.basename(ref_img_path)
        )
        accept_btn.clicked.connect(
            lambda _,
            p=test_img_path,
            r=dest_ref,
            w=accept_btn: copy_result_to_refs(p, r, w)
        )

    return card


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
    from qtpy.QtCore import QSize
    from qtpy.QtWidgets import QApplication

    from ayon_ui_qt.style import get_ayon_style
    from ayon_ui_qt.components.container import AYContainer
    from ayon_ui_qt.components.line_edit import AYLineEdit
    from ayon_ui_qt.components.scroll_area import AYScrollArea

    app = QApplication.instance() or QApplication([])
    app.setStyle(get_ayon_style())

    window = AYContainer(
        layout=AYContainer.Layout.VBox,
        variant=AYContainer.Variants.Low,
        layout_margin=10,
        layout_spacing=10,
    )
    window.setWindowTitle("Image Comparison")
    window_lyt = window._layout

    search_field = AYLineEdit(
        placeholder="Search images…",
        variant=AYLineEdit.Variants.Search_Field,
    )
    search_field.setFixedHeight(search_field.sizeHint().height())
    window_lyt.addWidget(search_field)

    scroll = AYScrollArea()
    scroll.setWidgetResizable(True)
    window_lyt.addWidget(scroll)

    root = AYContainer(
        variant=AYContainer.Variants.Low,
        layout=AYContainer.Layout.VBox,
        layout_margin=0,
        layout_spacing=10,
    )

    cards: list[tuple[str, QWidget]] = []
    for name, *rest in images:
        card = _make_image_card(name, *rest)
        root.add_widget(card)
        cards.append((name, card))

    root._layout.addStretch(1)

    scroll.setWidget(root)

    def _filter_cards(text: str) -> None:
        query = text.strip().lower()
        for card_name, card in cards:
            card.setVisible(not query or query in card_name.lower())

    search_field.textChanged.connect(_filter_cards)

    window.show()
    window.resize(root.sizeHint() + QSize(20, 40))
    app.exec()


if __name__ == "__main__":
    import json
    import sys
    import glob

    if sys.argv[1:]:
        if sys.argv[1] == "--show-refs" and len(sys.argv) == 2:
            # show all reference images in the refs directory for manual
            # inspection
            ref_dir = os.path.join(os.getcwd(), "tests", "test_visual")
            ref_images = glob.glob(os.path.join(ref_dir, "*.png"))
            images = [
                (os.path.basename(img), img, img)
                for img in sorted(ref_images, key=os.path.basename)
            ]
            show_images(*images)
        else:
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

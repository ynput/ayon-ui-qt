"""Visual regression tests for AYEntityThumbnail."""

from __future__ import annotations

from pathlib import Path

import ayon_ui_qt as _ayon_ui_qt_pkg
from qtpy.QtWidgets import QWidget

from widget_test import WidgetTest
from ayon_ui_qt.components.entity_thumbnail import AYEntityThumbnail
from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.components.label import AYLabel

_RSRC = Path(_ayon_ui_qt_pkg.__file__).parent / "resources"


def _file_cacher(key: str) -> Path | str:
    """Resolve a cache key to a file path in the resources directory."""
    for ext in ("jpg", "png"):
        p = _RSRC / f"{key}.{ext}"
        if p.exists():
            return p
    return ""


class EntityThumbnailTest(WidgetTest):
    """Tests AYEntityThumbnail with images, placeholders, and variants."""

    size = (600, 200)
    tolerance = 0.0

    def build(self) -> QWidget:
        root = AYContainer(
            layout=AYContainer.Layout.VBox,
            layout_margin=20,
            layout_spacing=12,
        )

        # Row 1: Default thumbnail variant with images
        row1 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=12,
        )
        row1.add_widget(AYLabel("Thumbnail variant:"))
        self._thumb1 = AYEntityThumbnail(
            src=_RSRC / "avatar1.jpg",
            size=(85, 48),
            variant=AYEntityThumbnail.Variants.Thumbnail,
        )
        row1.add_widget(self._thumb1)
        self._thumb2 = AYEntityThumbnail(
            src=_RSRC / "avatar2.jpg",
            size=(85, 48),
            variant=AYEntityThumbnail.Variants.Thumbnail,
        )
        row1.add_widget(self._thumb2)
        # Placeholder (no image)
        self._thumb_placeholder = AYEntityThumbnail(
            size=(85, 48),
            variant=AYEntityThumbnail.Variants.Thumbnail,
        )
        row1.add_widget(self._thumb_placeholder)
        row1.addStretch(1)
        root.add_widget(row1)

        # Row 2: Entity_Card variant
        row2 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=12,
        )
        row2.add_widget(AYLabel("Entity_Card variant:"))
        self._card_thumb1 = AYEntityThumbnail(
            src=_RSRC / "avatar1.jpg",
            size=(85, 48),
            variant=AYEntityThumbnail.Variants.Entity_Card,
        )
        row2.add_widget(self._card_thumb1)
        self._card_thumb2 = AYEntityThumbnail(
            src=_RSRC / "avatar3.jpg",
            size=(85, 48),
            variant=AYEntityThumbnail.Variants.Entity_Card,
        )
        row2.add_widget(self._card_thumb2)
        # Placeholder with custom icon
        self._card_thumb_placeholder = AYEntityThumbnail(
            size=(85, 48),
            placeholder_icon="photo_library",
            variant=AYEntityThumbnail.Variants.Entity_Card,
        )
        row2.add_widget(self._card_thumb_placeholder)
        row2.addStretch(1)
        root.add_widget(row2)

        return root

    def swap_images(self) -> None:
        """Swap thumbnail images to show the fade transition state."""
        self._thumb1.set_thumbnail(_RSRC / "avatar3.jpg")
        self._card_thumb1.set_thumbnail(_RSRC / "avatar2.jpg")

    def disable_all(self) -> None:
        """Disable all thumbnails to show disabled state."""
        self._thumb1.setEnabled(True)
        self._thumb2.setEnabled(False)
        self._thumb_placeholder.setEnabled(False)
        self._card_thumb1.setEnabled(True)
        self._card_thumb2.setEnabled(False)
        self._card_thumb_placeholder.setEnabled(False)

    def wait_loaded(self, qtbot) -> None:
        """Flush pending paint events."""
        from qtpy.QtWidgets import QApplication

        QApplication.processEvents()

    def steps(self):
        return [self.swap_images, self.disable_all]

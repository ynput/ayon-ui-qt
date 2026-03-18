from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Callable

from qtpy.QtCore import (
    QEasingCurve,
    QRect,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
)
from qtpy.QtGui import QIcon, QPainter, QPaintEvent, QPixmap
from qtpy.QtWidgets import QPushButton, QStyle, QStyleOptionButton

from .. import get_ayon_style
from ..image_cache import ImageCache
from ..variants import QPushButtonVariants


class AYEntityThumbnail(QPushButton):
    def __init__(
        self,
        src: Path | str = "",
        file_cacher: Callable | None = None,
        size: tuple = (85, 48),
        fade_duration: int = 0,
        **kwargs,
    ):
        """A widget that displays a thumbnail image for an entity, with options
        to customize the image source, caching behavior, and size."""
        self._file_cacher = file_cacher
        self._size = size
        self._variant_str: str = QPushButtonVariants.Thumbnail.value

        super().__init__(QIcon(), "", **kwargs)
        self.setStyle(get_ayon_style())

        self._src: Path | str = ""
        self._incoming_pixmap: QPixmap | None = None
        self._opacity: float = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(fade_duration)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.valueChanged.connect(self._on_fade_tick)
        self._anim.finished.connect(self._on_fade_done)

        self.set_thumbnail(src)
        self.setFixedSize(*self._size)

    def set_fade_duration(self, duration: int) -> None:
        """Set the duration of the fade animation when changing thumbnails."""
        self._anim.setDuration(duration)

    def _resolve_src(self, src: Path | str) -> Path | str:
        """Resolve a cache key or path to an existing file path."""
        if Path(src).exists():
            return src
        ic = ImageCache.get_instance()
        if self._file_cacher:
            return ic.get(str(src), partial(self._file_cacher, src))
        if ic.has(str(src)):
            return ic.get_path(str(src)) or ""
        return src

    def _on_fade_tick(self, value: float) -> None:
        self._opacity = value
        self.update()

    def _on_fade_done(self) -> None:
        pixmap = self._incoming_pixmap
        if pixmap and not pixmap.isNull():
            icon = QIcon()
            icon.addPixmap(pixmap)
            self.setIcon(icon)
            self.setIconSize(QSize(*self._size))
        else:
            self.setIcon(QIcon())
        self._incoming_pixmap = None
        self._opacity = 1.0
        self.update()

    def set_thumbnail(self, name: Path | str) -> None:
        """Set the thumbnail image for the button."""
        self._src = self._resolve_src(name)
        self._anim.stop()
        if Path(self._src).exists():
            raw = QPixmap(str(self._src))
            self._incoming_pixmap = raw.scaled(
                QSize(*self._size),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._opacity = 0.0
            self._anim.start()
        else:
            self._incoming_pixmap = None
            self._opacity = 1.0
            self.setIcon(QIcon())

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        p = QPainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        # override rect set by stylesheet
        size = QSize(*self._size)
        self.setFixedSize(size)
        option.rect = QRect(0, 0, size.width(), size.height())
        # draw base (current icon)
        get_ayon_style().drawControl(
            QStyle.ControlElement.CE_PushButton, option, p, self
        )
        # overlay incoming pixmap with fade opacity
        if self._incoming_pixmap and not self._incoming_pixmap.isNull():
            x = (size.width() - self._incoming_pixmap.width()) // 2
            y = (size.height() - self._incoming_pixmap.height()) // 2
            p.save()
            p.setClipRect(QRect(1, 1, size.width() - 2, size.height() - 2))
            p.setOpacity(self._opacity)
            p.drawPixmap(x, y, self._incoming_pixmap)
            p.restore()


if __name__ == "__main__":
    from ..tester import Style, test
    from .container import AYContainer

    def resource_loader(key):
        rsrc_dir = Path(__file__).parent.parent / "resources"
        for ext in ("jpg", "png"):
            fpath = rsrc_dir / f"{key}.{ext}"
            if fpath.exists():
                # we could also resize the image here.
                return fpath
        return ""

    def build():
        w = AYContainer(
            layout=AYContainer.Layout.HBox,
            margin=8,
            layout_margin=8,
            layout_spacing=4,
        )
        w.add_widget(
            AYEntityThumbnail(src="avatar1", file_cacher=resource_loader)
        )
        w.add_widget(
            AYEntityThumbnail(
                src="SMPTE_Color_Bars", file_cacher=resource_loader
            )
        )
        delayed = AYEntityThumbnail(
            src="avatar2", file_cacher=resource_loader, fade_duration=0
        )
        w.add_widget(delayed)

        # simulate thumbnail update after some time
        delayed.set_fade_duration(1000)
        QTimer.singleShot(1500, lambda: delayed.set_thumbnail("avatar3"))
        return w

    test(build, style=Style.AyonStyleOverCSS)

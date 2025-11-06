from __future__ import annotations

from pathlib import Path
from typing import Callable
from functools import partial

from qtpy.QtCore import QSize
from qtpy.QtWidgets import QPushButton
from qtpy.QtGui import QIcon, QPixmap

from ..image_cache import ImageCache


class AYEntityThumbnail(QPushButton):
    def __init__(
        self,
        src: Path | str = "",
        file_cacher: Callable | None = None,
        size: tuple = (85, 48),
        **kwargs,
    ):
        """A widget that displays a thumbnail image for an entity, with options
        to customize the image source, caching behavior, and size."""
        self._src = src
        self._file_cacher = file_cacher
        self._size = size
        self._variant = "thumbnail"

        if not Path(self._src).exists() and self._file_cacher:
            ic = ImageCache.get_instance()
            self._src = ic.get(
                str(self._src), partial(self._file_cacher, self._src)
            )

        super().__init__(QIcon(), "", **kwargs)

        self.set_thumbnail(self._src)
        self.setFixedSize(*self._size)

    def set_thumbnail(self, name: Path | str):
        """Set the thumbnail image for the button."""
        if not Path(self._src).exists() and self._file_cacher:
            ic = ImageCache.get_instance()
            self._src = ic.get(
                str(self._src), partial(self._file_cacher, self._src)
            )
        if Path(self._src).exists():
            pxm = QPixmap(str(self._src))
            qicon = QIcon()
            qicon.addPixmap(pxm)
            self.setIcon(qicon)
            self.setIconSize(QSize(*self._size))
        else:
            self.setIcon(QIcon())


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
        return w

    test(build, style=Style.Widget)

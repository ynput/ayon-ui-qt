from __future__ import annotations

from os.path import normpath
from typing import Optional

from qtpy import QtCore, QtWidgets

from ..utils import clear_layout
from .. import get_ayon_style
from .layouts import AYHBoxLayout
from ..variants import QLabelVariants
from .label import AYLabel


class AYEntityPathSegment(AYLabel):
    def __init__(
        self,
        text,
        parent=None,
        variant: AYLabel.Variants = AYLabel.Variants.Default,
        dim=True,
        rel_text_size=-2,
    ):
        super().__init__(text, parent=parent)
        self._variant_str: str = variant.value


class AYEntityPath(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setStyle(get_ayon_style())
        self._path = ""
        self._path_segments = []
        self._entity_id = None
        self.setLayout(AYHBoxLayout(self))

        self.entity_path = "Project/assets/characters/robot/Render"

    @property
    def entity_path(self):
        return self._path

    @entity_path.setter
    def entity_path(self, value):
        self._path_segments = normpath(value).split("/")
        self._path = value
        self._build()

    def _build(self):
        lyt = self.layout()
        if not lyt:
            return

        clear_layout(lyt)
        for p in self._path_segments:
            w = AYEntityPathSegment(p, parent=self)
            lyt.addWidget(w)
            if p != self._path_segments[-1]:
                lyt.addWidget(AYEntityPathSegment("/", parent=self))
        lyt.addStretch(100)

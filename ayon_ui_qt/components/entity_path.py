from typing import Optional
from os.path import normpath

from qtpy import QtCore, QtWidgets

from .layouts import AYHBoxLayout
from ..utils import clear_layout


class AYEntityPathSegment(QtWidgets.QLabel):
    def __init__(self, text, parent=None, variant="head"):
        super().__init__(text, parent=parent)
        self._variant = variant

    def get_variant(self) -> str:
        return self._variant

    def set_variant(self, value: str):
        self._variant = value

    variant = QtCore.Property(str, get_variant, set_variant)  # type: ignore


class AYEntityPath(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
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

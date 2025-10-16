from typing import Optional
from qtpy import QtCore, QtGui, QtWidgets

from .layouts import AYHBoxLayout


class AYEntityPathSegment(QtWidgets.QLabel):
    def __init__(self, text, parent=None, variant="head"):
        super().__init__(text, parent=parent)
        self._variant = variant
        self.setStyleSheet(
            """AYEntityPathSegment {
                color: #8B9198;
                background-color: transparent;
                font-size: 14px;
            }
            AYEntityPathSegment[variant="tail"]:hover {
                color: #ffffff;
                background-color: #333333;
                padding: 3px;
            }
            """
        )

    def get_variant(self) -> str:
        return self._variant

    def set_variant(self, value: str):
        self._variant = value

    variant = QtCore.Property(str, get_variant, set_variant)


class AYEntityPath(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._path = ""
        self._path_segments = []
        self._entity_id = None

        self.entity_path = "Project/assets/characters/robot/Render"
        self._build()

        # self.setStyleSheet(
        #     "EntityPath {align: left;}"
        # )

    @property
    def entity_path(self):
        return self._path

    @entity_path.setter
    def entity_path(self, value):
        self._path_segments = value.split("/")
        self._path = value

    def _build(self):
        lyt = AYHBoxLayout(self)
        self._head = AYEntityPathSegment(self._path_segments[0], parent=self)
        self._mid = AYEntityPathSegment("...", parent=self, variant="mid")
        self._tail = AYEntityPathSegment(
            self._path_segments[-1], parent=self, variant="tail"
        )
        lyt.addWidget(self._head)
        lyt.addWidget(AYEntityPathSegment("/", parent=self))
        lyt.addWidget(self._mid)
        lyt.addWidget(AYEntityPathSegment("/", parent=self))
        lyt.addWidget(self._tail)
        lyt.addSpacerItem(
            QtWidgets.QSpacerItem(
                0, 0, QtWidgets.QSizePolicy.Policy.MinimumExpanding
            )
        )

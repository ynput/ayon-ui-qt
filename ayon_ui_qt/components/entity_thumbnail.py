from qtpy.QtWidgets import QPushButton, QSizePolicy
from qtpy.QtGui import QIcon


class AYEntityThumbnail(QPushButton):
    def __init__(self, **kwargs):
        self._icon = QIcon()
        super().__init__(self._icon, "", **kwargs)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(85, 48)

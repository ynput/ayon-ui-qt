from qtpy import QtCore, QtGui, QtWidgets


class AYEntityThumbnail(QtWidgets.QPushButton):
    def __init__(self, parent):
        self._icon = QtGui.QIcon()
        super().__init__(self._icon, "", parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setFixedSize(85, 48)

        # self.setStyleSheet(
        #     """AYEntityThumbnail {
        #         background-color: #000000;
        #         border: 2px #8B9198;
        #         border-style: solid;
        #         border-radius: 4px;
        #     }
        #     """
        # )

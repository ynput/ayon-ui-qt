from qtpy import QtCore, QtGui, QtWidgets


class AYHBoxLayout(QtWidgets.QHBoxLayout):
    def __init__(self, *args, margin=4, spacing=4):
        super().__init__(*args)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)


class AYVBoxLayout(QtWidgets.QVBoxLayout):
    def __init__(self, *args, margin=4, spacing=4):
        super().__init__(*args)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)


class AYGridLayout(QtWidgets.QGridLayout):
    def __init__(self, *args, margin=4, spacing=4):
        super().__init__(*args)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

from qtpy import QtCore, QtGui, QtWidgets


class AYUserImage(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        # file path to icon
        self._src = kwargs.pop("src", None)
        # short user name
        self._name = kwargs.pop("name", None)
        # full user name
        self._full_name = kwargs.pop("full_name", None)
        # pixmap size
        self._size = kwargs.pop("size", 30)
        # green outline if true, light grey otherwise
        self._highlight = kwargs.pop("highlight", False)
        # enable / disable outline
        self._outline = kwargs.pop("outline", True)
        # background color for initials
        self._bg = QtGui.QColor("#484875")
        self._grey = QtGui.QColor(225, 225, 225)
        self._green = QtGui.QColor(107, 225, 172)

        super().__init__(*args, **kwargs)

        self.setStyleSheet("background-color: transparent;")

        self.set_image()

    def set_image(self):
        self.pxm = QtGui.QPixmap(self._size, self._size)
        self.pxm.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(self.pxm)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Define colors
        outline_color = self._green if self._highlight else self._grey

        if self._src:
            # Load and draw src icon file in a circle
            source_pixmap = QtGui.QPixmap(self._src)
            if not source_pixmap.isNull():
                # Scale the source image to fit within the circle (with some
                # margin for outline)

                # Leave space for outline
                inner_size = self._size - (2 if self._outline else 0)
                scaled_pixmap = source_pixmap.scaled(
                    inner_size,
                    inner_size,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )

                # Create circular clipping path
                clip_path = QtGui.QPainterPath()
                clip_path.addEllipse(0, 0, self._size, self._size)
                painter.setClipPath(clip_path)

                # Draw the scaled image centered
                x = (self._size - scaled_pixmap.width()) // 2
                y = (self._size - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)

                # Reset clipping
                painter.setClipping(False)
            else:
                print(f"Could not load src {self._src}")
        else:
            initials = "?"
            if self._full_name:
                initials = "".join([p[0] for p in self._full_name.split()])
            elif self._name:
                initials = self._name[0]

            # Draw a circle with white initials over a color background

            # Fill circle with grey background
            painter.setBrush(QtGui.QBrush(QtGui.QColor(self._bg)))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, self._size, self._size)

            # Draw white initials
            painter.setPen(QtGui.QColor(255, 255, 255))
            font = painter.font()
            point_size = max(8, self._size // 2)
            font.setPointSize(point_size)
            painter.setFont(font)

            painter.drawText(
                QtCore.QRect(0, 0, self._size, self._size),
                QtCore.Qt.AlignmentFlag.AlignCenter,
                initials.upper(),
            )

        # Draw outline
        if self._outline or self._highlight:
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.setPen(QtGui.QPen(outline_color, 1))
            painter.drawEllipse(1, 1, self._size - 2, self._size - 2)

        painter.end()

        # Set the pixmap to the label
        self.setPixmap(self.pxm)

    def update_params(self, src, full_name):
        self._src = src
        self._full_name = full_name
        self.set_image()


if __name__ == "__main__":
    from ..tester import test
    from .layouts import AYHBoxLayout

    def build():
        fp = "/Volumes/plp_T5/personal/plp/plp_avatar.jpg.png"
        w = QtWidgets.QWidget()
        lyt = AYHBoxLayout(w, margin=16)
        lyt.addWidget(AYUserImage(src=fp))
        lyt.addWidget(AYUserImage(src=fp, highlight=True))
        lyt.addWidget(AYUserImage(src=fp, outline=False))
        lyt.addWidget(AYUserImage(full_name="Oliver Cromwell"))
        lyt.addWidget(AYUserImage(name="Oliver"))
        lyt.addWidget(AYUserImage(highlight=True))
        lyt.addWidget(AYUserImage(name="Oliver", outline=False))
        lyt.addWidget(AYUserImage(name="Oliver", outline=False, highlight=True))
        lyt.addWidget(AYUserImage(src=fp, outline=False, size=60))
        lyt.addWidget(AYUserImage(src=fp, highlight=True, size=60))
        lyt.addWidget(AYUserImage(full_name="Oliver Cromwell", size=60))
        lyt.addWidget(AYUserImage(name="Oliver", outline=False, size=60))
        return w

    test(build)

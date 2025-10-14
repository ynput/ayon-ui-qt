from qtpy import QtCore, QtGui, QtWidgets
try:
    from qtmaterialsymbols import get_icon
except ImportError:
    from ayon_ui_qt.vendor.qtmaterialsymbols import get_icon


class AYLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        self._tag = kwargs.pop("tag", None)
        self._dim = kwargs.pop("dim", False)
        self._icon = kwargs.pop("icon", None)
        self._icon_color = kwargs.pop("icon_color", "#ffffff")
        super().__init__(*args, **kwargs)

        self.setStyleSheet(
            """
            AYLabel {
                font-size: 14px;
                color:#deffffff;
                background-color: transparent;
            }

            AYLabel[tag="h2"] {
                font-size: 16px;
            }

            AYLabel[tag="h3"] {
                font-size: 14px;
            }

            AYLabel[tag="h4"] {
                font-size: 12px;
            }

            AYLabel[tag="h5"] {
                font-size: 10px;
            }

            AYLabel[dim="true"] {
                font-size: 14px;
                color:#80ffffff;
                background-color: transparent;
            }

            AYLabel[tag="h2"][dim="true"] {
                font-size: 16px;
            }

            AYLabel[tag="h3"][dim="true"] {
                font-size: 14px;
            }

            AYLabel[tag="h4"][dim="true"] {
                font-size: 12px;
            }

            AYLabel[tag="h4"][dim="true"] {
                font-size: 10px;
            }
            """
        )

        self.set_icon()

    def set_icon(self):
        if self._icon:
            icn = get_icon(self._icon, color=self._icon_color)
            self.setPixmap(icn.pixmap())

    def get_tag(self):
        return self._tag

    def set_tag(self, value):
        self._tag = value

    def get_dim(self):
        return self._dim

    def set_dim(self, value):
        self._dim = value

    tag = QtCore.Property(str, get_tag, set_tag)
    dim = QtCore.Property(bool, get_dim, set_dim)

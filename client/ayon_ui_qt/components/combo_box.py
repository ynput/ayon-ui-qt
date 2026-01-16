from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Literal, Optional, get_args, overload

try:
    from qtmaterialsymbols import get_icon  # type: ignore
except ImportError:
    from ..vendor.qtmaterialsymbols import get_icon
from qtpy import QtCore, QtWidgets
from qtpy.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPaintEvent,
    QPalette,
    QStandardItemModel,
)

# Configure logging
logger = logging.getLogger(__name__)


# Size variants
Size = Literal["full", "short", "icon"]

ALL_STATUSES = [
    {
        "text": "Not ready",
        "short_text": "NRD",
        "icon": "fiber_new",
        "color": "#434a56",
    },
    {
        "text": "Ready to start",
        "short_text": "RDY",
        "icon": "timer",
        "color": "#bababa",
    },
    {
        "text": "In progress",
        "short_text": "PRG",
        "icon": "play_arrow",
        "color": "#3498db",
    },
    {
        "text": "Pending review",
        "short_text": "RVW",
        "icon": "visibility",
        "color": "#ff9b0a",
    },
    {
        "text": "Approved",
        "short_text": "APP",
        "icon": "task_alt",
        "color": "#00f0b4",
    },
    {
        "text": "On hold",
        "short_text": "HLD",
        "icon": "back_hand",
        "color": "#fa6e46",
    },
    {
        "text": "Omitted",
        "short_text": "OMT",
        "icon": "block",
        "color": "#cb1a1a",
    },
]


@dataclass
class Item:
    text: str
    short_text: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


def txt_color(bg_color: str | QColor) -> QColor:
    value = (
        QColor(bg_color).valueF()
        if isinstance(bg_color, str)
        else bg_color.valueF()
    )
    return QColor("#eee") if value < 0.9 else QColor("#222")


class AYComboBox(QtWidgets.QComboBox):
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        items: List[dict] | None = None,
        size: Size = "full",
        height: int = 30,
        placeholder: Optional[str] = None,
        inverted: bool = False,
        disabled: bool = False,
        icon_size: int = 20,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        from .. import get_ayon_style

        self.setStyle(get_ayon_style())
        self.setMouseTracking(True)
        self.setMaximumHeight(height)

        # Initialize properties
        self._size: str = size
        self._height: int = height
        self._placeholder: Optional[str] = placeholder
        self._inverted: bool = inverted
        self._disabled: bool = disabled
        self._item_list: list = [Item(**s) for s in items] if items else []
        self._icon_size: int = icon_size
        self._custom_options: List[Item] = []

        self.update_items()

    @overload
    def add_item(self, item: dict[str, str]):
        pass

    @overload
    def add_item(self, item: Item):
        pass

    def add_item(self, item):
        it = Item(**item) if isinstance(item, dict) else item
        self._item_list.append(it)
        self.update_items()

    def update_items(self, item_list: list[dict] | None = None):
        if item_list:
            self.setModel(QStandardItemModel())
            self._item_list = [Item(**s) for s in item_list]

        bg_color = self.palette().color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Window
        )

        for idx, item in enumerate(self._item_list):
            icon = get_icon(
                item.icon,
                color_normal=item.color,
                color_selected=item.color,
            )

            text = str(
                item.text
                if self._size == "full"
                else item.short_text
                if self._size == "short"
                else ""
            )

            if idx >= self.count():
                self.addItem(icon, text)
                self.setItemData(idx, item, QtCore.Qt.ItemDataRole.UserRole)
            else:
                self.setItemIcon(idx, icon)
                self.setItemText(idx, text)

            self.setItemData(
                idx,
                QBrush(item.color),
                QtCore.Qt.ItemDataRole.ForegroundRole,
            )
            self.setItemData(
                idx,
                QBrush(bg_color),
                QtCore.Qt.ItemDataRole.BackgroundRole,
            )

    def set_inverted(self, state: bool):
        self._inverted = state
        self.update_items()

    def set_size(self, size: str):
        self._size = size
        self.update_items()

    def sizeHint(self) -> QtCore.QSize:
        if self.testAttribute(QtCore.Qt.WidgetAttribute.WA_StyleSheet):
            from .. import get_ayon_style

            option = QtWidgets.QStyleOptionComboBox()
            self.initStyleOption(option)
            return get_ayon_style().sizeFromContents(
                QtWidgets.QStyle.ContentsType.CT_ComboBox,
                option,
                self.rect().size(),
                self,
            )
        return super().sizeHint()

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        if self.testAttribute(QtCore.Qt.WidgetAttribute.WA_StyleSheet):
            from .. import get_ayon_style

            p = QPainter(self)
            option = QtWidgets.QStyleOptionComboBox()
            self.initStyleOption(option)
            _style = get_ayon_style()
            # option.palette.setBrush(QPalette.ColorRole.Base, _style.model.base_palette.base())
            # print(f"CBB: {option.palette.base()}")
            _style.drawComplexControl(
                QtWidgets.QStyle.ComplexControl.CC_ComboBox, option, p, self
            )
            if self.currentIndex() < 0 and self.placeholderText():
                option.palette.setBrush(
                    QPalette.ColorRole.ButtonText,
                    option.palette.placeholderText(),
                )
                option.currentText = self.placeholderText()
            _style.drawControl(
                QtWidgets.QStyle.ControlElement.CE_ComboBoxLabel,
                option,
                p,
                self,
            )
            return
        super().paintEvent(arg__1)


# TEST  =======================================================================

if __name__ == "__main__":
    """Run the StatusSelect test interface or print status info."""
    import os

    from ..tester import Style, test
    from .container import AYContainer

    def build():
        w = AYContainer(
            layout=AYContainer.Layout.VBox,
            variant="low",
            layout_spacing=6,
            layout_margin=10,
        )
        w.setMinimumWidth(250)
        inv = QtWidgets.QCheckBox("inverted", parent=w)
        w.addWidget(inv)
        cb = AYComboBox(items=ALL_STATUSES)
        w.addWidget(cb, stretch=0, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        size = QtWidgets.QComboBox(w)
        size.addItems([s for s in get_args(Size)])
        w.addWidget(size)

        # configure
        inv.clicked.connect(lambda x: cb.set_inverted(x))
        size.currentTextChanged.connect(lambda x: cb.set_size(x))

        return w

    os.environ["QT_SCALE_FACTOR"] = "1"

    test(build, style=Style.Widget)

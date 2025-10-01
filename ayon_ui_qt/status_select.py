from __future__ import annotations

import copy
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from qt_material_icons import MaterialIcon
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QStyle
from qtpy.QtGui import QColor, QBrush, QPen, QIcon, QPalette

# Configure logging
logger = logging.getLogger(__name__)

# Status states
STATUS_STATES = ("not_started", "in_progress", "done", "blocked")

# Size variants
STATUS_SIZES = ("full", "short", "icon")

ALL_STATUSES = [
    {
        "text": "Not ready",
        "short_name": "NRD",
        "icon": "fiber_new",
        "color": "#434a56",
    },
    {
        "text": "Ready to start",
        "short_name": "RDY",
        "icon": "timer",
        "color": "#bababa",
    },
    {
        "text": "In progress",
        "short_name": "PRG",
        "icon": "play_arrow",
        "color": "#3498db",
    },
    {
        "text": "Pending review",
        "short_name": "RVW",
        "icon": "visibility",
        "color": "#ff9b0a",
    },
    {
        "text": "Approved",
        "short_name": "APP",
        "icon": "task_alt",
        "color": "#00f0b4",
    },
    {
        "text": "On hold",
        "short_name": "HLD",
        "icon": "back_hand",
        "color": "#fa6e46",
    },
    {
        "text": "Omitted",
        "short_name": "OMT",
        "icon": "block",
        "color": "#cb1a1a",
    },
]


@dataclass
class Item:
    text: str
    short_name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    original_name: Optional[str] = None


def txt_color(bg_color: str | QColor) -> QColor:
    value = (
        QColor(bg_color).valueF()
        if isinstance(bg_color, str)
        else bg_color.valueF()
    )
    return QColor("#eee") if value < 0.9 else QColor("#222")


def colorize_icon(icon: QIcon, icon_color, mode=QIcon.Mode.Normal):
    icon_size = icon.availableSizes()[0]
    pixmap = QtGui.QPixmap(icon.pixmap(icon_size))
    pntr = QtGui.QPainter(pixmap)
    pntr.setCompositionMode(
        QtGui.QPainter.CompositionMode.CompositionMode_SourceIn
    )
    pntr.fillRect(pixmap.rect(), icon_color)
    pntr.end()
    icon.addPixmap(pixmap, mode=mode)


class StatusItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None, padding: int = 4) -> None:
        super().__init__(parent)
        self._padding = padding
        self._icon_size = 16
        self._icon_text_spacing = 8

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        # enable mouse hover + repaint
        option.widget.setMouseTracking(True)

        # change colors for highlight
        highlight_color = option.palette.color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Light
        )

        if option.state & QStyle.StateFlag.State_MouseOver:
            option.palette.setColor(
                QPalette.ColorGroup.Active,
                QPalette.ColorRole.Highlight,
                highlight_color,
            )
            option.palette.setColor(
                QPalette.ColorGroup.Active,
                QPalette.ColorRole.HighlightedText,
                index.data(QtCore.Qt.ItemDataRole.ForegroundRole).color(),
            )
        elif option.state & QStyle.StateFlag.State_Selected:
            option.palette.setColor(
                QPalette.ColorGroup.Active,
                QPalette.ColorRole.Highlight,
                index.data(QtCore.Qt.ItemDataRole.ForegroundRole).color(),
            )
            option.palette.setColor(
                QPalette.ColorGroup.Active,
                QPalette.ColorRole.HighlightedText,
                index.data(QtCore.Qt.ItemDataRole.BackgroundRole).color(),
            )

        super().paint(painter, option, index)

    def sizeHint(
        self, option: QtWidgets.QStyleOptionViewItem, index
    ) -> QtCore.QSize:
        """Calculate size hint including padding."""
        status: Item = index.data(QtCore.Qt.ItemDataRole.UserRole)

        if not status:
            return super().sizeHint(option, index)

        # Calculate text dimensions
        font_metrics = option.fontMetrics
        text_size = font_metrics.size(0, status.text)

        # Calculate content dimensions
        content_width = text_size.width()
        content_height = max(text_size.height(), self._icon_size)

        # Add icon space if present
        if status.icon:
            content_width += self._icon_size + self._icon_text_spacing

        # Add padding to get total size
        total_width = content_width + self._padding + self._padding
        total_height = content_height + self._padding + self._padding

        # Ensure minimum height
        total_height = max(total_height, 32)

        return QtCore.QSize(total_width, total_height)


class AYComboBox(QtWidgets.QComboBox):
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        size: str = "full",
        height: int = 30,
        placeholder: Optional[str] = None,
        inverted: bool = False,
        disabled: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.setMouseTracking(True)
        self.setItemDelegate(StatusItemDelegate(self))

        # Initialize properties
        self._size: str = size
        self._height: int = height
        self._placeholder: Optional[str] = placeholder
        self._inverted: bool = inverted
        self._disabled: bool = disabled
        self._status_collection: list = [Item(**s) for s in ALL_STATUSES]
        self._current_status: Optional[Item] = None
        self._icon_size: int = 20
        self._show_icons: bool = True
        self._custom_options: List[Item] = []

        self.setMinimumHeight(self._height)
        self.setMaximumHeight(self._height)

        # Set size policy to expand horizontally
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        self.set_data()

    def set_data(self):
        bg_color = self.palette().color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Window
        )

        for idx, status in enumerate(self._status_collection):
            icon = MaterialIcon(status.icon)
            icon.set_color(status.color)
            colorize_icon(
                icon,
                bg_color if self._inverted else status.color,
                mode=QIcon.Mode.Selected,
            )

            if idx >= self.count():
                self.addItem(icon, status.text)
                self.setItemData(idx, status, QtCore.Qt.ItemDataRole.UserRole)
            else:
                self.setItemIcon(idx, icon)

            self.setItemData(
                idx,
                QBrush(status.color),
                QtCore.Qt.ItemDataRole.ForegroundRole,
            )
            self.setItemData(
                idx,
                QBrush(bg_color),
                QtCore.Qt.ItemDataRole.BackgroundRole,
            )

    def set_inverted(self, state: bool):
        self._inverted = state
        self.set_data()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Custom paint event to render the selected status with its color.
        The menu items are drawn by the item delegate."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        bg_color = self.palette().color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Window
        )

        # Get the current selected status
        current_index = self.currentIndex()
        if current_index >= 0:
            status: Item = self.itemData(
                current_index, QtCore.Qt.ItemDataRole.UserRole
            )
            if status and status.color:
                # Paint background with status color
                rect = self.rect()
                painter.save()
                painter.setBrush(
                    QBrush(
                        QColor(status.color) if self._inverted else bg_color
                    )
                )
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, 4, 4)
                painter.restore()

                # adjust label color based on background luminance
                fg_color = bg_color if self._inverted else QColor(status.color)
                painter.setPen(fg_color)

                # Calculate content area with padding
                content_rect = rect.adjusted(
                    10, 0, -10, 0
                )  # Leave space for dropdown arrow

                # Draw icon if available and enabled
                icon_rect = None
                if status.icon and self._show_icons:
                    icon_y = (
                        content_rect.top()
                        + (content_rect.height() - self._icon_size) // 2
                    )
                    icon_rect = QtCore.QRect(
                        content_rect.left(),
                        icon_y,
                        self._icon_size,
                        self._icon_size,
                    )

                    try:
                        icon = self.itemIcon(current_index)
                        pixmap = icon.pixmap(
                            self._icon_size,
                            self._icon_size,
                            mode=QIcon.Mode.Selected,
                        )
                        painter.drawPixmap(icon_rect.topLeft(), pixmap)
                    except Exception as e:
                        logger.warning(
                            f"Failed to load icon '{status.icon}': {e}"
                        )

                # Calculate text rectangle (adjust for icon if present)
                text_rect = QtCore.QRect(content_rect)
                if icon_rect:
                    # Add spacing between icon and text (8px like in ItemDelegate)
                    icon_text_spacing = 8
                    text_rect.setLeft(icon_rect.right() + icon_text_spacing)

                # Draw the status text
                painter.drawText(
                    text_rect,
                    QtCore.Qt.AlignmentFlag.AlignVCenter,
                    status.text,
                )

                return

        # Fall back to default painting if no custom status
        super().paintEvent(event)


# TEST  =======================================================================

if __name__ == "__main__":
    """Run the StatusSelect test interface or print status info."""
    import os
    from ayon_ui_qt.tester import test

    def build():
        w = QtWidgets.QFrame()
        w.setMouseTracking(True)
        w.setContentsMargins(10, 10, 10, 10)
        l = QtWidgets.QVBoxLayout(w)
        inv = QtWidgets.QCheckBox("inverted", parent=w)
        l.addWidget(inv)
        cb = AYComboBox()
        l.addWidget(cb, stretch=0, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        # configure
        inv.clicked.connect(lambda x: cb.set_inverted(x))

        return w

    os.environ["QT_SCALE_FACTOR"] = "1"

    test(build, use_css=False)

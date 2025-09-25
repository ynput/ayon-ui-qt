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

# Configure logging
logger = logging.getLogger(__name__)

# Status states
STATUS_STATES = ("not_started", "in_progress", "done", "blocked")

# Size variants
STATUS_SIZES = ("full", "short", "icon")

ALL_STATUSES = [
    {
        "name": "Not ready",
        "short_name": "NRD",
        "icon": "fiber_new",
        "color": "#434a56",
        "state": "not_started",
    },
    {
        "name": "Ready to start",
        "short_name": "RDY",
        "icon": "timer",
        "color": "#bababa",
        "state": "not_started",
    },
    {
        "name": "In progress",
        "short_name": "PRG",
        "icon": "play_arrow",
        "color": "#3498db",
        "state": "in_progress",
    },
    {
        "name": "Pending review",
        "short_name": "RVW",
        "icon": "visibility",
        "color": "#ff9b0a",
        "state": "in_progress",
    },
    {
        "name": "Approved",
        "short_name": "APP",
        "icon": "task_alt",
        "color": "#00f0b4",
        "state": "done",
    },
    {
        "name": "On hold",
        "short_name": "HLD",
        "icon": "back_hand",
        "color": "#fa6e46",
        "state": "blocked",
    },
    {
        "name": "Omitted",
        "short_name": "OMT",
        "icon": "block",
        "color": "#cb1a1a",
        "state": "blocked",
    },
]


@dataclass
class Status:
    name: str
    short_name: Optional[str] = None
    state: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    original_name: Optional[str] = None


class ItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None, padding: int = 4) -> None:
        super().__init__(parent)
        self._padding = padding
        self._icon_size = 16
        self._icon_text_spacing = 8

    def set_padding(self, padding: int) -> None:
        """Update padding configuration."""
        self._padding = padding

    def get_content_rect(
        self, option: QtWidgets.QStyleOptionViewItem
    ) -> QtCore.QRect:
        """Calculate content area after applying padding."""
        return option.rect.adjusted(
            self._padding, self._padding, -self._padding, -self._padding
        )

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index,
    ):
        status: Status = index.data(QtCore.Qt.ItemDataRole.UserRole)

        if not status or not status.color:
            super().paint(painter, option, index)
            return

        # Determine hover state and colors
        is_hovered = option.state & QtWidgets.QStyle.StateFlag.State_MouseOver
        bg_color = (
            QtGui.QColor(status.color)
            if is_hovered
            else option.backgroundBrush.color()
        )
        text_color = (
            QtGui.QColor("#fff") if is_hovered else QtGui.QColor(status.color)
        )

        # Fill entire rect (including padding) for proper click/hover area
        painter.fillRect(option.rect, bg_color)
        painter.setPen(text_color)

        # Get content area after padding
        content_rect = self.get_content_rect(option)

        # Draw icon if available
        icon_rect = None
        if status.icon:
            icon_y = (
                content_rect.top()
                + (content_rect.height() - self._icon_size) // 2
            )
            icon_rect = QtCore.QRect(
                content_rect.left(), icon_y, self._icon_size, self._icon_size
            )

            try:
                from qt_material_icons import MaterialIcon

                icon = MaterialIcon(status.icon)
                pixmap = icon.pixmap(self._icon_size, self._icon_size)
                painter.drawPixmap(icon_rect.topLeft(), pixmap)
            except Exception as e:
                logger.warning(f"Failed to load icon '{status.icon}': {e}")

        # Calculate text rectangle
        text_rect = QtCore.QRect(content_rect)
        if icon_rect:
            text_rect.setLeft(icon_rect.right() + self._icon_text_spacing)

        # Draw text
        painter.drawText(
            text_rect,
            QtCore.Qt.AlignmentFlag.AlignVCenter
            | QtCore.Qt.AlignmentFlag.AlignLeft,
            status.name,
        )

    def sizeHint(
        self, option: QtWidgets.QStyleOptionViewItem, index
    ) -> QtCore.QSize:
        """Calculate size hint including padding."""
        status: Status = index.data(QtCore.Qt.ItemDataRole.UserRole)

        if not status:
            return super().sizeHint(option, index)

        # Calculate text dimensions
        font_metrics = option.fontMetrics
        text_size = font_metrics.size(0, status.name)

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


class StatusSelect(QtWidgets.QComboBox):
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        size: str = "full",
        height: int = 30,
        placeholder: Optional[str] = None,
        disabled: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)

        # Initialize properties
        self._size: str = size
        self._height: int = height
        self._placeholder: Optional[str] = placeholder
        self._disabled: bool = disabled
        self._status_collection: list = [Status(**s) for s in ALL_STATUSES]
        self._current_status: Optional[Status] = None
        self._icon_size: int = 20
        self._show_icons: bool = True
        self._custom_options: List[Status] = []

        self.setMinimumHeight(self._height)
        self.setMaximumHeight(self._height)

        # Set size policy to expand horizontally
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        self.setItemDelegate(ItemDelegate(self))

        for status in self._status_collection:
            self.addItem(status.name)
            self.setItemData(
                self.count() - 1,
                status,
                QtCore.Qt.ItemDataRole.UserRole,
            )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Custom paint event to render the selected status with its color."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Get the current selected status
        current_index = self.currentIndex()
        if current_index >= 0:
            status: Status = self.itemData(
                current_index, QtCore.Qt.ItemDataRole.UserRole
            )
            if status and status.color:
                # Paint background with status color
                rect = self.rect()
                painter.fillRect(rect, QtGui.QColor(status.color))
                l = QtGui.QColor(status.color).valueF()
                painter.setPen(
                    QtGui.QColor("#fff") if l < 0.8 else QtGui.QColor("#000")
                )  # White text on colored background

                # Calculate content area with padding
                content_rect = rect.adjusted(
                    10, 0, -30, 0
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
                        icon = MaterialIcon(status.icon)
                        pixmap = icon.pixmap(self._icon_size, self._icon_size)
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
                    status.name,
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
        w = StatusSelect()
        return w

    os.environ["QT_SCALE_FACTOR"] = "1"

    test(build)

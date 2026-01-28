"""AYFilter component for multi-select filtering with tags and dropdown.

This module provides:
- FilterItem: Data model for filter options
- FilterCheckboxDelegate: Custom delegate for checkbox-style rendering
- FilterDropdownPopup: Floating popup for filter selection
- AYFilter: Main filter widget with tag bar and dropdown selection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QModelIndex, QPersistentModelIndex, Qt, Signal
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QStyle, QStyleOptionViewItem

from .. import get_ayon_style
from ..variants import QFrameVariants, QStyledItemDelegateVariants

from .buttons import AYButton
from .container import AYContainer
from .frame import AYFrame
from .label import AYLabel
from .layouts import AYVBoxLayout
from .tag import AYTag

logger = logging.getLogger(__name__)


@dataclass
class FilterItem:
    """Data model for a single filter option.

    Attributes:
        key: Unique identifier for the filter.
        label: Display text shown in dropdown and tags.
        selected: Current selection state.
        color: Optional background color for tag display.
        icon: Optional material icon name.
        enabled: Whether the filter can be toggled.
    """

    key: str
    label: str
    selected: bool = False
    color: str | None = field(default=None)
    icon: str | None = field(default=None)
    enabled: bool = True

    def __hash__(self) -> int:
        """Return hash based on key."""
        return hash(self.key)

    def __eq__(self, other: object) -> bool:
        """Compare equality based on key."""
        if isinstance(other, FilterItem):
            return self.key == other.key
        return False


class FilterCheckboxDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate for rendering filter items with checkbox indicators.

    Draws a small square checkbox indicator on the right side of each item.
    Checked items display an X icon inside the checkbox.

    Attributes:
        CHECKBOX_SIZE: Size of the checkbox indicator in pixels.
        CHECKBOX_MARGIN: Margin around the checkbox.
        TEXT_PADDING: Padding for the text from the left edge.
    """

    CHECKBOX_SIZE = 16
    CHECKBOX_MARGIN = 8
    TEXT_PADDING = 12

    Variants = QStyledItemDelegateVariants

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        variant: Variants = Variants.Default,
    ) -> None:
        """Initialize the delegate.

        Args:
            parent: Optional parent widget.
            variant: Style variant for the delegate.
        """
        super().__init__(parent)
        self._variant_str = variant.value

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        """Paint the filter item with checkbox indicator.

        Args:
            painter: QPainter instance for rendering.
            option: Style options for the item.
            index: Model index of the item.
        """
        # Update option with model data for the drawer
        option.text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        check_state = index.data(Qt.ItemDataRole.CheckStateRole)
        option.checkState = (
            Qt.CheckState.Checked
            if check_state == Qt.CheckState.Checked
            else Qt.CheckState.Unchecked
        )

        # Delegate painting to AYONStyle
        parent = self.parent()
        widget = parent if isinstance(parent, QtWidgets.QWidget) else None
        get_ayon_style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            option,
            painter,
            widget,
        )

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QtCore.QSize:
        """Return size hint for the item.

        Args:
            option: Style options for the item.
            index: Model index of the item.

        Returns:
            Recommended size for the item.
        """
        base = super().sizeHint(option, index)
        return QtCore.QSize(base.width(), max(base.height(), 36))

    def editorEvent(
        self,
        event: QtCore.QEvent,
        model: QtCore.QAbstractItemModel,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        """Handle click events to toggle checkbox state.

        Args:
            event: The input event.
            model: The data model.
            option: Style options for the item.
            index: Model index of the item.

        Returns:
            True if the event was handled.
        """
        if event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            current = index.data(Qt.ItemDataRole.CheckStateRole)
            new_state = (
                Qt.CheckState.Unchecked
                if current == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
            model.setData(index, new_state, Qt.ItemDataRole.CheckStateRole)
            return True
        return super().editorEvent(event, model, option, index)


class FilterDropdownPopup(AYFrame):
    """Floating popup widget for filter selection.

    This popup appears below the toggle button and contains a list of
    filter items with checkboxes. It closes when clicking outside,
    pressing Escape, or when explicitly closed.

    Signals:
        item_toggled: Emitted when a filter item is toggled.
                      Passes (key: str, selected: bool).
        popup_closed: Emitted when the popup is closed.
    """

    item_toggled = Signal(str, bool)  # (key, selected)
    popup_closed = Signal()

    # Styling constants
    POPUP_MIN_WIDTH = 180
    POPUP_MAX_HEIGHT = 300

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize the dropdown popup.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent, variant=AYFrame.Variants.Low)

        # Set popup window flags
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_WindowPropagation)

        self._init_ui()

    def _init_ui(self) -> None:
        """Build the popup layout."""
        layout = AYVBoxLayout(self, margin=4, spacing=0)

        # List widget for filter items
        self._list_widget = QtWidgets.QListWidget(self)
        self._list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        )
        self._list_widget.setItemDelegate(
            FilterCheckboxDelegate(self._list_widget)
        )
        self._list_widget.setMouseTracking(True)
        self._list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._list_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self._list_widget.clicked.connect(self._on_item_clicked)

        layout.addWidget(self._list_widget)

        # Set size constraints
        self.setMinimumWidth(self.POPUP_MIN_WIDTH)
        self.setMaximumHeight(self.POPUP_MAX_HEIGHT)

    def populate(self, items: List[FilterItem]) -> None:
        """Populate the list with filter items.

        Args:
            items: List of FilterItem objects to display.
        """
        self._list_widget.clear()
        for item in items:
            self._add_list_item(item)

        # Adjust height based on content
        self._adjust_size()

    def _add_list_item(self, item: FilterItem) -> None:
        """Add a filter item to the list widget.

        Args:
            item: The FilterItem to add to the list.
        """
        list_item = QtWidgets.QListWidgetItem(item.label)
        list_item.setData(QtCore.Qt.ItemDataRole.UserRole, item.key)
        list_item.setData(
            QtCore.Qt.ItemDataRole.CheckStateRole,
            QtCore.Qt.CheckState.Checked
            if item.selected
            else QtCore.Qt.CheckState.Unchecked,
        )
        list_item.setFlags(
            list_item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable
        )
        self._list_widget.addItem(list_item)

    def _adjust_size(self) -> None:
        """Adjust popup size based on content."""
        item_count = self._list_widget.count()
        if item_count == 0:
            return

        # Calculate height based on items
        row_height = 36  # From delegate sizeHint
        content_height = item_count * row_height + 8  # 8 for margins
        height = min(content_height, self.POPUP_MAX_HEIGHT)
        self.setFixedHeight(height)

    def update_item_state(self, key: str, selected: bool) -> None:
        """Update the check state of a specific item.

        Args:
            key: Key of the item to update.
            selected: New selection state.
        """
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item and item.data(QtCore.Qt.ItemDataRole.UserRole) == key:
                item.setData(
                    QtCore.Qt.ItemDataRole.CheckStateRole,
                    QtCore.Qt.CheckState.Checked
                    if selected
                    else QtCore.Qt.CheckState.Unchecked,
                )
                break

    def show_below(self, widget: QtWidgets.QWidget) -> None:
        """Show the popup positioned below the given widget.

        Args:
            widget: Widget to position the popup below.
        """
        # Get global position of the bottom-left of the widget
        global_pos = widget.mapToGlobal(QtCore.QPoint(0, widget.height()))

        # Ensure popup doesn't go off screen
        screen = QtWidgets.QApplication.screenAt(global_pos)
        if screen:
            screen_geo = screen.availableGeometry()

            # Adjust horizontal position if needed
            if global_pos.x() + self.width() > screen_geo.right():
                global_pos.setX(screen_geo.right() - self.width())

            # Show above if not enough space below
            if global_pos.y() + self.height() > screen_geo.bottom():
                global_pos = widget.mapToGlobal(QtCore.QPoint(0, 0))
                global_pos.setY(global_pos.y() - self.height())

        self.move(global_pos)
        self.show()

    def _on_item_clicked(self, index: QtCore.QModelIndex) -> None:
        """Handle list item click - emit toggle signal.

        Args:
            index: Model index of the clicked item.
        """
        item = self._list_widget.item(index.row())
        if not item:
            return

        key = item.data(QtCore.Qt.ItemDataRole.UserRole)
        current_state = item.data(QtCore.Qt.ItemDataRole.CheckStateRole)
        new_selected = current_state == QtCore.Qt.CheckState.Checked

        self.item_toggled.emit(key, new_selected)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle key press events.

        Args:
            event: The key event.
        """
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Handle close event.

        Args:
            event: The close event.
        """
        self.popup_closed.emit()
        super().closeEvent(event)


class AYFilter(AYFrame):
    """Multi-select filter widget with tag display and dropdown selection.

    Displays selected filters as dismissible tags in a top bar, with a
    dropdown panel for selecting/deselecting filter options.

    Signals:
        filter_changed: Emitted when selection changes. Passes list of
                        selected FilterItem keys.
        filter_added: Emitted when a filter is selected. Passes the key.
        filter_removed: Emitted when a filter is deselected. Passes the key.

    Attributes:
        items: List of FilterItem objects representing available filters.
    """

    filter_changed = Signal(list)  # List[str] of selected keys
    filter_added = Signal(str)  # key of added filter
    filter_removed = Signal(str)  # key of removed filter

    Variants = QFrameVariants

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        label: str = "Sort by",
        items: List[FilterItem] | None = None,
        default_color: str = "#8fceff",
        variant: Variants = Variants.Low,
    ) -> None:
        """Initialize the filter widget.

        Args:
            parent: Optional parent widget.
            label: Text displayed before the filter tags.
            items: Initial list of filter items.
            default_color: Default tag color when item has no color set.
            variant: Frame variant for background styling.
        """
        super().__init__(parent, variant=variant, margin=0)

        self._label_text = label
        self._items: List[FilterItem] = list(items) if items else []
        self._default_color = default_color
        self._tags: dict[str, AYTag] = {}
        self._dropdown_visible = False

        self._init_ui()
        self._connect_signals()
        self._sync_tags_from_items()

    # --- UI Setup ---

    def _init_ui(self) -> None:
        """Build the widget layout."""
        main_layout = AYVBoxLayout(self, margin=0, spacing=0)

        # Top bar
        self._top_bar = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.Low,
            layout_margin=4,
            layout_spacing=4,
        )
        main_layout.addWidget(self._top_bar)

        # Label
        self._label = AYLabel(self._label_text)
        self._label.setContentsMargins(10, 0, 5, 0)
        self._top_bar.add_widget(self._label)

        # Tags container
        self._tags_container = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.Default,
            layout_margin=0,
            layout_spacing=4,
        )
        lyt = self._tags_container.layout()
        if lyt:
            lyt.setSizeConstraint(
                QtWidgets.QLayout.SizeConstraint.SetFixedSize
            )
        self._top_bar.add_widget(self._tags_container)

        # Spacer
        self._top_bar.addStretch()

        # Toggle button
        self._toggle_btn = AYButton(
            icon="keyboard_arrow_down",
            variant=AYButton.Variants.Nav_Small,
            tooltip="Toggle filter options",
        )
        self._toggle_btn.setContentsMargins(4, 4, 4, 10)
        self._top_bar.add_widget(self._toggle_btn)

        # Create floating dropdown popup (not added to layout)
        self._dropdown_popup = FilterDropdownPopup()
        self._dropdown_popup.populate(self._items)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._toggle_btn.clicked.connect(self._on_toggle_dropdown)
        self._dropdown_popup.item_toggled.connect(self._on_popup_item_toggled)
        self._dropdown_popup.popup_closed.connect(self._on_popup_closed)

    # --- Public API ---

    def add_filter(self, item: FilterItem) -> None:
        """Add a new filter option.

        Args:
            item: The FilterItem to add.
        """
        if item not in self._items:
            self._items.append(item)
            self._repopulate_popup()
            if item.selected:
                self._add_tag(item)

    def remove_filter(self, key: str) -> None:
        """Remove a filter option by key.

        Args:
            key: Unique identifier of the filter to remove.
        """
        for i, item in enumerate(self._items):
            if item.key == key:
                self._items.pop(i)
                self._remove_tag(key)
                self._repopulate_popup()
                break

    def set_filter_selected(self, key: str, selected: bool) -> None:
        """Set selection state of a filter.

        Args:
            key: Unique identifier of the filter.
            selected: New selection state.
        """
        for item in self._items:
            if item.key == key:
                if item.selected != selected:
                    item.selected = selected
                    self._update_popup_item_state(key, selected)
                    if selected:
                        self._add_tag(item)
                        self.filter_added.emit(key)
                    else:
                        self._remove_tag(key)
                        self.filter_removed.emit(key)
                    self._emit_filter_changed()
                break

    def get_selected_keys(self) -> List[str]:
        """Get list of selected filter keys.

        Returns:
            List of keys for currently selected filters.
        """
        return [item.key for item in self._items if item.selected]

    def get_selected_items(self) -> List[FilterItem]:
        """Get list of selected filter items.

        Returns:
            List of FilterItem objects that are selected.
        """
        return [item for item in self._items if item.selected]

    def clear_selection(self) -> None:
        """Deselect all filters."""
        for item in self._items:
            if item.selected:
                self.set_filter_selected(item.key, False)

    def select_all(self) -> None:
        """Select all filters."""
        for item in self._items:
            if not item.selected:
                self.set_filter_selected(item.key, True)

    # --- Private Methods ---

    def _repopulate_popup(self) -> None:
        """Repopulate the popup with current filter items."""
        self._dropdown_popup.populate(self._items)

    def _update_popup_item_state(self, key: str, selected: bool) -> None:
        """Update checkbox state of a popup item.

        Args:
            key: Key of the item to update.
            selected: New selection state.
        """
        self._dropdown_popup.update_item_state(key, selected)

    def _sync_tags_from_items(self) -> None:
        """Synchronize tags with current filter item states."""
        for item in self._items:
            if item.selected and item.key not in self._tags:
                self._add_tag(item)
            elif not item.selected and item.key in self._tags:
                self._remove_tag(item.key)

    def _add_tag(self, item: FilterItem) -> None:
        """Create and add a tag widget for a filter item.

        Args:
            item: The FilterItem to create a tag for.
        """
        if item.key in self._tags:
            return

        color = QColor(item.color or self._default_color)
        tag = AYTag(item.key, color, label=item.label)
        tag.tag_removed.connect(self._on_tag_removed)
        tag.tag_expanded.connect(self._on_tag_expanded)

        self._tags[item.key] = tag
        self._tags_container.add_widget(tag)

    def _remove_tag(self, key: str) -> None:
        """Remove a tag widget.

        Args:
            key: Key of the tag to remove.
        """
        if key not in self._tags:
            return

        tag = self._tags.pop(key)
        tag.setParent(None)
        tag.deleteLater()

    def _emit_filter_changed(self) -> None:
        """Emit filter_changed signal with current selection."""
        self.filter_changed.emit(self.get_selected_keys())

    # --- Event Handlers ---

    def _on_toggle_dropdown(self) -> None:
        """Handle toggle button click."""
        if self._dropdown_visible:
            # Close popup
            self._dropdown_popup.close()
        else:
            # Show popup below the top bar
            self._dropdown_visible = True
            self._toggle_btn.set_icon("keyboard_arrow_up")
            self._dropdown_popup.show_below(self._top_bar)

    def _on_popup_item_toggled(self, key: str, selected: bool) -> None:
        """Handle popup item toggle.

        Args:
            key: Key of the toggled filter.
            selected: New selection state.
        """
        self.set_filter_selected(key, selected)

    def _on_popup_closed(self) -> None:
        """Handle popup close event."""
        self._dropdown_visible = False
        self._toggle_btn.set_icon("keyboard_arrow_down")

    def _on_tag_removed(self, key: str) -> None:
        """Handle tag X button click.

        Args:
            key: Key of the removed tag.
        """
        self.set_filter_selected(key, False)

    def _on_tag_expanded(self, key: str) -> None:
        """Handle tag expand button click - toggle dropdown.

        Args:
            key: Key of the expanded tag.
        """
        self._on_toggle_dropdown()


if __name__ == "__main__":
    from ..tester import Style, test
    from .container import AYContainer

    def _build() -> QtWidgets.QWidget:
        """Build test widget."""
        w = AYContainer(variant=AYContainer.Variants.High, layout_margin=10)
        w.add_widget(
            AYFilter(
                label="Sort by",
                items=[
                    FilterItem("task", "Task"),
                    FilterItem("folder", "Folder", selected=True),
                    FilterItem("status", "Status", selected=True),
                    FilterItem("priority", "Priority"),
                    FilterItem("due_date", "Due Date"),
                ],
            )
        )
        w.addStretch(10)
        return w

    test(_build, style=Style.AyonStyleOverCSS)

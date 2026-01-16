"""Tag selector component for displaying and managing tags."""

from __future__ import annotations

from qtpy.QtCore import Signal
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)

from .buttons import AYButton
from .layouts import AYHBoxLayout, AYVBoxLayout


class AYTagSelector(QDialog):
    """A searchable dropdown dialog for selecting tags.

    Displays available tags in a searchable list with multi-select capability.
    Emits a signal when tags are changed.

    Attributes:
        tags_changed: Signal emitted when selected tags change, passes list of selected tag names.
    """

    tags_changed = Signal(list)

    def __init__(
        self,
        available_tags: list[str] | list[dict] | None = None,
        selected_tags: list[str] | None = None,
        parent = None,
    ):
        """Initialize the tag selector dialog.

        Args:
            available_tags: List of all available tags (strings or dicts with 'name'/'text' key).
            selected_tags: List of currently selected tags (strings).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        # Convert available tags to strings if they're dicts
        self.available_tags = self._extract_tag_names(available_tags or [])
        self.selected_tags = list(selected_tags or [])
        self.search_input = None
        self.tag_list = None

        self.setWindowTitle("Select Tags")
        self.setMinimumWidth(350)
        self.setMinimumHeight(400)
        self._build()

    @staticmethod
    def _extract_tag_names(tags: list) -> list[str]:
        """Extract tag names from mixed list of strings and dicts.

        Args:
            tags: List of tag strings or dicts with 'name' or 'text' key

        Returns:
            Sorted list of tag name strings
        """
        tag_names = []
        for tag in tags:
            if isinstance(tag, dict):
                # Try to get name from dict, fallback to 'text' or 'name' key
                tag_name = tag.get("name") or tag.get("text") or str(tag)
            else:
                tag_name = str(tag)
            tag_names.append(tag_name)
        return sorted(tag_names)

    def _build(self) -> None:
        """Build the dialog layout with search and tag list."""
        main_layout = AYVBoxLayout(margin=8, spacing=6)

        # Search header
        search_label = QLabel("Search Tags")
        main_layout.addWidget(search_label)

        # Search input field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to filter tags...")
        self.search_input.textChanged.connect(self._on_search_changed)
        main_layout.addWidget(self.search_input)

        # Tag list with multi-select
        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )

        # Populate initial list
        for tag in self.available_tags:
            item = QListWidgetItem(tag)
            # Set smaller font for tag names
            font = QFont()
            font.setPointSize(9)
            item.setFont(font)
            self.tag_list.addItem(item)
            # Pre-select tags that are already selected
            if tag in self.selected_tags:
                item.setSelected(True)

        main_layout.addWidget(self.tag_list)

        # Buttons layout
        button_layout = AYHBoxLayout(margin=0, spacing=4)

        ok_button = AYButton("OK", variant="filled", parent=self)
        ok_button.clicked.connect(self.accept)

        cancel_button = AYButton("Cancel", variant="text", parent=self)
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _on_search_changed(self, search_text: str) -> None:
        """Filter tags based on search input."""
        search_lower = search_text.lower()

        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            # Show item if it matches search text or is empty
            should_show = (
                not search_text
                or search_lower in item.text().lower()
            )
            self.tag_list.setRowHidden(i, not should_show)

    def get_selected_tags(self) -> list[str]:
        """Get the list of selected tags.

        Returns:
            List of selected tag names.
        """
        selected = []
        for item in self.tag_list.selectedItems():
            selected.append(item.text())
        return sorted(selected)

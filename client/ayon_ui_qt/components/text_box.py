from __future__ import annotations

import logging
import os
from functools import partial

from qtpy import QtWidgets
from qtpy.QtCore import (
    QObject,
    Qt,
    Signal,  # type: ignore
    Slot,  # type: ignore
)  # type: ignore
from qtpy.QtGui import (
    QColor,
    QFont,
    QPalette,
    QPixmap,
    QTextCursor,
    QTextDocument,
    QTextFrameFormat,
)
from qtpy.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
)

from .. import get_ayon_style
from ..data_models import CommentCategory, ProjectData, User
from ..variants import QFrameVariants, QTextEditVariants
from .buttons import AYButton
from .combo_box import AYComboBox
from .comment_completion import (
    format_comment_on_change,
    on_completer_activated,
    on_completer_key_press,
    on_completer_text_changed,
    on_users_updated,
    setup_user_completer,
)
from .container import AYContainer
from .layouts import AYHBoxLayout, AYVBoxLayout
from .text_edit import AYTextEdit

logger = logging.getLogger(__name__)

MD_DIALECT = QTextDocument.MarkdownFeature.MarkdownDialectGitHub


class AYTextEditor(AYTextEdit):
    Variants = QTextEditVariants

    def __init__(
        self,
        *args,
        num_lines: int = 0,
        read_only: bool = False,
        user_list: list[User] | None,
        variant: Variants = Variants.Default,
        **kwargs,
    ):
        # remove our kwargs
        self.num_lines: int = num_lines
        self._read_only: bool = read_only
        self._user_list: list[User] = user_list or []
        self._variant_str: str = variant.value

        super().__init__(*args, variant=variant, **kwargs)
        self.setStyle(get_ayon_style())

        if self.num_lines:
            self.setFixedHeight(
                self.fontMetrics().lineSpacing() * self.num_lines + 8
            )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
            if self.num_lines
            else QSizePolicy.Policy.Fixed,
        )

        # automatic bullet lists
        self.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)

        if not self._read_only:
            self.setPlaceholderText(
                "Comment or mention with @user, @@version, @@@task..."
            )
        self.setReadOnly(self._read_only)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("white"))
        self.setPalette(palette)
        # Setup user completer
        setup_user_completer(
            self,
            self._on_completer_activated,
            self._on_text_changed,
        )
        self.document().contentsChanged.connect(
            lambda: format_comment_on_change(self)
        )

    def _on_text_changed(self) -> None:
        """Handle text changes to show/hide completer."""
        on_completer_text_changed(self)

    def _on_completer_activated(self, text: str) -> None:
        """Handle completer selection."""
        on_completer_activated(self, text)

    def keyPressEvent(self, event) -> None:
        """Handle key press events for completer."""
        if on_completer_key_press(self, event):
            event.accept()
            return
        super().keyPressEvent(event)

    def set_style(self, style):
        cursor = self.textCursor()

        # Disconnect the format_comment_on_change to prevent re-formatting
        self.document().contentsChanged.disconnect()
        self._applying_style = True

        cursor.beginEditBlock()

        if style == "stl_bold":
            # Toggle bold for current format or set it for new text
            fmt = cursor.charFormat()
            new_weight = (
                QFont.Weight.Normal
                if fmt.fontWeight() == QFont.Weight.Bold
                else QFont.Weight.Bold
            )
            fmt.setFontWeight(new_weight)

            # Apply the format to current selection OR set as current format
            # for next text
            if cursor.hasSelection():
                cursor.setCharFormat(fmt)
            else:
                # Set as the current format for subsequent typing
                self.setCurrentCharFormat(fmt)

            # Ensure the cursor maintains this format
            self.setTextCursor(cursor)

        elif style == "stl_italic":
            fmt = cursor.charFormat()
            new_italic = not fmt.fontItalic()
            fmt.setFontItalic(new_italic)

            if cursor.hasSelection():
                cursor.setCharFormat(fmt)
            else:
                self.setCurrentCharFormat(fmt)

            self.setTextCursor(cursor)

        elif style == "stl_h1":
            fmt = cursor.charFormat()
            base_size = self.font().pointSize()
            current_size = fmt.fontPointSize()

            # Toggle header formatting
            if current_size > base_size:  # Already a header
                fmt.setFontPointSize(base_size)
                fmt.setFontWeight(QFont.Weight.Normal)
            else:  # Make it a header
                fmt.setFontPointSize(base_size * 1.5)
                fmt.setFontWeight(QFont.Weight.Bold)

            if cursor.hasSelection():
                cursor.setCharFormat(fmt)
            else:
                self.setCurrentCharFormat(fmt)

            self.setTextCursor(cursor)

        elif style == "stl_link":
            pw = self.parentWidget()
            if not pw:
                return

            selected_text = (
                cursor.selectedText() if cursor.hasSelection() else ""
            )
            field = QtWidgets.QLineEdit(selected_text, parent=pw)

            def _make_link():
                link = field.text()
                fmt = self.currentCharFormat()
                fmt.setAnchor(True)
                fmt.setAnchorHref(link)
                fmt.setFontUnderline(True)

                if cursor.hasSelection():
                    cursor.setCharFormat(fmt)
                else:
                    self.setCurrentCharFormat(fmt)

                field.close()
                field.deleteLater()
                self.setFocus()
                self.update()

            # open link edit field
            field.show()
            fr = field.rect()
            field.setGeometry(4, 0, self.rect().width(), fr.height())
            field.selectAll()
            field.setFocus()
            field.returnPressed.connect(_make_link)

        elif style == "stl_code":
            frame_fmt = QTextFrameFormat()
            cursor.insertFrame(frame_fmt)
            print("IMPLEMENT ME !")

        cursor.endEditBlock()
        self._applying_style = False
        self.document().contentsChanged.connect(
            lambda: format_comment_on_change(self)
        )

    def set_format(self, format):
        """Set up the bullet/numbered/checklist formatting."""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        # Select all and delete to remove placeholder
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        if format == "fmt_bullet":
            # Apply bullet list formatting
            self.document().setMarkdown("- ", MD_DIALECT)
        elif format == "fmt_number":
            # Apply numbered list formatting
            self.document().setMarkdown("1. ", MD_DIALECT)
        elif format == "fmt_checklist":
            # Apply checklist formatting
            self.document().setMarkdown("- [ ] ", MD_DIALECT)

        cursor.insertText(" ")
        cursor.endEditBlock()
        # Move cursor to end
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)


def _dict_from_comment_category(
    comment_categories: list[CommentCategory],
) -> list[dict]:
    if comment_categories:
        return [
            {
                "text": c.name,
                "short_text": c.name,
                "icon": "crop_square",
                "color": c.color,
            }
            for c in comment_categories
        ]
    return [
        {
            "text": "No category",
            "short_text": "No category",
            "icon": "crop_square",
            "color": "#707070",
        }
    ]


class AttachmentWidget(QtWidgets.QWidget):
    """Widget to display a single attachment thumbnail with remove button."""

    remove_clicked = Signal(int)  # Signal emits the attachment index

    def __init__(self, parent=None, index=0, filename="", file_path=""):
        super().__init__(parent)
        self.index = index
        self.filename = filename
        self.file_path = file_path
        self.setup_ui()
        self.load_image()

    def setup_ui(self):
        # Use a container for the thumbnail with overlay button
        container = QtWidgets.QWidget(self)
        container.setFixedSize(80, 60)

        # Thumbnail
        self.thumbnail_label = QLabel(container)
        self.thumbnail_label.setFixedSize(80, 60)
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Remove button overlaid on top-right corner
        self.remove_btn = AYButton(
            "×", variant=AYButton.Variants.Nav, parent=container
        )
        self.remove_btn.setFixedSize(18, 18)
        self.remove_btn.move(62, 0)  # Position at top-right corner
        self.remove_btn.clicked.connect(
            lambda: self.remove_clicked.emit(self.index)
        )
        # Ensure button is on top
        self.remove_btn.raise_()
        # Main layout
        layout = AYVBoxLayout(margin=4, spacing=2)
        layout.addWidget(container)

        # Filename label (truncated)
        self.filename_label = QLabel(self)
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.filename_label)

        self.update_display()

    def load_image(self):
        """Load thumbnail from file_path or base64"""
        if self.file_path.startswith("data:image"):
            # Base64 encoded image
            import base64

            # Extract base64 data
            base64_data = (
                self.file_path.split(",", 1)[1]
                if "," in self.file_path
                else self.file_path
            )
            try:
                image_data = base64.b64decode(base64_data)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                self.thumbnail_label.setPixmap(
                    pixmap.scaled(
                        80,
                        60,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            except Exception as e:
                logger.error("Failed to load base64 image: %s", e)
                self.thumbnail_label.setText("Image")
        else:
            # File path
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull():
                self.thumbnail_label.setPixmap(
                    pixmap.scaled(
                        80,
                        60,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.thumbnail_label.setText("Image")

    def update_display(self):
        """Update the display with current filename and image"""
        # Update filename label
        self.filename_label.setText(
            self.filename[:12] + "..."
            if len(self.filename) > 12
            else self.filename
        )
        # Reload image
        self.load_image()

    def update_content(self, filename="", file_path=""):
        """Update the widget content"""
        if filename:
            self.filename = filename
        if file_path:
            self.file_path = file_path
        self.update_display()


class AYTextBoxSignals(QObject):
    # Signal emitted when comment button is clicked, passes markdown content
    comment_submitted = Signal(str, str, list)  # type: ignore


class AYTextBox(AYContainer):
    signals = AYTextBoxSignals()
    Variants = QFrameVariants
    style_icons = {
        "stl_h1": "format_h1",
        "stl_bold": "format_bold",
        "stl_italic": "format_italic",
        "stl_link": "link",
        "stl_code": "code",
    }
    format_icons = {
        "fmt_number": "format_list_numbered",
        "fmt_bullet": "format_list_bulleted",
        "fmt_checklist": "checklist",
    }
    mention_map = {
        "person": "@",
        "layers": "@@",
        "check_circle": "@@@",
    }

    def __init__(
        self,
        *args,
        num_lines=0,
        show_categories=False,
        user_list: list[User] | None = None,
        variant: Variants = Variants.Default,
        **kwargs,
    ):
        self._variant_str: str = variant.value
        super().__init__(
            *args,
            layout=AYContainer.Layout.VBox,
            variant=variant,
            margin=0,
            **kwargs,
        )

        self.show_categories = show_categories
        self.comment_categories: list[dict] = _dict_from_comment_category([])
        self.category = self.comment_categories[0]["text"]
        self._user_list: list[User] = user_list or []
        # Store image annotation data
        self._annotation_attachments: list[dict] = []
        self._file_attachments: list[str] = []  # Store file paths only
        self._build(num_lines)

    def _build_upper_bar(self):
        grp_spacing = 16
        lyt = AYHBoxLayout(spacing=0, margin=0)
        # comment category if available
        if self.show_categories:
            self.com_cat = AYComboBox(
                parent=self, items=self.comment_categories
            )
            self.com_cat.currentTextChanged.connect(self._on_category_changed)
            lyt.addWidget(self.com_cat)
        lyt.addStretch()
        # styling buttons
        for var, icn in self.style_icons.items():
            setattr(
                self,
                var,
                AYButton(self, variant=AYButton.Variants.Nav, icon=icn),
            )
            lyt.addWidget(getattr(self, var))
        # formatting buttons
        for var, icn in self.format_icons.items():
            setattr(
                self,
                var,
                AYButton(self, variant=AYButton.Variants.Nav, icon=icn),
            )
            lyt.addWidget(getattr(self, var))
        lyt.addSpacing(grp_spacing)
        self.attach_file_btn = AYButton(
            self, variant=AYButton.Variants.Nav, icon="attach_file"
        )
        self.attach_file_btn.clicked.connect(self._on_attach_file_clicked)
        lyt.addWidget(self.attach_file_btn)
        return lyt

    def _build_attachment_area(self):
        """Build the scrollable attachment display area."""
        # Container for attachments
        self.attachment_container = QtWidgets.QWidget(self)
        self.attachment_layout = AYHBoxLayout(
            self.attachment_container, margin=4, spacing=4
        )

        # Scroll area
        self.attachment_scroll = QScrollArea(self)
        self.attachment_scroll.setWidget(self.attachment_container)
        self.attachment_scroll.setWidgetResizable(True)
        self.attachment_scroll.setFixedHeight(100)
        self.attachment_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.attachment_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.attachment_scroll.hide()  # Hidden by default

        return self.attachment_scroll

    def _build_edit_field(self, num_lines):
        self.edit_field = AYTextEditor(
            self,
            num_lines=num_lines,
            user_list=self._user_list,
            variant=AYTextEditor.Variants.Default,
        )
        for var in self.style_icons:
            getattr(self, var).clicked.connect(
                partial(self.edit_field.set_style, var)
            )
        for var in self.format_icons:
            getattr(self, var).clicked.connect(
                partial(self.edit_field.set_format, var)
            )
        return self.edit_field

    def _build_lower_bar(self):
        lyt = AYHBoxLayout(margin=0, spacing=0)

        for icn, mention in self.mention_map.items():
            btn = AYButton(self, variant=AYButton.Variants.Nav, icon=icn)
            btn.clicked.connect(partial(self._add_mention_to_editor, mention))
            lyt.addWidget(btn)

        lyt.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QSizePolicy.Policy.MinimumExpanding)
        )
        self.comment_button = AYButton(
            "Comment", variant=AYButton.Variants.Filled
        )
        self.comment_button.clicked.connect(self._on_comment_clicked)
        lyt.addWidget(self.comment_button)
        return lyt

    def _on_comment_clicked(self) -> None:
        """Handle comment button click and emit signal with markdown content."""
        markdown_content = self.edit_field.document().toMarkdown(MD_DIALECT)
        self.signals.comment_submitted.emit(
            markdown_content, self.category, self._file_attachments
        )
        self.edit_field.clear()
        self.clear_annotation_attachment()
        self.clear_file_attachments()

    def _add_mention_to_editor(self, mention: str) -> None:
        """Add mention text to the editor at cursor position."""
        cursor = self.edit_field.textCursor()
        cursor.insertText(mention)
        self.edit_field.setTextCursor(cursor)
        self.edit_field.setFocus()

    def _on_category_changed(self, category: str) -> None:
        self.category = category

    def _on_attach_file_clicked(self) -> None:
        """Handle attach file button click and open file dialog."""
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select files to attach",
            "",
            "Image Files (*.png *.jpeg *.jpg);;All Files (*)",
        )

        if file_paths:
            self.add_file_attachments(file_paths)

    def _on_annotation_attachment_removed(self, index: int) -> None:
        """Handle removal of an image annotation attachment."""
        if 0 <= index < len(self._annotation_attachments):
            file_path = self._annotation_attachments[index].get(
                "file_path", ""
            )
            if os.path.exists(file_path):
                os.remove(file_path)  # Optionally delete the file
            self._annotation_attachments.pop(index)
            self._refresh_attachment_display()

    def _on_file_attachment_removed(self, index: int) -> None:
        """Handle removal of a file attachment."""
        if 0 <= index < len(self._file_attachments):
            self._file_attachments.pop(index)
            self._refresh_file_attachment_display()

    def _refresh_attachment_display(self) -> None:
        """Refresh the attachment display area."""
        # Keep track of existing widgets by index
        existing_widgets = {}
        for idx in range(self.attachment_layout.count()):
            item = self.attachment_layout.itemAt(idx)
            if item and item.widget() and hasattr(item.widget(), "index"):
                widget = item.widget()
                if widget is not None:
                    existing_widgets[widget.index] = widget

        # Update or create widgets
        if self._annotation_attachments:
            for idx, attachment in enumerate(self._annotation_attachments):
                logger.info(
                    "Displaying attachment: %s with path: %s",
                    attachment.get("filename"),
                    attachment.get("file_path"),
                )

                if idx in existing_widgets:
                    # Update existing widget
                    widget = existing_widgets[idx]
                    widget.update_content(
                        filename=attachment.get(
                            "filename", f"attachment_{idx}"
                        ),
                        file_path=attachment.get("file_path", ""),
                    )
                    # Update index if it changed
                    widget.index = idx
                else:
                    # Create new widget
                    widget = AttachmentWidget(
                        parent=self.attachment_container,
                        index=idx,
                        filename=attachment.get(
                            "filename", f"attachment_{idx}"
                        ),
                        file_path=attachment.get("file_path", ""),
                    )
                    widget.remove_clicked.connect(
                        self._on_annotation_attachment_removed
                    )
                    self.attachment_layout.insertWidget(idx, widget)

            # Remove any extra widgets that shouldn't be there
            for idx in list(existing_widgets.keys()):
                if idx >= len(self._annotation_attachments):
                    widget = existing_widgets[idx]
                    self.attachment_layout.removeWidget(widget)
                    widget.deleteLater()

            # Make sure we have a stretch at the end
            if self.attachment_layout.count() > 0 and (
                not isinstance(
                    self.attachment_layout.itemAt(
                        self.attachment_layout.count() - 1
                    ).widget(),
                    type(None),
                )
            ):
                self.attachment_layout.addStretch()

            self.attachment_scroll.show()
        else:
            # Remove all widgets if no attachments
            while self.attachment_layout.count():
                item = self.attachment_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self.attachment_scroll.hide()

        # Force a complete refresh
        self.attachment_container.update()
        self.attachment_scroll.viewport().update()

    def _build_file_attachment_area(self):
        """Build the scrollable file attachment display area."""
        # Container for file attachments
        self.file_attachment_container = QtWidgets.QWidget(self)
        self.file_attachment_layout = AYVBoxLayout(
            self.file_attachment_container, margin=4, spacing=2
        )

        # Scroll area
        self.file_attachment_scroll = QScrollArea(self)
        self.file_attachment_scroll.setWidget(self.file_attachment_container)
        self.file_attachment_scroll.setWidgetResizable(True)
        self.file_attachment_scroll.setFixedHeight(60)
        self.file_attachment_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.file_attachment_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.file_attachment_scroll.hide()  # Hidden by default

        return self.file_attachment_scroll

    def _refresh_file_attachment_display(self) -> None:
        """Refresh the file attachment display area."""
        # Clear existing widgets
        while self.file_attachment_layout.count():
            item = self.file_attachment_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Add file attachment items
        if self._file_attachments:
            for idx, file_path in enumerate(self._file_attachments):
                filename = os.path.basename(file_path)

                # Create a container for the file item
                file_item = QtWidgets.QWidget(self.file_attachment_container)
                file_item_layout = AYHBoxLayout(file_item, margin=2, spacing=4)

                # File label
                file_label = QLabel(filename, file_item)
                file_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                file_item_layout.addWidget(file_label)

                # Remove button
                remove_btn = AYButton(
                    "×", variant=AYButton.Variants.Nav, parent=file_item
                )
                remove_btn.setFixedSize(20, 20)
                remove_btn.clicked.connect(
                    lambda checked=False,
                    i=idx: self._on_file_attachment_removed(i)
                )
                file_item_layout.addWidget(remove_btn)

                self.file_attachment_layout.addWidget(file_item)

            self.file_attachment_layout.addStretch()
            self.file_attachment_scroll.show()
        else:
            self.file_attachment_scroll.hide()

        self.file_attachment_container.update()

    def add_annotation_attachments(self, attachments: list[dict]) -> None:
        """Add multiple image annotation attachments at once.

        Args:
            attachments: List of attachment dictionaries with 'file_path'
                        and 'filename' keys
        """
        if not attachments:
            return

        for attachment in attachments:
            file_pattern = attachment.get("file_pattern", "")
            current_frame = attachment.get("current_frame", 0)
            filename = attachment.get("filename", "")
            file_path = attachment.get("file_path", "")
            timestamp = attachment.get("timestamp", 0)

            # Find existing attachment that matches
            existing_attachments = [
                existing
                for existing in self._annotation_attachments
                if existing.get("file_pattern") == file_pattern
                and existing.get("current_frame") == current_frame
            ]
            if existing_attachments:
                # Update the first matching attachment (should be only one)
                existing = existing_attachments[0]
                logger.info(
                    "Attachment already exists, updating: %s", filename
                )
                existing.update(
                    {
                        "file_path": file_path,
                        "filename": filename,
                        "timestamp": timestamp,
                    }
                )
                self._refresh_attachment_display()

            else:
                # Add new attachment
                self._annotation_attachments.append(
                    {
                        "file_pattern": file_pattern,
                        "current_frame": current_frame,
                        "file_path": file_path,
                        "filename": filename,
                        "timestamp": timestamp,
                    }
                )

        self._refresh_attachment_display()

    def add_file_attachments(self, file_paths: list[str]) -> None:
        """Add multiple file attachments at once.

        Args:
            file_paths: List of file paths to attach
        """
        if not file_paths:
            return

        added_count = 0
        for file_path in file_paths:
            # Check for duplicates
            if file_path in self._file_attachments:
                logger.info("File attachment already exists: %s", file_path)
                continue

            self._file_attachments.append(file_path)
            added_count += 1

        # Refresh display only once after all additions
        if added_count > 0:
            self._refresh_file_attachment_display()
            logger.info("Added %d file attachment(s)", added_count)

    def clear_annotation_attachment(self) -> None:
        """Clear all image annotations from the editor."""
        self._annotation_attachments.clear()
        self._refresh_attachment_display()

    def clear_file_attachments(self) -> None:
        """Clear all file attachments from the editor."""
        self._file_attachments.clear()
        self._refresh_file_attachment_display()

    def get_attachments(self) -> list[dict]:
        """Get the current list of image annotations.

        Returns:
            List of annotation attachment dictionaries
        """
        return self._annotation_attachments.copy()

    def get_file_attachments(self) -> list[str]:
        """Get the current list of file attachments.

        Returns:
            List of file paths
        """
        return self._file_attachments.copy()

    @Slot(ProjectData)
    def on_ctlr_project_changed(self, data: ProjectData):
        self.comment_categories = _dict_from_comment_category(
            data.comment_category
        )
        if self.show_categories:
            self.com_cat.update_items(self.comment_categories)
        self.edit_field._user_list = self._user_list = data.users
        on_users_updated(self.edit_field)

    def _build(self, num_lines):
        self.add_layout(self._build_upper_bar())
        self.add_widget(
            self._build_attachment_area()
        )  # Add image annotation area
        self.add_widget(
            self._build_file_attachment_area()
        )  # Add file attachment area
        self.add_widget(self._build_edit_field(num_lines), stretch=10)
        self.add_layout(self._build_lower_bar())

    def set_markdown(self, md: str):
        self.edit_field.document().setMarkdown(md, MD_DIALECT)


# TEST ------------------------------------------------------------------------


if __name__ == "__main__":
    from ..tester import Style, test
    from .container import AYContainer

    def build():
        w = AYContainer(layout=AYContainer.Layout.HBox, margin=8)
        ww = AYTextBox(parent=w, variant=AYTextBox.Variants.High)
        ww.set_markdown(
            "## Title\nText can be **bold** or *italic*, as expected !\n"
            "- [ ] Do this\n- [ ] Do that\n"
        )
        w.add_widget(ww)
        ww.signals.comment_submitted.connect(
            lambda x, y: print(
                f"Comment [{y}] {'=' * (70 - len(y) - 2)}\n{x}{'=' * 78}"
            )
        )

        # Test adding attachments
        ww.add_annotation_attachments(
            [
                {
                    "file_path": "test1.png",
                    "filename": "test_annotation1.png",
                    "timestamp": 12345678,
                },
                {
                    "file_path": "test2.png",
                    "filename": "test_annotation2.png",
                    "timestamp": 12345679,
                },
            ]
        )

        return w

    test(build, style=Style.AyonStyleOverCSS)

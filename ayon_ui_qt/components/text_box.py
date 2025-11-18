from __future__ import annotations

import logging
from functools import partial

from qtpy.QtCore import (
    QObject,
    Signal,  # type: ignore
    Slot,  # type: ignore
    Qt,
)  # type: ignore
from qtpy import QtWidgets
from qtpy.QtGui import (
    QFont,
    QTextCursor,
    QTextDocument,
    QTextFrameFormat,
    QPixmap,
)
from qtpy.QtWidgets import (
    QSizePolicy,
    QTextEdit,
    QLabel,
    QScrollArea,
)

from .buttons import AYButton
from .frame import AYFrame
from .layouts import AYHBoxLayout, AYVBoxLayout
from .combo_box import AYComboBox
from .comment_completion import (
    setup_user_completer,
    on_completer_text_changed,
    on_completer_activated,
    on_completer_key_press,
    on_users_updated,
    format_comment_on_change,
)
from ..data_models import CommentCategory, ProjectData, User
from .. import style_widget_and_siblings

logger = logging.getLogger(__name__)

MD_DIALECT = QTextDocument.MarkdownFeature.MarkdownDialectGitHub


class AYTextEditor(QTextEdit):
    def __init__(
        self,
        *args,
        num_lines: int = 0,
        read_only: bool = False,
        user_list: list[User] | None,
        **kwargs,
    ):
        # remove our kwargs
        self.num_lines: int = num_lines
        self._read_only: bool = read_only
        self._user_list: list[User] = user_list or []

        super().__init__(*args, **kwargs)

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

        # Setup user completer
        setup_user_completer(
            self,
            self._on_completer_activated,
            self._on_text_changed,
        )
        self.document().contentsChanged.connect(
            lambda: format_comment_on_change(self)
        )

        style_widget_and_siblings(self, fix_app=False)

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
        # print(f"selected: {cursor.selectedText()}")
        if style == "stl_h1":
            cursor.beginEditBlock()
            char_format = cursor.blockCharFormat()

            # Check if already a header (by checking font size)
            current_size = cursor.charFormat().fontPointSize()
            base_size = self.font().pointSize()

            # print(f"current_size = {current_size}   base_size = {base_size}")

            # Toggle header formatting
            if current_size > base_size:  # Already a header
                # Remove header formatting
                char_format.setFontPointSize(base_size)
                char_format.setFontWeight(QFont.Weight.Normal)
            else:  # Make it a header
                # Apply header formatting (H2 style)
                char_format.setFontPointSize(base_size * 1.5)  # 1.5x larger
                char_format.setFontWeight(QFont.Weight.Bold)

            # Apply to entire block
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.setCharFormat(char_format)
            cursor.endEditBlock()
            # keep focus in editor
            self.setFocus()

        elif cursor.hasSelection():
            fmt = cursor.charFormat()
            cursor.beginEditBlock()

            if style == "stl_bold":
                if cursor.charFormat().fontWeight() == QFont.Weight.Normal:
                    fmt.setFontWeight(QFont.Weight.Bold)
                else:
                    fmt.setFontWeight(QFont.Weight.Normal)
                cursor.setCharFormat(fmt)

            elif style == "stl_italic":
                if cursor.charFormat().fontItalic():
                    fmt.setFontItalic(False)
                else:
                    fmt.setFontItalic(True)
                cursor.setCharFormat(fmt)

            elif style == "stl_link":
                pw = self.parentWidget()
                if not pw:
                    return

                field = QtWidgets.QLineEdit(cursor.selectedText(), parent=pw)

                def _make_link():
                    link = field.text()
                    fmt.setAnchor(True)
                    fmt.setAnchorHref(link)
                    fmt.setFontUnderline(True)
                    cursor.setCharFormat(fmt)
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
                txt = cursor.selectedText()
                frame_fmt = QTextFrameFormat()
                cursor.insertFrame(frame_fmt)

                print("IMPLEMENT ME !")

            cursor.endEditBlock()

    def set_format(self, format):
        print(f"format: {format}")


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

        # Use a container for the thumbnail with overlay button
        container = QtWidgets.QWidget(self)
        container.setFixedSize(80, 60)

        # Thumbnail
        self.thumbnail_label = QLabel(container)
        self.thumbnail_label.setFixedSize(80, 60)
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Load thumbnail from file_path or base64
        if file_path.startswith("data:image"):
            # Base64 encoded image
            import base64

            # Extract base64 data
            base64_data = file_path.split(",", 1)[1] if "," in file_path else file_path
            image_data = base64.b64decode(base64_data)

            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            self.thumbnail_label.setPixmap(pixmap.scaled(
                80, 60, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            # File path
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.thumbnail_label.setPixmap(pixmap.scaled(
                    80, 60, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                self.thumbnail_label.setText("Image")

        # Remove button overlaid on top-right corner
        remove_btn = AYButton("×", variant="nav", parent=container)
        remove_btn.setFixedSize(18, 18)
        remove_btn.move(62, 0)  # Position at top-right corner
        remove_btn.setStyleSheet("""
            AYButton {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border-radius: 9px;
                font-size: 14px;
                font-weight: bold;
            }
            AYButton:hover {
                background-color: rgba(200, 0, 0, 0.9);
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.index))
        remove_btn.raise_()  # Ensure button is on top

        # Main layout
        layout = AYVBoxLayout(self, margin=4, spacing=2)
        layout.addWidget(container)

        # Filename label (truncated)
        filename_label = QLabel(
            filename[:12] + "..." if len(filename) > 12 else filename, self
        )
        filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(filename_label)


class AYTextBoxSignals(QObject):
    # Signal emitted when comment button is clicked, passes markdown content
    comment_submitted = Signal(str, str)  # type: ignore


class AYTextBox(AYFrame):
    signals = AYTextBoxSignals()

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

    def __init__(
        self,
        *args,
        num_lines=0,
        show_categories=False,
        user_list: list[User] | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.show_categories = show_categories
        self.comment_categories: list[dict] = _dict_from_comment_category([])
        self.category = self.comment_categories[0]["text"]
        self._user_list: list[User] = user_list or []
        self._attachments: list[dict] = []  # Store attachment data
        self._build(num_lines)

    def _build_upper_bar(self):
        grp_spacing = 16
        lyt = AYHBoxLayout(self, spacing=0, margin=0)
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
            setattr(self, var, AYButton(self, variant="nav", icon=icn))
            lyt.addWidget(getattr(self, var))
        # formatting buttons
        for var, icn in self.format_icons.items():
            setattr(self, var, AYButton(self, variant="nav", icon=icn))
            lyt.addWidget(getattr(self, var))
        lyt.addSpacing(grp_spacing)
        lyt.addWidget(AYButton(self, variant="nav", icon="attach_file"))
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
            self, num_lines=num_lines, user_list=self._user_list
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
        for icn in ("person", "layers", "check_circle"):
            lyt.addWidget(AYButton(self, variant="nav", icon=icn))
        lyt.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QSizePolicy.Policy.MinimumExpanding)
        )
        self.comment_button = AYButton("Comment", variant="filled")
        self.comment_button.clicked.connect(self._on_comment_clicked)
        lyt.addWidget(self.comment_button)
        return lyt

    def _on_comment_clicked(self) -> None:
        """Handle comment button click and emit signal with markdown content."""
        markdown_content = self.edit_field.document().toMarkdown(MD_DIALECT)
        self.signals.comment_submitted.emit(markdown_content, self.category)
        self.edit_field.clear()
        self.clear_attachments()

    def _on_category_changed(self, category: str) -> None:
        self.category = category

    def _on_attachment_removed(self, index: int) -> None:
        """Handle removal of an attachment."""
        if 0 <= index < len(self._attachments):
            self._attachments.pop(index)
            self._refresh_attachment_display()

    def _refresh_attachment_display(self) -> None:
        """Refresh the attachment display area."""
        # Disable updates during rebuild to prevent flickering
        self.attachment_container.setUpdatesEnabled(False)

        try:
            # Clear existing widgets
            while self.attachment_layout.count():
                item = self.attachment_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add attachment widgets
            if self._attachments:
                for idx, attachment in enumerate(self._attachments):
                    widget = AttachmentWidget(
                        parent=self.attachment_container,
                        index=idx,
                        filename=attachment.get("filename", f"attachment_{idx}"),
                        file_path=attachment.get("file_path", "")
                    )
                    widget.remove_clicked.connect(self._on_attachment_removed)
                    self.attachment_layout.addWidget(widget)

                self.attachment_layout.addStretch()
                self.attachment_scroll.show()
            else:
                self.attachment_scroll.hide()
        finally:
            # Re-enable updates and trigger repaint once
            self.attachment_container.setUpdatesEnabled(True)
            self.attachment_container.update()

    def add_attachments(self, attachments: list[dict]) -> None:
        """Add multiple attachments at once.

        Args:
            attachments: List of attachment dictionaries with 'file_path'
                        and 'filename' keys
        """
        if not attachments:
            return

        added_count = 0
        for attachment in attachments:
            filename = attachment.get("filename", "")
            file_path = attachment.get("file_path", "")

            # Check for duplicates
            if any(existing.get("filename") == filename for existing in self._attachments):
                logger.info("Attachment already exists: %s", filename)
                continue

            # Add to list without refreshing
            self._attachments.append({
                "file_path": file_path,
                "filename": filename,
                "timestamp": attachment.get("timestamp")
            })
            added_count += 1

        # Refresh display only once after all additions
        if added_count > 0:
            self._refresh_attachment_display()
            logger.info("Added %d attachment(s)", added_count)

    def clear_attachments(self) -> None:
        """Clear all attachments from the editor."""
        self._attachments.clear()
        self._refresh_attachment_display()

    def get_attachments(self) -> list[dict]:
        """Get the current list of attachments.

        Returns:
            List of attachment dictionaries
        """
        return self._attachments.copy()

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
        lyt = AYVBoxLayout(self, margin=4, spacing=0)
        lyt.addLayout(self._build_upper_bar())
        lyt.addWidget(self._build_attachment_area())  # Add attachment area
        lyt.addWidget(self._build_edit_field(num_lines), stretch=10)
        lyt.addLayout(self._build_lower_bar())

    def set_markdown(self, md: str):
        self.edit_field.document().setMarkdown(md, MD_DIALECT)


# TEST ------------------------------------------------------------------------


if __name__ == "__main__":
    from ..tester import Style, test
    from .container import AYContainer

    def build():
        w = AYContainer(layout=AYContainer.Layout.HBox, margin=8)
        ww = AYTextBox(parent=w)
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
        ww.add_attachments(
            [
                {
                    "file_path": "test1.png",
                    "filename": "test_annotation1.png",
                    "timestamp": 12345678
                },
                {
                    "file_path": "test2.png",
                    "filename": "test_annotation2.png",
                    "timestamp": 12345679
                },
            ]
        )

        return w

    test(build, style=Style.Widget)

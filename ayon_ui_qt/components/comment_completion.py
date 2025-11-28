from __future__ import annotations

import re

from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import (
    QStandardItemModel,
    QStandardItem,
    QPainter,
    QTextCursor,
    QTextCharFormat,
    QFont,
)
from qtpy.QtWidgets import (
    QCompleter,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QTextEdit,
)

from .user_image import AYUserImage
from ..data_models import User
from .. import style_widget_and_siblings, get_ayon_style


class UserCompleterDelegate(QStyledItemDelegate):
    """Custom delegate to display user icon and full name in completer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_size = 20

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,
    ) -> None:
        """Paint user icon and full name."""
        user: User = index.data(Qt.ItemDataRole.UserRole)
        if not user:
            super().paint(painter, option, index)
            return

        # Draw background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.light())
        else:
            painter.fillRect(option.rect, option.palette.midlight())

        # Draw user icon
        user_image = AYUserImage(
            src=user.avatar_url,
            full_name=user.full_name,
            size=self.icon_size,
            outline=False,
        )
        icon_pixmap = user_image.pixmap()
        icon_x = option.rect.x() + 4
        icon_y = option.rect.y() + (option.rect.height() - self.icon_size) // 2
        painter.drawPixmap(icon_x, icon_y, icon_pixmap)

        # Draw full name
        text_x = icon_x + self.icon_size + 8
        text_rect = option.rect.adjusted(text_x, 0, 0, 0)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter,
            user.full_name,
        )

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index,
    ) -> QSize:
        """Return size hint for completer items."""
        return QSize(option.rect.width(), self.icon_size + 8)


class UserCompleterModel(QStandardItemModel):
    """Model for user completer."""

    def __init__(self, users: list[User], parent=None):
        super().__init__(parent)
        self.users = users
        self._populate()

    def _populate(self) -> None:
        """Populate model with users."""
        self.clear()
        for user in self.users:
            item = QStandardItem(user.full_name)
            item.setData(user, Qt.ItemDataRole.UserRole)
            self.appendRow(item)


def setup_user_completer(
    text_edit: QTextEdit,
    on_completer_activated,
    on_text_changed,
) -> None:
    """Setup user name completer for a QTextEdit widget.

    Args:
        text_edit: The QTextEdit widget to attach completer to.
        on_completer_activated: Callback for completer activation.
        on_text_changed: Callback for text changes.
    """
    users = getattr(text_edit, "_user_list")
    if not users:
        users = [
            User(
                name="not available",
                short_name="not available",
                full_name="not available",
                email="",
                avatar_url="",
            )
        ]
    model = UserCompleterModel(users, text_edit)
    text_edit.completer = QCompleter(model, text_edit)
    text_edit.completer.setCompletionMode(
        QCompleter.CompletionMode.PopupCompletion
    )
    text_edit.completer.setFilterMode(Qt.MatchFlag.MatchContains)
    text_edit.completer.setMaxVisibleItems(4)
    text_edit.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    text_edit.completer.setWidget(text_edit)

    # Set custom delegate
    popup = text_edit.completer.popup()
    if popup:
        delegate = UserCompleterDelegate(popup)
        popup.setItemDelegate(delegate)
        popup.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
        style_widget_and_siblings(popup, fix_app=False)

    # Connect completer signals
    text_edit.completer.activated.connect(on_completer_activated)
    text_edit.textChanged.connect(on_text_changed)


def on_users_updated(text_edit: QTextEdit):
    if not hasattr(text_edit, "completer"):
        return

    users = getattr(text_edit, "_user_list")
    if not users:
        users = [
            User(
                name="not available",
                short_name="not available",
                full_name="not available",
                email="",
                avatar_url="",
            )
        ]
    model = UserCompleterModel(users, text_edit)
    text_edit.completer.setModel(model)


def on_completer_text_changed(
    text_edit: QTextEdit,
) -> None:
    """Handle text changes to show/hide completer.

    Args:
        text_edit: The QTextEdit widget with completer.
    """
    if not hasattr(text_edit, "completer") or text_edit.isReadOnly():
        return

    cursor = text_edit.textCursor()
    block = cursor.block()
    text = block.text()
    pos_in_block = cursor.positionInBlock()

    # Find the last '@' before cursor
    at_pos = text.rfind("@", 0, pos_in_block)
    if at_pos == -1:
        popup = text_edit.completer.popup()
        if popup:
            popup.hide()
        return

    # Get text after '@'
    prefix = text[at_pos + 1 : pos_in_block]

    # Show completer if '@' is followed by nothing or non-space characters
    if not prefix or (prefix and not prefix[0].isspace()):
        text_edit.completer.setCompletionPrefix(prefix)
        show_completer_popup(text_edit, at_pos)
        # Auto-select if only one item
        popup = text_edit.completer.popup()
        if popup:
            popup_model = popup.model()
            row_count = popup_model.rowCount() if popup_model else 0
            if row_count == 1:
                popup.setCurrentIndex(popup_model.index(0, 0))
    else:
        popup = text_edit.completer.popup()
        if popup:
            popup.hide()


def show_completer_popup(text_edit: QTextEdit, at_pos: int) -> None:
    """Show completer popup above the QTextEdit.

    Args:
        text_edit: The QTextEdit widget with completer.
        at_pos: Position of '@' character in the block.
    """
    popup = text_edit.completer.popup()
    if not popup:
        return

    # Get editor dimensions
    editor_rect = text_edit.rect()
    editor_width = editor_rect.width()

    # Show popup to get its height
    popup.show()

    # Calculate height based on max visible items (4)
    max_visible = text_edit.completer.maxVisibleItems()
    item_height = popup.sizeHintForRow(0)
    popup_height = item_height * max_visible

    # Position popup above the QTextEdit with same width as editor
    global_pos = text_edit.mapToGlobal(editor_rect.topLeft())
    popup_x = global_pos.x()
    popup_y = global_pos.y() - popup_height

    popup.setGeometry(popup_x, popup_y, editor_width, popup_height)


def on_completer_activated(
    text_edit: QTextEdit,
    text: str,
) -> None:
    """Handle completer selection.

    Args:
        text_edit: The QTextEdit widget with completer.
        text: The selected completion text (user full name).
    """
    cursor = text_edit.textCursor()
    block = cursor.block()
    text_in_block = block.text()
    pos_in_block = cursor.positionInBlock()

    # Find the '@' position
    at_pos = text_in_block.rfind("@", 0, pos_in_block)
    if at_pos == -1:
        return

    # Replace from '@' to cursor with '@' + full_name
    cursor.setPosition(block.position() + at_pos)
    cursor.setPosition(
        block.position() + pos_in_block,
        QTextCursor.MoveMode.KeepAnchor,
    )
    cursor.insertText(f"@{text}")
    text_edit.setTextCursor(cursor)
    popup = text_edit.completer.popup()
    if popup:
        popup.hide()


def on_completer_key_press(
    text_edit: QTextEdit,
    event,
) -> bool:
    """Handle key press events for completer.

    Args:
        text_edit: The QTextEdit widget with completer.
        event: The key press event.

    Returns:
        True if event was handled, False otherwise.
    """
    if not hasattr(text_edit, "completer"):
        return False

    popup = text_edit.completer.popup()
    if popup and popup.isVisible():
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Get current completion from the selected index
            current_index = popup.currentIndex()
            if current_index.isValid():
                completion = current_index.data()
                if completion:
                    text_edit.completer.activated.emit(completion)
                    return True
    return False


def parse_markdown_from_web(text: str) -> list[dict]:
    """Parse web markdown syntax and return format information.

    Identifies H1 (text\n----), **bold**, _italic_, [link](url),
    and `code` patterns.

    Args:
        text: Markdown text containing web syntax

    Returns:
        List of dicts with keys: 'type', 'start', 'end', 'content', 'url'
    """
    formats = []

    # Pattern for H1 (text followed by newline and dashes)
    for match in re.finditer(r"^(.+?)\n-{2,}$", text, re.MULTILINE):
        formats.append({
            "type": "h1",
            "start": match.start(),
            "end": match.end(),
            "content": match.group(1),
        })

    # Pattern for **bold**
    for match in re.finditer(r"\*\*(.+?)\*\*", text):
        formats.append({
            "type": "bold",
            "start": match.start(),
            "end": match.end(),
            "content": match.group(1),
        })

    # Pattern for _italic_
    for match in re.finditer(r'_(.+?)_', text):
        formats.append({
            "type": "italic",
            "start": match.start(),
            "end": match.end(),
            "content": match.group(1),
        })

    # Pattern for [link](url)
    for match in re.finditer(r"\[(.+?)\]\((.+?)\)", text):
        formats.append({
            "type": "link",
            "start": match.start(),
            "end": match.end(),
            "content": match.group(1),
            "url": match.group(2),
        })

    # Pattern for `code`
    for match in re.finditer(r"`(.+?)`", text):
        formats.append({
            "type": "code",
            "start": match.start(),
            "end": match.end(),
            "content": match.group(1),
        })

    return formats


def apply_web_markdown_formatting(
    text_edit: QTextEdit,
    text: str,
    styles: dict | None = None,
) -> None:
    """Apply web markdown formatting to text, removing syntax.

    Removes markdown syntax while preserving formatting
    (**bold** becomes bold text, _italic_ becomes italic text, etc).

    Args:
        text_edit: QTextEdit widget to apply formatting to
        text: Markdown text from web
        styles: Optional custom styles dict with keys: "bold", "italic", "link", "code"
    """
    pal = get_ayon_style().model.base_palette

    # Parse markdown to find all format positions
    formats = parse_markdown_from_web(text)

    # Sort by start position (reverse order for proper offset calculation)
    formats.sort(key=lambda x: x["start"], reverse=True)

    # Build plain text by removing syntax and track position mappings
    plain_text = text
    position_map = {}  # Maps original positions to new positions

    for fmt in formats:
        start = fmt["start"]
        end = fmt["end"]
        content = fmt["content"]
        fmt_type = fmt["type"]

        # Calculate what to remove based on format type
        if fmt_type == "h1":
            plain_text = plain_text[:start] + content + plain_text[end:]
            position_map[fmt_type] = (start, start + len(content))
        elif fmt_type == "bold":
            plain_text = plain_text[:start] + content + plain_text[end:]
            position_map[fmt_type] = (start, start + len(content))
        elif fmt_type == "italic":
            plain_text = plain_text[:start] + content + plain_text[end:]
            position_map[fmt_type] = (start, start + len(content))
        elif fmt_type == "link":
            link_text = fmt["content"]
            plain_text = plain_text[:start] + link_text + plain_text[end:]
            position_map[fmt_type] = (start, start + len(link_text))
        elif fmt_type == "code":
            plain_text = plain_text[:start] + content + plain_text[end:]
            position_map[fmt_type] = (start, start + len(content))

    # Set plain text
    text_edit.setPlainText(plain_text)

    # Block signals and start edit block for performance
    text_edit.document().blockSignals(True)
    cursor = text_edit.textCursor()
    cursor.beginEditBlock()

    # Re-parse to get all formats with their new positions
    formats = parse_markdown_from_web(text)
    formats.sort(key=lambda x: x["start"], reverse=True)

    # Build mapping of original to plain text positions
    plain_text = text
    offset_map = {}
    current_offset = 0

    for fmt in formats:
        start = fmt["start"]
        end = fmt["end"]
        content = fmt["content"]
        fmt_type = fmt["type"]

        # Track the offset and new position
        if fmt_type == "h1":
            # H1 syntax: text\n---- the match.end() already includes the dashes
            # So the syntax_len is the difference between match end and content
            syntax_len = end - start - len(content)
            offset_map[start] = (start - current_offset, start - current_offset + len(content))
            current_offset += syntax_len
        elif fmt_type == "bold":
            syntax_len = len(f"**{content}**") - len(content)
            offset_map[start] = (start - current_offset, start - current_offset + len(content))
            current_offset += syntax_len
        elif fmt_type == "italic":
            syntax_len = len(f"_{content}_") - len(content)
            offset_map[start] = (start - current_offset, start - current_offset + len(content))
            current_offset += syntax_len
        elif fmt_type == "link":
            syntax_len = len(fmt["content"] + fmt.get("url", "")) + 4
            offset_map[start] = (start - current_offset, start - current_offset + len(content))
            current_offset += syntax_len
        elif fmt_type == "code":
            syntax_len = len(f"`{content}`") - len(content)
            offset_map[start] = (start - current_offset, start - current_offset + len(content))
            current_offset += syntax_len

    # Now apply formatting in correct order (forward iteration)
    formats_sorted = parse_markdown_from_web(text)
    formats_sorted.sort(key=lambda x: x['start'])

    # Create a list to accumulate offset changes
    cumulative_offset = 0
    format_list = []

    for fmt in formats_sorted:
        start = fmt["start"] - cumulative_offset
        content = fmt["content"]
        fmt_type = fmt["type"]
        url = fmt.get("url", "")

        if fmt_type == "h1":
            # H1: text\n---- becomes just text
            end = start + len(content)
            # The cumulative offset is the difference between original end and new end
            original_syntax_len = fmt["end"] - fmt["start"] - len(fmt["content"])
            cumulative_offset += original_syntax_len
        elif fmt_type == "bold":
            end = start + len(content)
            cumulative_offset += len(f"**{content}**") - len(content)
        elif fmt_type == "italic":
            end = start + len(content)
            cumulative_offset += len(f"_{content}_") - len(content)
        elif fmt_type == "link":
            end = start + len(content)
            cumulative_offset += len(fmt["content"] + fmt.get("url", "")) + 4
        elif fmt_type == "code":
            end = start + len(content)
            cumulative_offset += len(f"`{content}`") - len(content)

        format_list.append((fmt_type, start, end, url))

    # Apply formats from the accumulated list
    for fmt_type, start, end, url in format_list:
        char_fmt = QTextCharFormat()

        if fmt_type == "h1":
            # Get base font size and apply H1 styling (1.5x larger, bold)
            # Try multiple sources for font size
            base_size = text_edit.font().pointSize()
            if base_size <= 0:
                base_size = text_edit.document().defaultFont().pointSize()
            if base_size <= 0:
                base_size = text_edit.fontInfo().pointSize()
            if base_size <= 0:
                base_size = 12  # Fallback
            
            char_fmt.setFontPointSize(int(base_size * 1.5))
            char_fmt.setFontWeight(QFont.Weight.Bold)
            if styles and "h1" in styles and "color" in styles["h1"]:
                char_fmt.setForeground(styles["h1"]["color"])
        elif fmt_type == "bold":
            char_fmt.setFontWeight(QFont.Weight.Bold)
            if styles and "bold" in styles and "color" in styles["bold"]:
                char_fmt.setForeground(styles["bold"]["color"])
        elif fmt_type == "italic":
            char_fmt.setFontItalic(True)
            if styles and "italic" in styles and "color" in styles["italic"]:
                char_fmt.setForeground(styles["italic"]["color"])
        elif fmt_type == "link":
            char_fmt.setForeground(pal.link())
            char_fmt.setFontUnderline(True)
            # Set anchor href for link
            char_fmt.setAnchor(True)
            char_fmt.setAnchorHref(url)
            if styles and "link" in styles and "color" in styles["link"]:
                char_fmt.setForeground(styles["link"]["color"])
        elif fmt_type == "code":
            code_font = QFont()
            code_font.setFixedPitch(True)
            char_fmt.setFont(code_font)
            char_fmt.setForeground(pal.light())
            if styles and "code" in styles and "color" in styles["code"]:
                char_fmt.setForeground(styles["code"]["color"])

        # Apply format to the range
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.setCharFormat(char_fmt)

    # End edit block and unblock signals
    cursor.endEditBlock()
    text_edit.document().blockSignals(False)

    # Clear selection and place cursor at end
    cursor.clearSelection()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    text_edit.setTextCursor(cursor)


def format_comment_on_change(text_edit: QTextEdit) -> None:
    """Format QTextDocument to highlight mentions starting with @.

    Any word starting with @ will be formatted in red.
    """
    text_edit.document().blockSignals(True)

    pal = get_ayon_style().model.base_palette
    document = text_edit.document()
    cursor = text_edit.textCursor()
    fmt = cursor.charFormat()

    # Create a format for red text
    user_format = QTextCharFormat(fmt)
    user_format.setForeground(pal.link())
    url_format = QTextCharFormat(fmt)
    url_format.setForeground(pal.link())
    url_format.setFontUnderline(True)

    # Create a format for normal text
    normal_format = QTextCharFormat()

    # Get all text from document
    md = document.toMarkdown()

    users = [u.full_name for u in text_edit._user_list]

    # Find all words starting with @
    p_user = r"(?P<user>@\w+( \w+)?)"
    p_link = r"(?P<link>\[[\w\s]+\]\(.+\))"
    p_raw_link = r"(?P<raw_link>https?://)"
    p_all = f"{p_user}|{p_link}|{p_raw_link}"
    matches = list(re.finditer(p_all, md))

    # Clear all formatting first
    cursor.select(QTextCursor.SelectionType.Document)
    cursor.setCharFormat(normal_format)

    # We parsed the markdown but the cursor if using the plain text, so we
    # need to keep track of the number of extra markdown characters to keep
    # things aligned.
    xtra = 0
    for match in matches:
        for key, val in match.groupdict().items():
            if val is None:
                continue
            if key == "user":
                cursor.setPosition(match.start())
                if val[1:] in users:
                    cursor.setPosition(
                        match.end(), QTextCursor.MoveMode.KeepAnchor
                    )
                else:
                    cursor.setPosition(
                        match.end() - len(val.split()[-1]),
                        QTextCursor.MoveMode.KeepAnchor,
                    )

                cursor.setCharFormat(user_format)
            if key == "raw_link":
                cursor.setPosition(match.start())
                cursor.setPosition(
                    match.end(), QTextCursor.MoveMode.KeepAnchor
                )
                cursor.setCharFormat(user_format)
            elif key == "link":
                p0 = match.start() - xtra
                cursor.setPosition(p0)
                link_name = re.search(r"\[(.+)\]", val).group(1)
                p1 = (match.start() - xtra) + len(link_name)
                cursor.setPosition(p1, QTextCursor.MoveMode.KeepAnchor)
                xtra += len(val) - len(link_name) + 1
                cursor.setCharFormat(url_format)

    # Restore original cursor position
    text_edit.document().blockSignals(False)

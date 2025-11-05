from __future__ import annotations


from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import (
    QStandardItemModel,
    QStandardItem,
    QPainter,
    QTextCursor,
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
from .. import style_widget_and_siblings


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

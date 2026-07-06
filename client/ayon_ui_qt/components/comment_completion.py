from __future__ import annotations

import re
import logging

from qtpy.QtCore import QModelIndex, QSize, Qt
from qtpy.QtGui import (
    QColor,
    QFont,
    QPainter,
    QStandardItem,
    QStandardItemModel,
    QSyntaxHighlighter,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from qtpy.QtWidgets import (
    QCompleter,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTextEdit,
)

from ..style import get_ayon_style
from ..data_models import MentionEntity, Team, User
from .user_image import AYUserImage

# Mention prefix length -> AYON entity type. ``@`` = user, ``@@`` = version,
# ``@@@`` = task.  The numbers are the count of leading ``@`` characters.
# Teams share the single-``@`` level with users: the completer popup lists
# both, and the selected row decides whether a ``user:`` or ``team:`` mention
# is inserted.
MENTION_LEVELS: dict[int, str] = {1: "user", 2: "version", 3: "task"}

# AYON entity type -> the ``@`` prefix shown in front of a rendered mention.
MENTION_PREFIX: dict[str, str] = {
    "user": "@",
    "team": "@",
    "version": "@@",
    "task": "@@@",
}
# Anchor hrefs of this shape (``type:id``) are AYON mentions, not web links.
_MENTION_HREF_RE = re.compile(
    r"^(user|version|task|folder|product|representation|workfile|team):"
)

# Background colour used for both character-level (inline code) and
# block-level (fenced code block) highlighting.  Defined once here so
# that both the highlighter and ``apply_code_block_backgrounds()`` always
# use the same value.
CODE_BG: QColor = QColor("#1e1e1e")
CODE_FG: QColor = QColor("#eeeeee")


class UserCompleterDelegate(QStyledItemDelegate):
    """Custom delegate to display user/team icon and name in completer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_size = 20
        self._user_pixmap = {}

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,
    ) -> None:
        """Paint the avatar and name of a user or team row."""
        data = index.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, Team):
            avatar_src = ""
            cache_key = f"team:{data.name}"
            display_name = data.name
            label = f"{data.name}  ({len(data.members)} members)"
        elif isinstance(data, User):
            avatar_src = data.avatar_url
            cache_key = data.name
            display_name = data.full_name
            label = data.full_name
        else:
            super().paint(painter, option, index)
            return

        painter.save()

        # Draw background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.light())
        else:
            painter.fillRect(option.rect, option.palette.midlight())

        # Draw avatar (teams get an initials avatar from the team name)
        try:
            icon_pixmap = self._user_pixmap[cache_key]
        except KeyError:
            user_image = AYUserImage(
                src=avatar_src,
                full_name=display_name,
                size=self.icon_size,
                outline=False,
            )
            icon_pixmap = user_image.pixmap()
            self._user_pixmap[cache_key] = icon_pixmap

        icon_x = option.rect.x() + 4
        icon_y = option.rect.y() + (option.rect.height() - self.icon_size) // 2
        painter.drawPixmap(icon_x, icon_y, icon_pixmap)

        # Draw name — pen set explicitly so it always contrasts with the
        # background filled above, whatever pen the view handed us.
        painter.setPen(option.palette.text().color())
        text_x = icon_x + self.icon_size + 8
        text_rect = option.rect.adjusted(text_x, 0, 0, 0)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter,
            label,
        )

        painter.restore()

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index,
    ) -> QSize:
        """Return size hint for completer items."""
        return QSize(option.rect.width(), self.icon_size + 8)


class UserCompleterModel(QStandardItemModel):
    """Model for the single-``@`` completer level: users and teams."""

    def __init__(
        self,
        users: list[User],
        teams: list[Team] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.users = users
        self.teams = teams or []
        self._populate()

    def _populate(self) -> None:
        """Populate model with teams first, then users."""
        self.clear()
        for team in self.teams:
            item = QStandardItem(team.name)
            item.setData(team, Qt.ItemDataRole.UserRole)
            self.appendRow(item)
        for user in self.users:
            item = QStandardItem(user.full_name)
            item.setData(user, Qt.ItemDataRole.UserRole)
            self.appendRow(item)


class MentionCompleterModel(QStandardItemModel):
    """Completer model for version/task mentions.

    Each row's display text is the entity label and the row carries the
    :class:`~..data_models.MentionEntity` on ``Qt.ItemDataRole.UserRole`` so
    the activation handler can build the ``type:id`` mention link.
    """

    def __init__(self, entities: list[MentionEntity], parent=None):
        super().__init__(parent)
        self.entities = entities or []
        self._populate()

    def _populate(self) -> None:
        self.clear()
        for entity in self.entities:
            item = QStandardItem(entity.label)
            item.setData(entity, Qt.ItemDataRole.UserRole)
            self.appendRow(item)


def _placeholder_users() -> list[User]:
    """Single inert entry used when no user list is available yet."""
    return [
        User(
            name="not available",
            short_name="not available",
            full_name="not available",
            email="",
            avatar_url="",
        )
    ]


def _user_team_model(text_edit: QTextEdit) -> UserCompleterModel:
    """Build the merged user+team model for the single-``@`` level.

    The "not available" placeholder is only shown when there are neither
    users nor teams to offer.
    """
    users = getattr(text_edit, "_user_list", None) or []
    teams = getattr(text_edit, "_team_list", None) or []
    if not users and not teams:
        users = _placeholder_users()
    return UserCompleterModel(users, teams, text_edit)


def _build_mention_models(text_edit: QTextEdit) -> dict:
    """(Re)build the user/version/task completer models from the lists
    currently stored on *text_edit* and cache them on the widget."""
    versions = getattr(text_edit, "_version_list", None) or []
    tasks = getattr(text_edit, "_task_list", None) or []
    models = {
        "user": _user_team_model(text_edit),
        "version": MentionCompleterModel(versions, text_edit),
        "task": MentionCompleterModel(tasks, text_edit),
    }
    text_edit._mention_models = models  # type: ignore[attr-defined]
    return models


def setup_mention_completer(
    text_edit: QTextEdit,
    on_text_changed,
) -> None:
    """Setup the multi-level @mention completer for a QTextEdit widget.

    A single :class:`QCompleter` is shared across the three mention levels
    (``@`` user, ``@@`` version, ``@@@`` task); its model is swapped on the
    fly by :func:`on_completer_text_changed` based on the typed prefix.

    Args:
        text_edit: The QTextEdit widget to attach the completer to.
        on_text_changed: Callback for text changes.
    """
    models = _build_mention_models(text_edit)

    text_edit.completer = QCompleter(models["user"], text_edit)
    text_edit.completer.setCompletionMode(
        QCompleter.CompletionMode.PopupCompletion
    )
    text_edit.completer.setFilterMode(Qt.MatchFlag.MatchContains)
    text_edit.completer.setMaxVisibleItems(4)
    text_edit.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    text_edit.completer.setWidget(text_edit)

    # Delegates: avatars for users/teams, plain text for versions/tasks.
    popup = text_edit.completer.popup()
    if popup:
        # The popup is a top-level window, so it does not inherit the dark
        # AYON palette from the editor (notably when docked in a host app
        # like OpenRV) and comes up white-on-white. Apply the style palette
        # explicitly — the delegates read their colours from option.palette.
        popup.setPalette(get_ayon_style().model.base_palette)
        viewport = popup.viewport()
        if viewport:
            viewport.setPalette(get_ayon_style().model.base_palette)
        text_edit._user_delegate = UserCompleterDelegate(popup)
        text_edit._default_delegate = QStyledItemDelegate(popup)
        popup.setItemDelegate(text_edit._user_delegate)
        popup.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)

    # Insertion is driven by the selected popup index (not the display
    # string) so that non-unique labels still resolve to the right entity.
    # The default ``activated`` overload (QString) fires on both mouse and
    # keyboard selection; the string arg is ignored and the entity is read
    # from the popup's current index instead.
    text_edit.completer.activated.connect(
        lambda *_: insert_mention_from_index(
            text_edit, text_edit.completer.popup().currentIndex()
        )
    )
    text_edit.textChanged.connect(on_text_changed)


def _set_active_mention_model(text_edit: QTextEdit, mtype: str) -> None:
    """Swap the completer to the model (and delegate) for *mtype*."""
    models = getattr(text_edit, "_mention_models", None)
    if not models:
        return
    model = models.get(mtype)
    if model is None or text_edit.completer.model() is model:
        return
    text_edit.completer.setModel(model)
    popup = text_edit.completer.popup()
    if popup:
        delegate = (
            text_edit._user_delegate
            if mtype == "user"
            else text_edit._default_delegate
        )
        popup.setItemDelegate(delegate)


def on_users_updated(text_edit: QTextEdit):
    """Rebuild the user+team completer model after the user list changed."""
    if not hasattr(text_edit, "completer"):
        return
    models = getattr(text_edit, "_mention_models", None)
    if models is None:
        models = _build_mention_models(text_edit)
    models["user"] = _user_team_model(text_edit)


def on_teams_updated(text_edit: QTextEdit):
    """Rebuild the user+team completer model after the team list changed."""
    on_users_updated(text_edit)


def on_versions_updated(text_edit: QTextEdit):
    """Rebuild the version completer model after the version list changed."""
    if not hasattr(text_edit, "completer"):
        return
    versions = getattr(text_edit, "_version_list", None) or []
    models = getattr(text_edit, "_mention_models", None)
    if models is None:
        models = _build_mention_models(text_edit)
    models["version"] = MentionCompleterModel(versions, text_edit)


def on_tasks_updated(text_edit: QTextEdit):
    """Rebuild the task completer model after the task list changed."""
    if not hasattr(text_edit, "completer"):
        return
    tasks = getattr(text_edit, "_task_list", None) or []
    models = getattr(text_edit, "_mention_models", None)
    if models is None:
        models = _build_mention_models(text_edit)
    models["task"] = MentionCompleterModel(tasks, text_edit)


def detect_mention_level(text: str, pos_in_block: int):
    """Detect an in-progress @mention immediately before *pos_in_block*.

    Finds the nearest ``@`` left of the cursor, counts the contiguous run of
    ``@`` it belongs to (1=user, 2=version, 3=task; capped at 3), and returns
    the text typed after the run.

    Args:
        text: Plain text of the current block.
        pos_in_block: Cursor position within the block.

    Returns:
        ``(level, run_start, prefix)`` or ``None`` when the cursor is not
        inside a mention.
    """
    at_pos = text.rfind("@", 0, pos_in_block)
    if at_pos == -1:
        return None

    prefix = text[at_pos + 1 : pos_in_block]
    # A space directly after '@' means the user moved on — not a mention.
    if prefix and prefix[0].isspace():
        return None

    run_start = at_pos
    while run_start > 0 and text[run_start - 1] == "@":
        run_start -= 1
    level = min(at_pos - run_start + 1, 3)
    return level, run_start, prefix


def _entity_from_index(index: QModelIndex) -> MentionEntity | None:
    """Resolve the :class:`MentionEntity` for a completer popup index.

    User rows store a :class:`~..data_models.User` (mention id is the
    username); team rows store a :class:`~..data_models.Team` (mention id is
    the team name); version/task rows store a :class:`MentionEntity` directly.
    """
    if index is None or not index.isValid():
        return None
    data = index.data(Qt.ItemDataRole.UserRole)
    if data is None:
        return None
    if isinstance(data, MentionEntity):
        return data
    if isinstance(data, Team):
        return MentionEntity(id=data.name, label=data.name, type="team")
    if isinstance(data, User):
        if data.name == "not available":
            return None
        return MentionEntity(id=data.name, label=data.full_name, type="user")
    return None


def insert_mention_from_index(
    text_edit: QTextEdit, index: QModelIndex
) -> None:
    """Replace the in-progress ``@…`` token with an AYON mention link.

    The mention is inserted as a Qt anchor (``setAnchorHref("type:id")``)
    which :meth:`AYTextEditor.as_markdown` serializes to ``[label](type:id)``
    — the exact form the AYON server extracts references from.

    Args:
        text_edit: The QTextEdit being edited.
        index: Selected completer popup index carrying the entity payload.
    """
    entity = _entity_from_index(index)
    if entity is None:
        return

    cursor = text_edit.textCursor()
    block = cursor.block()
    pos_in_block = cursor.positionInBlock()
    det = detect_mention_level(block.text(), pos_in_block)
    if det is None:
        return
    _level, run_start, _prefix = det

    text_edit._suppress_formatting = True  # type: ignore[attr-defined]
    cursor.beginEditBlock()

    # Remove from the start of the '@' run to the cursor.
    cursor.setPosition(block.position() + run_start)
    cursor.setPosition(
        block.position() + pos_in_block,
        QTextCursor.MoveMode.KeepAnchor,
    )
    cursor.removeSelectedText()

    fmt = QTextCharFormat()
    fmt.setAnchor(True)
    fmt.setAnchorHref(f"{entity.type}:{entity.id}")
    fmt.setFontUnderline(True)
    fmt.setForeground(get_ayon_style().model.base_palette.link())
    cursor.insertText(entity.label, fmt)
    # Plain trailing space so the link is terminated in the markdown output.
    cursor.insertText(" ", QTextCharFormat())

    cursor.endEditBlock()
    text_edit.setTextCursor(cursor)
    # Stop the anchor format bleeding into the next typed characters.
    text_edit.setCurrentCharFormat(QTextCharFormat())
    text_edit._suppress_formatting = False  # type: ignore[attr-defined]

    popup = text_edit.completer.popup()
    if popup:
        popup.hide()


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
    pos_in_block = cursor.positionInBlock()

    det = detect_mention_level(block.text(), pos_in_block)
    if det is None:
        popup = text_edit.completer.popup()
        if popup:
            popup.hide()
        return

    level, run_start, prefix = det
    _set_active_mention_model(text_edit, MENTION_LEVELS[level])
    text_edit.completer.setCompletionPrefix(prefix)
    show_completer_popup(text_edit, run_start)
    # Auto-select if only one item
    popup = text_edit.completer.popup()
    if popup:
        popup_model = popup.model()
        row_count = popup_model.rowCount() if popup_model else 0
        if row_count == 1:
            popup.setCurrentIndex(popup_model.index(0, 0))


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
            # Insert the mention for the selected popup row directly from
            # its entity payload (the display string is not unique).
            current_index = popup.currentIndex()
            if current_index.isValid():
                insert_mention_from_index(text_edit, current_index)
                return True
    return False


class MentionHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for @mentions, raw URLs, and code spans.

    Operates on block-local plain text so positions are always correct
    regardless of any rich-text formatting already present in the document
    (bold, italic, headings, code spans, etc.).

    Patterns highlighted:

    - Fenced code blocks (```\\`\\`\\` ... \\`\\`\\```) spanning multiple lines —
      black background, white monospace text.  Block state ``1`` tracks
      whether the current block is inside a fence.
    - Qt-rendered code blocks (from ``setMarkdown()``) — detected via
      ``nonBreakableLines`` on the block format.
    - Qt-rendered inline code spans (from ``setMarkdown()``) — detected via
      ``fontFixedPitch`` on individual text fragments.
    - Inline code spans (`` \\`code\\` ``) in raw (un-rendered) text — same
      style, detected by backtick regex.
    - ``@@@word`` — task mention
    - ``@@word``  — version mention
    - ``@word``   — user or team mention (only the first word if the full
      name is not in the known user/team lists; both words when it is)
    - ``https?://…`` — raw URL

    Args:
        document: The QTextDocument to attach to.
        user_list: Live list of :class:`~..data_models.User` objects used to
            decide whether a two-word mention should be highlighted in full.
        team_list: Live list of :class:`~..data_models.Team` objects, used
            the same way for team-name mentions.
    """

    # Compiled patterns — order matters: longer prefixes first so that
    # ``@@@`` is matched before ``@@`` and ``@@`` before ``@``.
    _P_TASK = re.compile(r"@@@\w+( \w+)?")
    _P_VERSION = re.compile(r"@@(?!@)\w+( \w+)?")
    _P_USER = re.compile(r"@(?!@)\w+( \w+)?")
    _P_RAW_LINK = re.compile(r"https?://\S+")
    # Inline code: single backtick pair on the same line.
    _P_CODE_INLINE = re.compile(r"`[^`\n]+`")

    def __init__(
        self, document, user_list: list, team_list: list | None = None
    ) -> None:
        super().__init__(document)
        self._user_list = user_list
        # Keep the caller's list object (even when empty):
        # format_comment_on_change compares by identity to decide whether a
        # rehighlight is needed, so substituting a fresh [] here would
        # trigger one on every keystroke.
        self._team_list = team_list if team_list is not None else []
        pal = get_ayon_style().model.base_palette
        self._mention_fmt = QTextCharFormat()
        self._mention_fmt.setForeground(pal.link())
        self._code_fmt = QTextCharFormat()
        self._code_fmt.setFontFixedPitch(True)
        self._code_fmt.setFontFamilies(
            ["Courier New", "Menlo", "Monaco", "monospace"]
        )
        self._code_fmt.setBackground(CODE_BG)
        self._code_fmt.setForeground(CODE_FG)

    def update_user_list(self, user_list: list) -> None:
        """Replace the user list and trigger a full rehighlight.

        Args:
            user_list: Updated list of User objects.
        """
        self._user_list = user_list
        self.rehighlight()

    def update_team_list(self, team_list: list) -> None:
        """Replace the team list and trigger a full rehighlight.

        Args:
            team_list: Updated list of Team objects.
        """
        # Identity must be preserved — see the note in __init__.
        self._team_list = team_list if team_list is not None else []
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        """Apply code, mention, and URL highlighting to a single block.

        Two detection strategies are combined so that code is styled in both
        *edit mode* (raw markdown typed by the user) and *display mode*
        (rich text rendered via ``document().setMarkdown()``):

        **Edit mode — raw fence markers:**
        Uses block state ``1`` to track multi-line fenced code blocks. A line
        starting with *```* opens or closes a fence; every line inside the
        fence is styled with :attr:`_code_fmt`.  A line that both opens and
        closes a fence on the same line (e.g. ``\\`\\`\\`code\\`\\`\\```) is
        treated as a single-line code block with no state change.

        **Display mode — Qt-rendered char formats:**
        After ``setMarkdown()`` Qt strips the fence markers and stores rich
        text character formats.  Fenced code blocks have
        ``nonBreakableLines=True`` set on the block format (``fontFixedPitch``
        stays ``False`` on the block-level char format).  Inline code spans
        set ``fontFixedPitch=True`` on individual text *fragments* within a
        paragraph.  Both are detected here and styled with :attr:`_code_fmt`.

        Inline code spans from raw backtick syntax (`` \\`code\\` ``) are also
        detected via :attr:`_P_CODE_INLINE` for live-typed backtick spans.

        Code formatting is applied *after* mention/URL patterns so that it
        takes precedence over any mention highlight inside a code span.

        Called automatically by Qt whenever the block changes.

        Args:
            text: Plain text content of the current block.
        """
        block = self.currentBlock()
        in_fence = self.previousBlockState() == 1

        # ── Edit mode: raw fence markers ─────────────────────────────────
        if in_fence:
            # The entire line belongs to the open fenced block.
            self.setFormat(0, len(text), self._code_fmt)
            # A line starting with ``` closes the fence.
            if text.startswith("```"):
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(1)
            return

        if text.startswith("```"):
            self.setFormat(0, len(text), self._code_fmt)
            rest = text[3:]
            # Closing ``` on the same line → single-line block, no state.
            if "```" in rest:
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(1)
            return

        self.setCurrentBlockState(0)

        # ── Display mode: Qt-rendered whole-block code ───────────────────
        # After setMarkdown(), Qt marks fenced code block lines with
        # nonBreakableLines=True on the block format.  The char format
        # carries fontFamilies=['monospace'] but fontFixedPitch stays False.
        # Style the whole line and skip mention/URL patterns — they don't
        # belong inside code.
        if block.blockFormat().nonBreakableLines():
            self.setFormat(0, len(text), self._code_fmt)
            return

        # ── Mentions and URLs (applied before inline code) ───────────────
        known_names = {u.full_name for u in self._user_list}
        known_names.update(t.name for t in self._team_list)

        # Task mentions (@@@)
        for m in self._P_TASK.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._mention_fmt)

        # Version mentions (@@)
        for m in self._P_VERSION.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._mention_fmt)

        # User/team mentions (@) — highlight only the first word unless the
        # full two-word name is a known user full name or team name.
        for m in self._P_USER.finditer(text):
            full_match = m.group(0)
            mention_name = full_match[1:]  # strip leading @
            if mention_name in known_names:
                length = len(full_match)
            else:
                # Highlight only up to the first word (no trailing space+word)
                length = len(full_match.split()[0])
            self.setFormat(m.start(), length, self._mention_fmt)

        # Raw URLs
        for m in self._P_RAW_LINK.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._mention_fmt)

        # ── Inline code (applied last, overrides mention formatting) ─────

        # Raw backtick syntax `code` — detected in plain text for live
        # editing where backtick characters are still present:
        for m in self._P_CODE_INLINE.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._code_fmt)

        # Qt-rendered inline code spans — after setMarkdown() the backticks
        # are consumed and individual fragments carry fontFixedPitch=True:
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid() and fragment.charFormat().fontFixedPitch():
                frag_start = fragment.position() - block.position()
                self.setFormat(frag_start, fragment.length(), self._code_fmt)
            it += 1


def format_comment_on_change(text_edit: QTextEdit) -> None:
    """Ensure a :class:`MentionHighlighter` is installed on *text_edit*.

    Idempotent: safe to call on every ``contentsChanged`` signal.  The
    highlighter is created once and attached to the document.  Subsequent
    calls only call :meth:`MentionHighlighter.update_user_list` when the
    ``_user_list`` reference on *text_edit* has been replaced (e.g. after a
    server refresh), which avoids triggering an unnecessary ``rehighlight``
    — and the infinite-recursion that would follow — on every keystroke.

    Args:
        text_edit: The QTextEdit whose document should have mention
            highlighting applied.
    """
    highlighter: MentionHighlighter | None = getattr(
        text_edit, "_mention_highlighter", None
    )
    user_list = getattr(text_edit, "_user_list", [])
    team_list = getattr(text_edit, "_team_list", [])

    if highlighter is None:
        highlighter = MentionHighlighter(
            text_edit.document(), user_list, team_list
        )
        text_edit._mention_highlighter = highlighter  # type: ignore[attr-defined]
    else:
        # A list object was replaced (e.g. after a server refresh).
        # update_*_list() calls rehighlight() which is safe here because
        # these branches are only reached when _suppress_formatting is False
        # and the list identity has changed — not on every keystroke.
        if highlighter._user_list is not user_list:
            highlighter.update_user_list(user_list)
        if highlighter._team_list is not team_list:
            highlighter.update_team_list(team_list)


def markdown_with_clean_emphasis(text_edit: QTextEdit, dialect) -> str:
    """Serialize the document to markdown with valid emphasis boundaries.

    Qt serializes a bold/italic run that includes a leading or trailing
    space as e.g. ``** text**``, which is invalid CommonMark and renders as
    literal asterisks. This works on a *clone* of the document (no visible
    side effect), strips bold/italic off any boundary whitespace so the
    markers end up adjacent to text, then returns ``toMarkdown``.

    Only genuine bold/italic character runs are touched — bullet markers,
    literal (escaped) asterisks, and code spans are unaffected, because the
    transform operates on character formats rather than on the markdown text.

    The AYON style applies a global Medium (500) font weight, and
    ``QTextMarkdownWriter`` resolves fragments with no explicit
    ``FontWeight`` against that application font — anything above Normal
    (400) counts as bold, so every plain-text run would serialize wrapped
    in ``**``. Runs split by a mention anchor then start on the space after
    the mention (``[label](user:id)** text**``), which is the invalid form
    above. To prevent this, every fragment that is not genuinely bold
    (explicit weight above Medium) gets an explicit Normal weight pinned on
    the clone before serializing.

    Args:
        text_edit: The editor whose document should be serialized.
        dialect: The ``QTextDocument.MarkdownFeature`` dialect to use.

    Returns:
        GitHub-flavored markdown string with normalized emphasis.
    """
    doc = text_edit.document().clone()

    edits: list[tuple[int, int]] = []  # (pos, length) of bold/italic whitespace
    normal_runs: list[tuple[int, int]] = []  # runs pinned to Normal weight
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid():
                fmt = fragment.charFormat()
                # QFont.bold() semantics: only weights above Medium render
                # (and serialize) as bold. Anything at or below Medium is
                # style bleed, not user emphasis.
                bold = fmt.fontWeight() > QFont.Weight.Medium
                if not bold:
                    normal_runs.append(
                        (fragment.position(), fragment.length())
                    )
                if bold or fmt.fontItalic():
                    text = fragment.text()
                    if text.strip() and text.strip() != text:
                        base = fragment.position()
                        lead = len(text) - len(text.lstrip())
                        trail = len(text) - len(text.rstrip())
                        if lead:
                            edits.append((base, lead))
                        if trail:
                            edits.append((base + len(text) - trail, trail))
            it += 1
        block = block.next()

    if edits or normal_runs:
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        normal_fmt = QTextCharFormat()
        normal_fmt.setFontWeight(QFont.Weight.Normal)
        for pos, length in normal_runs:
            cursor.setPosition(pos)
            cursor.setPosition(pos + length, QTextCursor.MoveMode.KeepAnchor)
            cursor.mergeCharFormat(normal_fmt)
        clear_fmt = QTextCharFormat()
        clear_fmt.setFontWeight(QFont.Weight.Normal)
        clear_fmt.setFontItalic(False)
        for pos, length in edits:
            cursor.setPosition(pos)
            cursor.setPosition(pos + length, QTextCursor.MoveMode.KeepAnchor)
            cursor.mergeCharFormat(clear_fmt)
        cursor.endEditBlock()

    return doc.toMarkdown(dialect)


# Fenced code blocks and inline code spans — protected from emphasis
# sanitization because ``**`` inside code is literal content.
_P_CODE_SEGMENT = re.compile(r"```.*?(?:```|$)|`[^`\n]+`", re.DOTALL)
# A ``**…**`` span whose inner text has boundary whitespace — invalid
# CommonMark that renders as literal asterisks.
_P_BAD_BOLD = re.compile(r"\*\*((?:[^*\n]|\*(?!\*))+)\*\*")


def sanitize_invalid_emphasis(md: str) -> str:
    """Repair invalid ``**`` emphasis in stored markdown for display.

    Comments submitted before the Medium-font-weight serialization fix (see
    :func:`markdown_with_clean_emphasis`) may contain bold spans with
    boundary whitespace — ``[label](user:id)** text**`` — which is invalid
    CommonMark and renders as literal asterisks. This moves the boundary
    whitespace outside the markers (``** text**`` → `` **text**``) and drops
    markers around whitespace-only spans. Code fences and inline code spans
    are left untouched.

    Args:
        md: Markdown text about to be displayed.

    Returns:
        Markdown with valid emphasis boundaries.
    """

    def _fix_bold(m: re.Match) -> str:
        inner = m.group(1)
        stripped = inner.strip()
        if not stripped:
            return inner  # ``** **`` → just the whitespace
        if stripped == inner:
            return m.group(0)  # already valid
        lead = inner[: len(inner) - len(inner.lstrip())]
        trail = inner[len(inner.rstrip()):]
        return f"{lead}**{stripped}**{trail}"

    out: list[str] = []
    pos = 0
    for code in _P_CODE_SEGMENT.finditer(md):
        out.append(_P_BAD_BOLD.sub(_fix_bold, md[pos : code.start()]))
        out.append(code.group(0))
        pos = code.end()
    out.append(_P_BAD_BOLD.sub(_fix_bold, md[pos:]))
    return "".join(out)


def style_mention_anchors(text_edit: QTextEdit) -> None:
    """Render AYON mention links as mentions rather than web hyperlinks.

    After ``document().setMarkdown()`` an AYON mention (``[label](type:id)``)
    becomes a default anchor — blue and underlined, indistinguishable from a
    URL. This restyles those anchors to the mention colour without an
    underline and prefixes the matching ``@`` marker (``@`` / ``@@`` / ``@@@``)
    so they read like the mentions shown in the AYON web feed. Real web links
    (``http(s)://…``) are left untouched.

    Intended for **read-only display** fields only: it inserts the ``@``
    prefix as plain text, which would corrupt the markdown round-trip if the
    field were later submitted. Guarded by ``_suppress_formatting`` so it does
    not re-enter the ``contentsChanged`` formatting pass.

    Args:
        text_edit: The read-only QTextEdit whose document has just been
            populated via ``setMarkdown``.
    """
    doc = text_edit.document()

    # Collect mention anchor fragments first; mutating while iterating the
    # fragment list is unsafe.
    spans: list[tuple[int, int, str]] = []  # (pos, length, display_text)
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid():
                fmt = fragment.charFormat()
                if fmt.isAnchor():
                    href = fmt.anchorHref() or ""
                    match = _MENTION_HREF_RE.match(href)
                    if match:
                        prefix = MENTION_PREFIX.get(match.group(1), "@")
                        spans.append(
                            (
                                fragment.position(),
                                fragment.length(),
                                f"{prefix}{fragment.text()}",
                            )
                        )
            it += 1
        block = block.next()

    if not spans:
        return

    previous = getattr(text_edit, "_suppress_formatting", False)
    text_edit._suppress_formatting = True  # type: ignore[attr-defined]
    cursor = QTextCursor(doc)
    cursor.beginEditBlock()

    link_color = get_ayon_style().model.base_palette.link()
    mention_fmt = QTextCharFormat()
    mention_fmt.setForeground(link_color)
    mention_fmt.setFontUnderline(False)

    # Replace each anchor with a plain, mention-coloured token (no anchor, so
    # it neither underlines nor shows a link cursor). Work from the end so
    # earlier positions stay valid as text length changes.
    for pos, length, display_text in reversed(spans):
        cursor.setPosition(pos)
        cursor.setPosition(pos + length, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(display_text, QTextCharFormat(mention_fmt))

    cursor.endEditBlock()
    text_edit._suppress_formatting = previous  # type: ignore[attr-defined]


def apply_code_block_backgrounds(text_edit: QTextEdit) -> None:
    """Apply a full-width background colour to every fenced code block.

    ``QSyntaxHighlighter.setFormat()`` only paints behind individual
    text characters, so the end of a short line keeps the regular widget
    background.  Setting ``QTextBlockFormat.background`` instead causes
    Qt's own layout engine to paint the background across the *entire*
    width of the block before any characters are drawn.

    This function is intentionally separate from
    :class:`MentionHighlighter` because Qt's documentation forbids
    modifying the document from inside ``highlightBlock()``.

    Two detection strategies are combined so that code blocks are
    recognised in both scenarios:

    - **Display mode** (after ``document().setMarkdown()``): Qt marks
      fenced code block lines with ``nonBreakableLines=True`` on the
      block format.
    - **Edit mode** (raw typing): Lines inside a ``\\`\\`\\`…\\`\\`\\```` fence
      are detected by tracking an open-fence flag while iterating from
      the first block of the document.

    The function is guarded by the ``_suppress_formatting`` attribute on
    *text_edit* to prevent infinite recursion: writing block formats
    emits ``contentsChanged``, which would otherwise re-enter this
    function.

    Args:
        text_edit: The QTextEdit whose document should have fenced code
            block backgrounds applied.
    """
    if getattr(text_edit, "_suppress_formatting", False):
        return

    doc = text_edit.document()
    setattr(text_edit, "_suppress_formatting", True)

    cursor = QTextCursor(doc)
    cursor.beginEditBlock()

    try:
        in_fence = False
        block = doc.begin()
        while block.isValid():
            text = block.text()
            is_code = False

            # Display mode: Qt-rendered fenced code block.
            if block.blockFormat().nonBreakableLines():
                is_code = True
            else:
                # Edit mode: raw ``` fence markers.
                if in_fence:
                    is_code = True
                    if text.startswith("```"):
                        in_fence = False  # closing fence line — still code
                elif text.startswith("```"):
                    is_code = True
                    rest = text[3:]
                    if "```" not in rest:
                        in_fence = True  # opening fence
                    # else: single-line ```…``` — is_code=True, no state change

            bg_brush = block.blockFormat().background()
            has_code_bg = (
                bg_brush.style() != Qt.BrushStyle.NoBrush
                and bg_brush.color().rgb() == CODE_BG.rgb()
            )

            if is_code and not has_code_bg:
                cursor.setPosition(block.position())
                new_fmt = QTextBlockFormat()
                new_fmt.setBackground(CODE_BG)
                cursor.mergeBlockFormat(new_fmt)
            elif not is_code and has_code_bg:
                # Remove the previously applied code background.
                cursor.setPosition(block.position())
                restored = QTextBlockFormat(block.blockFormat())
                restored.clearBackground()
                cursor.setBlockFormat(restored)

            block = block.next()
    except Exception as e:
        logging.info(f"Error in apply_code_block_backgrounds: {e}")
    finally:
        # Ensure we always end the edit block and reset the flag
        cursor.endEditBlock()
        setattr(text_edit, "_suppress_formatting", False)

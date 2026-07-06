"""Markdown serialization of AYTextEditor comments.

Regression tests for the AYON style's global Medium (500) font weight
leaking into ``toMarkdown``: QTextMarkdownWriter resolves fragments with no
explicit FontWeight against the application font, so every plain-text run
used to serialize wrapped in ``**`` — and runs split by a mention anchor
started on a space (``[label](user:id)** text**``), which is invalid
CommonMark and rendered as literal asterisks after submit.
"""

from __future__ import annotations

from qtpy.QtGui import QTextCharFormat, QTextCursor

from ayon_ui_qt.components.text_box import AYTextEditor


def _insert_mention(editor: AYTextEditor, label: str, href: str) -> None:
    """Insert a mention anchor the same way insert_mention_from_index does."""
    cursor = editor.textCursor()
    editor._suppress_formatting = True
    fmt = QTextCharFormat()
    fmt.setAnchor(True)
    fmt.setAnchorHref(href)
    fmt.setFontUnderline(True)
    cursor.insertText(label, fmt)
    cursor.insertText(" ", QTextCharFormat())
    editor.setTextCursor(cursor)
    editor.setCurrentCharFormat(QTextCharFormat())
    editor._suppress_formatting = False


def test_plain_text_serializes_without_emphasis(qtbot) -> None:
    editor = AYTextEditor(user_list=[])
    qtbot.addWidget(editor)
    qtbot.keyClicks(editor, "hey john check this")
    assert editor.as_markdown().strip() == "hey john check this"


def test_text_after_mention_has_no_asterisks(qtbot) -> None:
    editor = AYTextEditor(user_list=[])
    qtbot.addWidget(editor)
    _insert_mention(editor, "John Doe", "user:john.doe")
    qtbot.keyClicks(editor, "please check")
    md = editor.as_markdown().strip()
    assert md == "[John Doe](user:john.doe) please check"


def test_text_before_mention_has_no_asterisks(qtbot) -> None:
    editor = AYTextEditor(user_list=[])
    qtbot.addWidget(editor)
    qtbot.keyClicks(editor, "hello ")
    _insert_mention(editor, "John Doe", "user:john.doe")
    md = editor.as_markdown().strip()
    assert md == "hello [John Doe](user:john.doe)"


def test_explicit_bold_survives(qtbot) -> None:
    editor = AYTextEditor(user_list=[])
    qtbot.addWidget(editor)
    qtbot.keyClicks(editor, "make this bold now")
    cursor = editor.textCursor()
    cursor.setPosition(5)
    cursor.setPosition(14, QTextCursor.MoveMode.KeepAnchor)  # "this bold"
    editor.setTextCursor(cursor)
    editor.set_style("stl_bold")
    assert editor.as_markdown().strip() == "make **this bold** now"


def test_bold_boundary_whitespace_trimmed(qtbot) -> None:
    editor = AYTextEditor(user_list=[])
    qtbot.addWidget(editor)
    qtbot.keyClicks(editor, "edge case here")
    cursor = editor.textCursor()
    cursor.setPosition(4)
    cursor.setPosition(10, QTextCursor.MoveMode.KeepAnchor)  # " case " w/ spaces
    editor.setTextCursor(cursor)
    editor.set_style("stl_bold")
    assert editor.as_markdown().strip() == "edge **case** here"


def test_sanitize_invalid_emphasis_legacy_bodies() -> None:
    from ayon_ui_qt.components.comment_completion import (
        sanitize_invalid_emphasis,
    )

    # Broken bodies stored before the serialization fix
    assert (
        sanitize_invalid_emphasis("[John Doe](user:jd)** please check**")
        == "[John Doe](user:jd) **please check**"
    )
    assert (
        sanitize_invalid_emphasis("**hello [John Doe](user:jd) **")
        == "**hello [John Doe](user:jd)** "
    )
    assert sanitize_invalid_emphasis("[John Doe](user:jd)** **") == (
        "[John Doe](user:jd) "
    )
    # Valid emphasis and code spans are untouched
    assert sanitize_invalid_emphasis("a **bold** word") == "a **bold** word"
    assert (
        sanitize_invalid_emphasis("code `** raw**` span")
        == "code `** raw**` span"
    )
    fenced = "```\n** raw**\n```"
    assert sanitize_invalid_emphasis(fenced) == fenced


def test_legacy_broken_body_displays_without_asterisks(qtbot) -> None:
    editor = AYTextEditor(user_list=[], read_only=True)
    qtbot.addWidget(editor)
    editor.set_markdown("[John Doe](user:jd)** please check**")
    assert "*" not in editor.toPlainText()


def test_checklist_comment_has_no_bold_bleed(qtbot) -> None:
    editor = AYTextEditor(user_list=[])
    qtbot.addWidget(editor)
    source = "- [ ] first task\n- [x] second task"
    editor.set_markdown(source)
    md = editor.as_markdown()
    assert "**" not in md
    assert "- [ ] first task" in md
    assert "- [x] second task" in md


def test_markdown_round_trip_is_stable(qtbot) -> None:
    editor = AYTextEditor(user_list=[])
    qtbot.addWidget(editor)
    source = (
        "regular **bold** and *italic* text with "
        "[John Doe](user:john.doe) mention"
    )
    editor.set_markdown(source)
    assert editor.as_markdown().strip() == source

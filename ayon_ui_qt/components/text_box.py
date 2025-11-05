from __future__ import annotations

import logging
from functools import partial

from qtpy.QtCore import (
    QObject,
    Signal,  # type: ignore
    Slot,  # type: ignore
)  # type: ignore
from qtpy import QtWidgets
from qtpy.QtGui import (
    QFont,
    QTextCursor,
    QTextDocument,
    QTextFrameFormat,
)
from qtpy.QtWidgets import (
    QSizePolicy,
    QTextEdit,
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
        lyt = AYHBoxLayout(self, margin=0, spacing=0)
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

    def _on_category_changed(self, category: str) -> None:
        self.category = category

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
        return w

    test(build, style=Style.Widget)

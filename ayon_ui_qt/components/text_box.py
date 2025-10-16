from functools import partial
from qtpy import QtCore, QtWidgets
from qtpy.QtGui import (
    QTextDocument,
    QTextCursor,
    QFont,
    QTextFrameFormat,
)
from qtpy.QtWidgets import QTextEdit, QSizePolicy
from .layouts import AYHBoxLayout, AYVBoxLayout
from .frame import AYFrame
from .buttons import AYButton


class AYTextEditor(QTextEdit):
    def __init__(
        self, *args, max_lines: int = 4, read_only: bool = False, **kwargs
    ):
        # remove our kwargs
        self.max_lines: int = max_lines
        self._read_only: bool = read_only

        super().__init__(*args, **kwargs)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        self._style = self.style().model.get_style("QTextEdit")

        # automatic bullet lists
        self.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)

        if not self._read_only:
            self.setPlaceholderText(
                "Comment or mention with @user, @@version, @@@task..."
            )
        self.setReadOnly(self._read_only)

    def set_style(self, style):
        print(f"style: {style}")
        cursor = self.textCursor()
        # print(f"selected: {cursor.selectedText()}")
        if style == "stl_h1":
            cursor.beginEditBlock()
            char_format = cursor.blockCharFormat()

            # Check if already a header (by checking font size)
            current_size = cursor.charFormat().fontPointSize()
            base_size = self.font().pointSize()

            print(f"current_size = {current_size}   base_size = {base_size}")

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


class AYTextBoxSignals(QtCore.QObject):
    # Signal emitted when comment button is clicked, passes markdown content
    comment_submitted = QtCore.Signal(str)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._build()

    def _build_upper_bar(self):
        grp_spacing = 16
        lyt = AYHBoxLayout(self, spacing=0, margin=0)
        for var, icn in self.style_icons.items():
            setattr(self, var, AYButton(self, variant="nav", icon=icn))
            lyt.addWidget(getattr(self, var))
        # separator
        lyt.addSpacing(grp_spacing)
        for var, icn in self.format_icons.items():
            setattr(self, var, AYButton(self, variant="nav", icon=icn))
            lyt.addWidget(getattr(self, var))
        lyt.addSpacing(grp_spacing)
        lyt.addWidget(AYButton(self, variant="nav", icon="attach_file"))
        lyt.addSpacerItem(
            QtWidgets.QSpacerItem(
                0, 0, QtWidgets.QSizePolicy.Policy.MinimumExpanding
            )
        )
        return lyt

    def _build_edit_field(self):
        self.edit_field = AYTextEditor(self)
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
            QtWidgets.QSpacerItem(
                0, 0, QtWidgets.QSizePolicy.Policy.MinimumExpanding
            )
        )
        self.comment_button = AYButton("Comment", variant="filled")
        self.comment_button.clicked.connect(self._on_comment_clicked)
        lyt.addWidget(self.comment_button)
        return lyt

    def _on_comment_clicked(self) -> None:
        """Handle comment button click and emit signal with markdown content."""
        markdown_content = self.edit_field.document().toMarkdown()
        self.signals.comment_submitted.emit(markdown_content)

    def _build(self):
        lyt = AYVBoxLayout(self, margin=4, spacing=0)
        lyt.addLayout(self._build_upper_bar())
        lyt.addWidget(self._build_edit_field(), stretch=10)
        lyt.addLayout(self._build_lower_bar())

    def set_markdown(self, md: str):
        self.edit_field.document().setMarkdown(
            md, QTextDocument.MarkdownFeature.MarkdownDialectGitHub
        )


# TEST ------------------------------------------------------------------------


if __name__ == "__main__":
    from ..tester import test

    def build():
        w = QtWidgets.QWidget()
        lyt = AYVBoxLayout(w, margin=8)
        ww = AYTextBox(parent=w)
        ww.set_markdown(
            "## Title\nText can be **bold** or *italic*, as expected !\n"
            "- [ ] Do this\n- [ ] Do that\n"
        )
        lyt.addWidget(ww)
        ww.signals.comment_submitted.connect(
            lambda x: print(f"Comment {'=' * 70}\n{x}{'=' * 78}")
        )
        return w

    test(build, use_css=False)

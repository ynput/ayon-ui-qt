from functools import partial
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtGui import QTextDocument
from qtpy.QtWidgets import QPlainTextEdit
from ayon_ui_qt.layouts import AYHBoxLayout, AYVBoxLayout
from ayon_ui_qt.frame import AYFrame
from ayon_ui_qt.buttons import AYButton


class AYTextEditor(QPlainTextEdit):
    def __init__(
        self, *args, max_lines: int = 4, read_only: bool = False, **kwargs
    ):
        # remove our kwargs
        self.max_lines: int = max_lines
        self._read_only: bool = read_only

        super().__init__(*args, **kwargs)

        # configure
        # 1.4 is a magic number because the font size comes from qss so always
        # unpredictable.
        # FIXME: internalize QSS ?
        line_height = int(self.fontMetrics().lineSpacing() * 1.4)
        self.setFixedHeight(line_height * max_lines)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        if not self._read_only:
            self.setPlaceholderText(
                "Comment or mention with @user, @@version, @@@task..."
            )
        self.setReadOnly(self._read_only)

    def set_style(self, style):
        print(f"style: {style}")

    def set_format(self, format):
        print(f"format: {format}")


class AYTextBox(AYFrame):
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
        lyt.addWidget(AYButton("Comment", variant="filled"))
        return lyt

    def _build(self):
        lyt = AYVBoxLayout(self, margin=4, spacing=0)
        lyt.addLayout(self._build_upper_bar())
        lyt.addWidget(self._build_edit_field())
        lyt.addLayout(self._build_lower_bar())


# TEST ------------------------------------------------------------------------


if __name__ == "__main__":
    from ayon_ui_qt.tester import test

    def build():
        w = QtWidgets.QWidget()
        lyt = AYVBoxLayout(w, margin=8)
        lyt.addWidget(AYTextBox(parent=w))
        return w

    test(build, use_css=False)

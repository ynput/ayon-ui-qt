import os
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field

from qtpy import QtCore, QtGui, QtWidgets

from ayon_ui_qt.components.frame import AYFrame
from ayon_ui_qt.components.layouts import AYVBoxLayout, AYHBoxLayout
from ayon_ui_qt.components.buttons import AYButton
from ayon_ui_qt.components.label import AYLabel
from ayon_ui_qt.components.user_image import AYUserImage


# PUBLISH ---------------------------------------------------------------------

@dataclass
class PublishedModel:
    user_full_name: str = ""
    user_name: str = ""
    user_src: str = ""
    version: str = ""
    product: str = ""
    date: str = ""

    def __post_init__(self):
        if self.date:
            # Parse the ISO string
            dt = datetime.fromisoformat(self.date)
            self._short_date = dt.strftime("%b %d, %I:%M %p")

    @property
    def type(self):
        return "publish"

    @property
    def short_date(self):
        return self._short_date


# COMMENT ---------------------------------------------------------------------


@dataclass
class CommentModel:
    user_full_name: str = ""
    user_name: str = ""
    user_src: str = ""
    comment: str = ""
    comment_date: str = ""

    def __post_init__(self):
        if self.comment_date:
            # Parse the ISO string
            dt = datetime.fromisoformat(self.comment_date)
            self._short_date = dt.strftime("%b %d, %I:%M %p")

    @property
    def type(self):
        return "comment"

    @property
    def short_date(self):
        return self._short_date


class AYCommentField(QtWidgets.QTextBrowser):
    def __init__(self, *args, **kwargs):
        # remove our kwargs
        max_lines: int = kwargs.pop("max_lines", 4)
        self._text: str = kwargs.pop("text", None)
        self._read_only: bool = kwargs.pop("read_only", False)

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


class AYComment(AYFrame):
    def __init__(self, *args, **kwargs):
        self._data: CommentModel = kwargs.pop("data", CommentModel())

        super().__init__(*args, bg=True, **kwargs)

        self._build()
        # configure
        if self._data:
            self.text_field.setPlainText(self._data.comment)
            self.date.setText(self._data.short_date)

    def _build_top_bar(self):
        self.user_icon = AYUserImage(
            parent=self,
            size=20,
            src=self._data.user_src,
            name=self._data.user_name,
            full_name=self._data.user_full_name,
            outline=False,
        )
        self.user_name = AYLabel(self._data.user_full_name, tag="h4")
        self.date = AYLabel(self._data.short_date, tag="h4", dim=True)
        lyt = AYHBoxLayout(margin=0)
        lyt.addWidget(self.user_icon)
        lyt.addWidget(self.user_name)
        lyt.addSpacerItem(
            QtWidgets.QSpacerItem(
                0, 0, QtWidgets.QSizePolicy.Policy.MinimumExpanding
            )
        )
        lyt.addWidget(self.date)
        return lyt

    def _build(self):
        lyt = AYVBoxLayout(self, margin=0)
        lyt.addLayout(self._build_top_bar())
        self.text_field = AYCommentField(
            self, text=self._data.comment, read_only=True
        )
        lyt.addWidget(self.text_field)

    def update_params(self, model: CommentModel):
        if self._data:
            self.user_icon.update_params(
                self._data.user_src, self._data.user_full_name
            )
            self.user_name.setText(self._data.user_name)
            self.date.setText(self._data.short_date)

    @staticmethod
    def parse(data: dict):
        """Take a comment payload, and return a CommentModel dataclass.

        Args:
            data (dict): JSON payload from the activity stream.

        Returns:
            CommentModel: Contains all required comment data.
        """
        full_name = (
            data.get("author", {}).get("attrib", {}).get("fullName", "Someone")
        )
        return CommentModel(
            user_full_name=full_name,
            user_name=full_name.split()[0],
            user_src="",
            comment=data.get("body", ""),
            comment_date=data.get("updatedAt", "not available"),
        )


class AYCommentEditor(AYFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._build()

    def _build_upper_bar(self):
        grp_spacing = 16
        lyt = AYHBoxLayout(self, spacing=0, margin=0)
        for icn in (
            "format_h1",
            "format_bold",
            "format_italic",
            "link",
            "code",
        ):
            lyt.addWidget(AYButton(self, variant="nav", icon=icn))
        # separator
        lyt.addSpacing(grp_spacing)
        for icn in (
            "format_list_numbered",
            "format_list_bulleted",
            "checklist",
        ):
            lyt.addWidget(AYButton(self, variant="nav", icon=icn))
        lyt.addSpacing(grp_spacing)
        lyt.addWidget(AYButton(self, variant="nav", icon="attach_file"))
        lyt.addSpacerItem(
            QtWidgets.QSpacerItem(
                0, 0, QtWidgets.QSizePolicy.Policy.MinimumExpanding
            )
        )
        return lyt

    def _build_edit_field(self):
        self.edit_field = AYCommentField(self)
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
        lyt = AYVBoxLayout(self)
        lyt.addLayout(self._build_upper_bar())
        lyt.addWidget(self._build_edit_field())
        lyt.addLayout(self._build_lower_bar())


if __name__ == "__main__":
    from ayon_ui_qt.tester import test

    def build():
        av1 = os.path.join(
            os.path.dirname(__file__), "resources", "avatar1.jpg"
        )
        av2 = os.path.join(
            os.path.dirname(__file__), "resources", "avatar2.jpg"
        )
        w = QtWidgets.QWidget()
        lyt = AYVBoxLayout(w, margin=8)
        lyt.addWidget(
            AYComment(
                user_src=av1,
                user_full_name="Bob Morane",
                comment="This is great !",
            )
        )
        lyt.addWidget(
            AYComment(
                user_src=av2,
                user_full_name="Leia Organa",
                comment="Can you avoid the dark side @Luke ?",
            )
        )
        lyt.addWidget(
            AYComment(
                user_full_name="Katniss Evergreen",
                comment="One squirrel...\nTwo squirrels\nThree squirrels...\n",
            )
        )
        lyt.addWidget(AYCommentEditor())
        return w

    test(build)

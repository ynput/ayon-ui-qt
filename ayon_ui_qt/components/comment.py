from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from qtpy.QtWidgets import QTextEdit

from .container import AYContainer, AYFrame
from .label import AYLabel
from .layouts import AYVBoxLayout
from .user_image import AYUserImage


def short_date(date_str: str) -> str:
    if date_str:
        try:
            # Parse the ISO string
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%b %d, %I:%M %p")
        except ValueError:
            # Handle invalid date format
            return date_str
    else:
        return "No date available"


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
        self._short_date = short_date(self.date)

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
        self._short_date = short_date(self.comment_date)

    @property
    def type(self):
        return "comment"

    @property
    def short_date(self):
        return self._short_date


class AYCommentField(QTextEdit):
    def __init__(self, *args, text="", read_only=False, num_lines=0, **kwargs):
        # remove our kwargs
        self._num_lines = num_lines
        self._text: str = text
        self._read_only: bool = read_only

        super().__init__(*args, **kwargs)
        self.setSizeAdjustPolicy(QTextEdit.SizeAdjustPolicy.AdjustToContents)
        self.setMarkdown(self._text)

        # configure
        int(self.fontMetrics().lineSpacing())

        if not self._read_only:
            self.setPlaceholderText(
                "Comment or mention with @user, @@version, @@@task..."
            )
        # self.setReadOnly(self._read_only)

    def _adjust(self, *args):
        print(f"adjust: {args}  {self.document().size()}")


class AYComment(AYFrame):
    def __init__(self, *args, data: CommentModel | None = None, **kwargs):
        self._data = data if data else CommentModel()

        super().__init__(*args, variant=AYFrame.Variant.Low, **kwargs)

        self._build()
        # configure
        if self._data:
            self.text_field.setMarkdown(self._data.comment)
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
        self.user_name = AYLabel(self._data.user_full_name, bold=True)
        self.date = AYLabel(self._data.short_date, dim=True, rel_text_size=-2)
        cntr = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYFrame.Variant.Low,
            layout_spacing=8,
        )
        cntr.addWidget(self.user_icon)
        cntr.addWidget(self.user_name)
        cntr.addStretch()
        cntr.addWidget(self.date)
        return cntr

    def _build(self):
        lyt = AYVBoxLayout(self, margin=0, spacing=0)
        lyt.addWidget(self._build_top_bar())
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


if __name__ == "__main__":
    from ..tester import Style, test
    from .container import AYContainer
    from .text_box import AYTextBox

    def build():
        rsrc_dir = Path(__file__).parent.parent / "resources"
        av1 = rsrc_dir / "avatar1.jpg"
        av2 = rsrc_dir / "avatar2.jpg"

        w = AYContainer(
            layout=AYContainer.Layout.VBox,
            # margin=8,
            layout_spacing=4,
            layout_margin=16,
            variant=AYFrame.Variant.Low,
        )

        w.addWidget(
            AYComment(
                data=CommentModel(
                    user_src=str(av1),
                    user_full_name="Bob Morane",
                    comment="This is great !",
                )
            )
        )
        w.addWidget(
            AYComment(
                data=CommentModel(
                    user_src=(str(av2)),
                    user_full_name="Leia Organa",
                    comment="Can you avoid the dark side @Luke ?",
                )
            )
        )
        w.addWidget(
            AYComment(
                data=CommentModel(
                    user_full_name="Katniss Evergreen",
                    comment="One squirrel...\nTwo squirrels\nThree squirrels !",
                )
            )
        )
        w.addWidget(AYTextBox(num_lines=3))
        return w

    test(build, style=Style.Widget)

from dataclasses import dataclass
from datetime import datetime


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


@dataclass
class StatusUiModel:
    text: str = ""
    short_text: str = ""
    icon: str = ""
    color: str = ""


@dataclass
class StatusChangeModel:
    user_full_name: str = ""
    user_name: str = ""
    user_src: str = ""
    product: str = ""
    version: str = ""
    old_status: str = ""
    new_status: str = ""
    date: str = ""

    def __post_init__(self):
        self._short_date = short_date(self.date)

    @property
    def type(self):
        return "status.change"

    @property
    def short_date(self):
        return self._short_date


@dataclass
class VersionPublishModel:
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
        return "version.publish"

    @property
    def short_date(self):
        return self._short_date


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

from dataclasses import dataclass, field
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
        return "Not available"


@dataclass
class StatusUiModel:
    text: str = ""
    short_text: str = ""
    icon: str = ""
    color: str = ""


@dataclass(unsafe_hash=True)
class StatusChangeModel:
    user_full_name: str = ""
    user_name: str = ""
    user_src: str = ""
    product: str = ""
    version: str = ""
    old_status: str = ""
    new_status: str = ""
    date: str = ""
    short_date: str = field(init=False, hash=False)
    type: str = field(init=False, default="status.change", hash=False)

    def __post_init__(self):
        self.short_date = short_date(self.date)


@dataclass(unsafe_hash=True)
class VersionPublishModel:
    user_full_name: str = ""
    user_name: str = ""
    user_src: str = ""
    version: str = ""
    product: str = ""
    date: str = ""
    short_date: str = field(init=False, hash=False)
    type: str = field(init=False, default="version.publish", hash=False)

    def __post_init__(self):
        self.short_date = short_date(self.date)


@dataclass(unsafe_hash=True)
class CommentModel:
    user_full_name: str = ""
    user_name: str = ""
    user_src: str = ""
    comment: str = ""
    comment_date: str = ""
    short_date: str = field(init=False, hash=False)
    type: str = field(init=False, default="comment", hash=False)

    def __post_init__(self):
        self.short_date = short_date(self.comment_date)


if __name__ == "__main__":
    # test objects are hashable
    c = CommentModel()
    print(f"c ={c}  hash(c) = {hash(c)}")
    v = VersionPublishModel()
    print(f"v ={v}  hash(v) = {hash(v)}")
    s = StatusChangeModel()
    print(f"s ={s}  hash(s) = {hash(s)}")

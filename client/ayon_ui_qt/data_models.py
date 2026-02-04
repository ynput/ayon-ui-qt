from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional


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


@dataclass
class TaskInfoModel:
    entity_name: str = ""
    entity_path: str = ""
    task_name: str = ""
    tags: list[str] = field(default_factory=list)
    assigned_user: str = ""
    priority: str = ""


@dataclass
class VersionInfoModel:
    version: str = ""
    status: str = ""
    thumbnail: str = ""


@dataclass(unsafe_hash=True)
class StatusChangeModel:
    activity_id: str = ""
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
    activity_id: str = ""
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


@dataclass
class AnnotationModel:
    id: str
    range: List[int]
    composite: str
    transparent: str


@dataclass
class FileModel:
    """Model for activity attached files.

    Attachments could be images, there could be also preview available for
    them.
    """
    id: str
    mime: str
    local_path: str = ""
    thumb_local_path: str = ""


@dataclass(unsafe_hash=True)
class CommentModel:
    activity_id: str = ""
    user_full_name: str = ""
    user_name: str = ""
    user_src: str = ""
    comment: str = ""
    category: str = ""
    category_color: str = ""
    comment_date: str = ""
    short_date: str = field(init=False, hash=False)
    type: str = field(init=False, default="comment", hash=False)
    files: list[FileModel] = field(default_factory=list, hash=False)
    annotations: list[AnnotationModel] = field(default_factory=list, hash=False)

    def __post_init__(self):
        """Set the date if not set and compute the short date."""
        if not self.comment_date:
            self.comment_date = datetime.now(timezone.utc).isoformat()

        self.short_date = short_date(self.comment_date)


# -----------------------------------------------------------------------------
# copies of ayon-review-desktop for local testing
# -----------------------------------------------------------------------------


@dataclass
class ActivityData:
    """Simple dataclass to cache representation data."""

    representation_id: str = ""
    hash: int = field(init=False)
    activity_list: list[
        CommentModel | VersionPublishModel | StatusChangeModel
    ] = field(default_factory=list)

    def __post_init__(self):
        """Compute the hash of the activity list."""
        self.hash = hash(tuple(self.activity_list))


@dataclass
class User:
    """Data model for user"""

    name: str
    short_name: str
    full_name: str
    email: str
    avatar_url: str = ""
    avatar_local_path: str = ""


@dataclass
class Team:
    name: str
    members: List[str]


@dataclass
class CommentCategory:
    """Model for powerpack `activity_categories` settings"""
    name: str
    color: str
    access: dict[str, Any]


@dataclass
class ProjectData:
    """Model to pass project data - anatomy, users, teams"""

    project_name: str
    users: List[User]
    teams: List[Team]
    anatomy: dict[str, Any]
    comment_category : List[CommentCategory]
    current_user: Optional[User]


    @staticmethod
    def not_set():
        ns = "PROJECT NOT SET"
        return ProjectData(
            project_name=ns,
            users=[],
            teams=[],
            anatomy={},
            comment_category=[],
            current_user=None
        )


@dataclass
class VersionData:
    """Model to pass enhanced version data"""

    id: str
    name: str
    author: str
    tags: list[str]
    status: str
    product_name: str
    task_name: str
    priority: str
    folder_path: str
    assignees: list[str]
    attrib: dict[str, str]
    thumbnail_id: str = ""
    thumbnail_local_path: str = ""

    @staticmethod
    def not_set():
        ns = "VERSION NOT SET"
        return VersionData(
            id=ns,
            name=ns,
            author=ns,
            tags=[],
            status=ns,
            product_name=ns,
            task_name=ns,
            priority=ns,
            folder_path=ns,
            assignees=[],
            attrib={},
            thumbnail_id=None,
            thumbnail_local_path=None
        )


if __name__ == "__main__":
    # test objects are hashable
    c = CommentModel()
    print(f"c ={c}  hash(c) = {hash(c)}")
    v = VersionPublishModel()
    print(f"v ={v}  hash(v) = {hash(v)}")
    s = StatusChangeModel()
    print(f"s ={s}  hash(s) = {hash(s)}")

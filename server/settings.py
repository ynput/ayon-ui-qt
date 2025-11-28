"""Settings model for UI Qt addon."""
from __future__ import annotations

from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class UIQtSettings(BaseSettingsModel):
    """Settings for AYON UI Qt addon.

    This library addon has minimal settings as most styling
    is defined in the ayon_style.json file.
    """

    enabled: bool = Field(
        default=True,
        title="Enabled",
        description="Enable the UI Qt component library",
    )

DEFAULT_UI_QT_VALUES = {
    "enabled": True,
}

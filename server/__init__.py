"""Server-side addon definition for AYON UI Qt.

This addon primarily provides client-side functionality (Qt widgets),
so server-side configuration is minimal.
"""
from __future__ import annotations

from typing import Any, Type

from ayon_server.addons import BaseServerAddon

from .settings import UIQtSettings, DEFAULT_UI_QT_VALUES


class UIQtAddon(BaseServerAddon):
    """Server-side addon for UI Qt library.

    This addon provides a library of Qt widgets styled to match
    AYON's frontend design system. Server-side functionality is
    limited to enabling/disabling the addon and optional theme
    customization.
    """

    name = "ui_qt"
    title = "AYON UI Qt"
    version = "0.1.0"

    settings_model: Type[UIQtSettings] = UIQtSettings

    async def get_default_settings(self) -> dict[str, Any]:
        """Return default addon settings.

        Returns:
            Default settings dictionary.
        """
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_UI_QT_VALUES)
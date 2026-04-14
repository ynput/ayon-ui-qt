"""AYON addon definition for UI Qt library.

This module provides the client-side addon integration with AYON.
"""
from __future__ import annotations

import os

from ayon_core.addon import AYONAddon

from .version import __version__


class UIQtAddon(AYONAddon):
    """Addon providing AYON-styled Qt widgets.

    This addon provides a library of Qt widgets that match AYON's
    frontend design system, enabling consistent UI across all
    AYON tools.
    """

    name = "ui_qt"
    title = "AYON UI Qt"
    version = __version__

    @classmethod
    def get_addon_dir(cls) -> str:
        """Return path to addon directory.

        Returns:
            Absolute path to addon directory.
        """
        return os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def get_resources_dir(cls) -> str:
        """Return path to resources directory.

        Returns:
            Absolute path to resources.
        """
        return os.path.join(cls.get_addon_dir(), "resources")
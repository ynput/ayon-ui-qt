"""AYON UI Qt - A Qt Widget library styled for AYON.

This module provides Qt widgets that match AYON's frontend design system,
enabling consistent UI across all AYON tools and applications."""

from .version import __version__

try:
    from .addon import UIQtAddon
except ImportError:
    # WE WANT TO BE ABLE TO TEST OUTSIDE THE LAUNCHER.
    pass


__all__ = [
    "__version__",
    "UIQtAddon",
]

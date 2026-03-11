"""Base class for visual widget tests."""

from __future__ import annotations

from abc import abstractmethod
from typing import Callable, Optional

from qtpy.QtWidgets import QWidget


class WidgetTest:
    """Base class for visual regression tests of AYON UI components.

    Subclass this in tests/components/test_*.py, implement build() and
    optionally steps(). The runner in test_visual.py discovers subclasses
    and drives the snapshot lifecycle.

    Class attributes:
        size: Widget dimensions (width, height) applied before first snapshot.
        tolerance: Per-pixel diff tolerance in the 0.0–1.0 range, passed to
            image_regression.check(diff_threshold=...).
    """

    size: tuple[int, int] = (800, 600)
    tolerance: float = 0.0

    def __init__(self) -> None:
        self.widget: Optional[QWidget] = None

    @abstractmethod
    def build(self) -> QWidget:
        """Build and return the widget under test.

        Called once per test run. Store any widgets you need to manipulate in
        steps as instance attributes here.
        """

    def steps(self) -> list[Callable[[], None]]:
        """Return ordered list of callables that mutate widget state.

        Each callable is invoked once and followed by a snapshot. Method names
        become part of the snapshot filename, so keep them descriptive.
        Default implementation returns an empty list (initial snapshot only).
        """
        return []

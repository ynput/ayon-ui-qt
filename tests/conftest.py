"""pytest configuration for visual regression tests.

Sets QT_QPA_PLATFORM=offscreen before any Qt import so tests run headless.
"""

import os

# Must be set before any Qt import. pytest-qt respects this too.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

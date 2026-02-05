"""Pre-launch hook for UI Qt addon."""

from __future__ import annotations
import os
from ayon_applications import PreLaunchHook
from ayon_ui_qt.addon import AYON_UI_QT_DIR


class PreGlobalsTools(PreLaunchHook):
    """Hook that runs before application launch.

    Attributes:
        order: Execution order (lower runs first, default is 0).
        app_groups: List of app groups to apply to, or {"*"} for all.
        hosts: List of host names to apply to, or {"*"} for all.
    """

    launch_types = set()

    def execute(self) -> None:
        """Execute the pre-launch hook.

        Access launch context via self.launch_context:
        - self.launch_context.env: Environment variables
        - self.launch_context.data: Launch data
        """
        module_dir = os.path.dirname(AYON_UI_QT_DIR)
        self.log.warning(f"Running AYON_UI_QT pre-launch hook: {module_dir}")

        # Set environment variable to find ayon_ui_qt addon.
        pypath = self.launch_context.env["PYTHONPATH"]
        if pypath:
            pypath = os.pathsep.join([str(module_dir), pypath])
        else:
            pypath = str(module_dir)
        self.launch_context.env["PYTHONPATH"] = pypath
        self.log.debug(f"Added ayon_ui_qt to PYTHONPATH: {module_dir}")

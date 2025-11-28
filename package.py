"""AYON UI Qt - Qt Widget library styled for AYON.

This addon provides a comprehensive library of Qt widgets that match
AYON's frontend design system, enabling consistent UI across all
AYON tools and applications.
"""

# Required: lower case addon name e.g. 'deadline', otherwise addon
#   will be invalid
name = "ui_qt"

# Optional: Addon title shown in UI, 'name' is used by default e.g. 'Deadline'
title = "UI Qt"

# Required: Valid semantic version (https://semver.org/)
version = "0.1.0-dev"

# Client directory containing the addon code
client_dir = "ayon_ui_qt"

# AYON server compatibility
ayon_server_version = ">=1.9.0"

# Version compatibility with AYON launcher
ayon_launcher_version = ">=1.3.0"

# Mapping of addon name to version requirements
# - addon with specified version range must exist to be able to use this addon
ayon_required_addons = {}

# Mapping of addon name to version requirements
# - if addon is used in same bundle the version range must be valid
ayon_compatible_addons = {}

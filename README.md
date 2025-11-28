# AYON UI Qt

A Qt Widget library addon for AYON that provides UI components matching AYON's frontend design system.

## Overview

This addon provides a comprehensive library of Qt widgets styled to match AYON's React-based frontend. It enables developers to create consistent, professional-looking UIs across all AYON tools and applications.

## Features

- **AYON-styled QStyle**: Custom `AYONStyle` class that provides consistent theming
- **Reusable Components**: Buttons, containers, labels, text boxes, combo boxes, and more
- **Variant Support**: Multiple style variants for each component (surface, tonal, filled, etc.)
- **Easy Integration**: Simple API to apply styling to widget trees

## Installation

### As an AYON Addon

1. Build the package:
   ```bash
   python create_package.py
   ```

2. Upload the generated `dist/ui_qt-{version}.zip` to your AYON server.

3. Enable the addon in AYON Studio Settings.

### For Development

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run tests:
   ```bash
   uv run pytest
   ```

## Usage

### Basic Usage

```python
from ayon_ui_qt import get_ayon_style, style_widget_and_siblings
from ayon_ui_qt.components import AYButton, AYContainer, AYLabel

# Create a styled container with buttons
container = AYContainer(
    layout=AYContainer.Layout.VBox,
    variant="low",
    layout_margin=10,
    layout_spacing=8,
)

# Add styled widgets
button = AYButton("Click me", variant="filled")
container.add_widget(button)

label = AYLabel("Status", icon="check_circle", icon_color="#00ff00")
container.add_widget(label)

# Apply AYON styling to widget tree
style_widget_and_siblings(container)
```

### Button Variants

```python
from ayon_ui_qt.components import AYButton

# Available variants: surface, tonal, filled, tertiary, text, nav, nav-small, danger
AYButton("Surface", variant="surface")
AYButton("Filled", variant="filled")
AYButton("Danger", variant="danger", icon="delete")
```

### Container Layouts

```python
from ayon_ui_qt.components import AYContainer

# Horizontal layout
h_container = AYContainer(layout=AYContainer.Layout.HBox)

# Vertical layout
v_container = AYContainer(layout=AYContainer.Layout.VBox)

# Grid layout
grid_container = AYContainer(layout=AYContainer.Layout.Grid)
```

## Project Structure

```
ayon-ui-qt/
├── client/
│   └── ayon_ui_qt/          # Client-side addon code
│       ├── __init__.py      # Main module exports
│       ├── addon.py         # AYON addon integration
│       ├── version.py       # Version info
│       ├── ayon_style.py    # Custom QStyle implementation
│       ├── ayon_style.json  # Style definitions
│       ├── components/      # UI components
│       ├── resources/       # Assets and test data
│       └── vendor/          # Vendored dependencies
├── server/
│   ├── __init__.py          # Server-side addon
│   └── settings.py          # Server settings
├── package.py               # AYON package definition
├── version.py               # Root version
├── create_package.py        # Build script
├── pyproject.toml           # Python package config
└── README.md
```

## Available Components

| Component | Description |
|-----------|-------------|
| `AYButton` | Styled push button with variants |
| `AYContainer` | Layout container (HBox, VBox, Grid) |
| `AYFrame` | Styled frame widget |
| `AYLabel` | Label with icon support |
| `AYTextBox` | Rich text editor with markdown |
| `AYComboBox` | Styled combo box |
| `AYUserImage` | User avatar display |
| `AYComment` | Comment display widget |
| `AYEntityPath` | Entity path breadcrumb |
| `AYEntityThumbnail` | Entity thumbnail button |

## Development

### Running Tests

```bash
# Run individual component tests
uv run python -m ayon_ui_qt.components.buttons
uv run python -m ayon_ui_qt.ayon_style
```

### Building the Package

```bash
python create_package.py
```

The package will be created at `dist/ui_qt-{version}.zip`.

## License

Apache-2.0

## Contributing

Contributions are welcome! Please follow the coding standards defined in the project's `.kilocode/rules/coding_standards.md`.

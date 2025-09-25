#!/usr/bin/env python3
"""
CSS to QSS Converter Script

This script converts serialized CSSStyleDeclaration from JSON files to Qt QSS
stylesheet format. It processes JSON files from 'ayon_ui_qt/web_styles' directory
and generates corresponding QSS styles.

Usage:
    uv run css_to_qss_converter.py
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXTRA_RULES = [
    """
    QScrollBar:vertical {
        border: 0px none;
        width: 10px;
        background: none;
    }
    QScrollBar::handle:vertical {
        border: 0px solid;
        border-radius: 5px;
        background: rgb(68, 74, 85);

    }
    QScrollBar:horizontal {
        border: 0px none;
        width: 10px;
        background: none;
    }
    QScrollBar::handle:horizontal {
        border: 0px solid;
        border-radius: 5px;
        background: rgb(68, 74, 85);

    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: rgb(39, 45, 53);
    }
    """
]


class CSSToQSSConverter:
    """Converts CSS properties to Qt QSS format."""

    # CSS state mapping to QSS pseudo-states
    CSS_STATE_TO_QSS_PSEUDO = {
        "hover": ":hover",
        "active": ":pressed",  # Qt uses :pressed for active state
        "focus": ":focus",
        "disabled": ":disabled",
    }

    # CSS property mapping to QSS properties
    CSS_TO_QSS_MAPPING = {
        # Background properties
        "backgroundColor": "background-color",
        "background-color": "background-color",  # Handle both camelCase and kebab-case
        "backgroundImage": "background-image",
        "background-image": "background-image",
        # Color properties
        "color": "color",
        # Border properties
        "borderRadius": "border-radius",
        "borderWidth": "border-width",
        "borderStyle": "border-style",
        "borderColor": "border-color",
        "borderTopWidth": "border-top-width",
        "borderRightWidth": "border-right-width",
        "borderBottomWidth": "border-bottom-width",
        "borderLeftWidth": "border-left-width",
        "borderTopStyle": "border-top-style",
        "borderRightStyle": "border-right-style",
        "borderBottomStyle": "border-bottom-style",
        "borderLeftStyle": "border-left-style",
        "borderTopColor": "border-top-color",
        "borderRightColor": "border-right-color",
        "borderBottomColor": "border-bottom-color",
        "borderLeftColor": "border-left-color",
        "borderTopLeftRadius": "border-top-left-radius",
        "borderTopRightRadius": "border-top-right-radius",
        "borderBottomLeftRadius": "border-bottom-left-radius",
        "borderBottomRightRadius": "border-bottom-right-radius",
        # Padding and margin
        "padding": "padding",
        "paddingTop": "padding-top",
        "paddingRight": "padding-right",
        "paddingBottom": "padding-bottom",
        "paddingLeft": "padding-left",
        "margin": "margin",
        "marginTop": "margin-top",
        "marginRight": "margin-right",
        "marginBottom": "margin-bottom",
        "marginLeft": "margin-left",
        # Font properties
        "font": "font",  # Font shorthand - will be parsed into individual properties
        "fontFamily": "font-family",
        "fontSize": "font-size",
        "fontWeight": "font-weight",
        "fontStyle": "font-style",
        "lineHeight": "line-height",
        "letterSpacing": "letter-spacing",
        # Text properties
        "textAlign": "text-align",
        "textDecoration": "text-decoration",
        "textTransform": "text-transform",
        # Size properties (map to min-size for buttons)
        # "width": "min-width",
        # "height": "min-height",
        # Other properties
        "opacity": "opacity",
        "outline": "outline",
        "outlineColor": "outline-color",
        "outlineWidth": "outline-width",
        "outlineStyle": "outline-style",
    }

    def __init__(self):
        """Initialize the converter."""
        self.output_dir = Path("ayon_ui_qt") / "output"
        self.output_dir.mkdir(exist_ok=True)

    def convert_color(self, color_value: str) -> str:
        """
        Convert CSS color formats to Qt-compatible format.

        Args:
            color_value: CSS color value (rgb(), rgba(), hex, etc.)

        Returns:
            Qt-compatible color string
        """
        if not color_value or color_value in ("auto", "none", "transparent"):
            return color_value

        # Handle rgb() format
        rgb_match = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", color_value)
        if rgb_match:
            r, g, b = rgb_match.groups()
            return f"rgb({r}, {g}, {b})"

        # Handle rgba() format
        rgba_match = re.match(
            r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", color_value
        )
        if rgba_match:
            r, g, b, a = rgba_match.groups()
            alpha = float(a)
            if alpha == 0:
                return "transparent"
            elif alpha == 1:
                return f"rgb({r}, {g}, {b})"
            else:
                # # Convert to hex with alpha
                # alpha_hex = format(int(alpha * 255), "02x")
                # r_hex = format(int(r), "02x")
                # g_hex = format(int(g), "02x")
                # b_hex = format(int(b), "02x")
                # return f"#{r_hex}{g_hex}{b_hex}{alpha_hex}"
                return color_value

        # Return as-is for hex colors and named colors
        return color_value

    def should_include_property(self, prop: str, value: str) -> bool:
        """
        Determine if a CSS property should be included in QSS output.

        Args:
            prop: CSS property name
            value: CSS property value

        Returns:
            True if property should be included
        """
        # Skip properties with default/empty values
        if not value or value in (
            "auto",
            "none",
            "normal",
            "0px",
            "0",
            "initial",
        ):
            return False

        # Skip webkit-specific properties
        if prop.startswith("webkit"):
            return False

        # Skip properties not in our mapping
        if prop not in self.CSS_TO_QSS_MAPPING:
            return False

        if any([re.match(r, prop) for r in self.ignore_props]):
            return False

        # Include properties with meaningful values
        return True

    def clean_font_family(self, font_family: str) -> str:
        """
        Clean font family string for QSS.

        Args:
            font_family: CSS font-family value

        Returns:
            Cleaned font family string
        """
        # Handle font family lists (e.g., "Nunito Sans", sans-serif)
        # If it contains a comma, it's likely a font family list
        if "," in font_family:
            # Don't add extra quotes around font family lists
            # Just clean up any extra outer quotes if they wrap the entire list
            cleaned = font_family.strip()
            # Remove outer quotes that wrap the entire font family list
            if (cleaned.startswith('"') and cleaned.endswith('"')) or (
                cleaned.startswith("'") and cleaned.endswith("'")
            ):
                cleaned = cleaned[1:-1]
            return cleaned

        # For single font families, apply the original logic
        cleaned = font_family.strip("\"'")

        # If it contains spaces, wrap in quotes
        if " " in cleaned and not (
            cleaned.startswith('"') and cleaned.endswith('"')
        ):
            return f'"{cleaned}"'

        return cleaned

    def parse_font_shorthand(self, font_value: str) -> Dict[str, str]:
        """
        Parse CSS font shorthand into individual font properties.

        CSS font syntax: [font-style] [font-variant] [font-weight] font-size [/line-height] font-family
        Example: "14px / 20px \"Nunito Sans\", sans-serif"

        Args:
            font_value: CSS font shorthand value

        Returns:
            Dictionary of individual font properties
        """
        if not font_value or font_value.strip() in ("auto", "none", "normal"):
            return {}

        # Parse font shorthand using regex
        # Handle patterns like: [font-weight] font-size [/ line-height] font-family
        # Examples: "14px / 20px \"Nunito Sans\"" or "500 14px / 20px \"Nunito Sans\""

        # Try pattern with optional font-weight first
        pattern_with_weight = r"(?:(\w+|\d+)\s+)?(\d+(?:\.\d+)?(?:px|em|rem|%|pt))\s*(?:/\s*(\d+(?:\.\d+)?(?:px|em|rem|%|pt)))?\s+(.+)"

        match = re.match(pattern_with_weight, font_value.strip())
        if not match:
            logger.warning(f"Could not parse font shorthand: {font_value}")
            return {}

        font_weight, font_size, line_height, font_family = match.groups()

        properties = {}

        # Font weight (optional)
        if font_weight:
            properties["fontWeight"] = font_weight

        # Font size (required)
        if font_size:
            properties["fontSize"] = font_size

        # Line height (optional)
        if line_height:
            properties["lineHeight"] = line_height

        # Font family (required)
        if font_family:
            # Clean up font family - remove extra whitespace and ensure proper quoting
            font_family = font_family.strip()
            properties["fontFamily"] = font_family

        logger.debug(
            f"Parsed font shorthand '{font_value}' into: {properties}"
        )
        return properties

    def convert_css_properties(
        self, css_style: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Convert CSS properties to QSS properties.

        Args:
            css_style: Dictionary of CSS properties

        Returns:
            Dictionary of QSS properties
        """
        qss_properties = {}

        for css_prop, css_value in css_style.items():
            if not isinstance(css_value, str):
                continue

            if not self.should_include_property(css_prop, css_value):
                continue

            qss_prop = self.CSS_TO_QSS_MAPPING.get(css_prop)
            if not qss_prop:
                continue

            # First flag CSS custom properties
            if re.search(r"--\w+-", css_value):
                raise ValueError("Unresolved variable: %s", css_value)

            # Special handling for font shorthand
            if css_prop == "font":
                # Parse font shorthand into individual properties
                font_props = self.parse_font_shorthand(css_value)
                for font_prop, font_val in font_props.items():
                    if font_prop in self.CSS_TO_QSS_MAPPING:
                        qss_font_prop = self.CSS_TO_QSS_MAPPING[font_prop]
                        if font_prop == "fontFamily":
                            processed_val = self.clean_font_family(font_val)
                        else:
                            processed_val = font_val
                        if processed_val and processed_val not in (
                            "auto",
                            "none",
                            "normal",
                        ):
                            qss_properties[qss_font_prop] = (
                                processed_val.rstrip(";")
                            )
                continue

            # Special handling for different property types
            if "color" in qss_prop.lower() or css_prop in ["backgroundColor"]:
                qss_value = self.convert_color(css_value)
            elif css_prop == "fontFamily":
                qss_value = self.clean_font_family(css_value)
            else:
                qss_value = css_value

            # Skip if conversion resulted in empty value
            if qss_value and qss_value not in ("auto", "none", "normal"):
                # Remove any trailing semicolons from the value
                qss_value = qss_value.rstrip(";")
                qss_properties[qss_prop] = qss_value

        return self._optimize_properties(qss_properties)

    def _optimize_properties(
        self, properties: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Optimize QSS properties by removing redundancies and invalid combinations.

        Args:
            properties: Dictionary of QSS properties

        Returns:
            Optimized dictionary of QSS properties
        """
        optimized = properties.copy()

        # Remove individual padding properties if shorthand exists
        if "padding" in optimized:
            for prop in [
                "padding-top",
                "padding-right",
                "padding-bottom",
                "padding-left",
            ]:
                optimized.pop(prop, None)

        # Remove individual margin properties if shorthand exists
        if "margin" in optimized:
            for prop in [
                "margin-top",
                "margin-right",
                "margin-bottom",
                "margin-left",
            ]:
                optimized.pop(prop, None)

        # Remove individual border properties if shorthand exists
        sides = (
            "-top",
            "-right",
            "-bottom",
            "-left",
            "-top-left",
            "-top-right",
            "-bottom-left",
            "-bottom-right",
        )
        parts = ("", "-width", "-color", "-style", "-radius")
        for p in parts:
            if f"border{p}" in optimized:
                for side in sides:
                    optimized.pop(f"border{side}{p}", None)

        # Remove text-decoration if it's just a color (not meaningful in QSS)
        if "text-decoration" in optimized:
            value = optimized["text-decoration"]
            if (
                value.startswith("rgb(")
                or value.startswith("#")
                or value == "transparent"
            ):
                optimized.pop("text-decoration", None)

        # Remove outline if it's redundant with outline-color and outline-style
        if (
            all(
                prop in optimized
                for prop in ["outline-color", "outline-style"]
            )
            and "outline" in optimized
        ):
            outline_value = optimized["outline"]
            if "none" in outline_value:
                optimized.pop("outline", None)

        # Remove opacity if it's 1 (default)
        if optimized.get("opacity") == "1":
            optimized.pop("opacity", None)

        return optimized

    def generate_compound_qss_selector(
        self,
        widget_class: str,
        selector_parts: List[Tuple[str, str]],
        pseudo_state: Optional[str] = None,
    ) -> str:
        """
        Generate compound QSS selector from Qt widget class and multiple attribute selectors.

        Args:
            widget_class: Qt widget class name (e.g., 'QPushButton')
            selector_parts: List of (name, value) tuples for attribute selectors
            pseudo_state: Qt pseudo-state (e.g., ':hover', ':pressed')

        Returns:
            Compound QSS selector string
        """
        base_selector = widget_class

        # Add attribute selectors
        for name, value in selector_parts:
            if name and value:
                base_selector += f'[{name}="{value}"]'

        if pseudo_state:
            base_selector = f"{base_selector}{pseudo_state}"

        return base_selector

    def generate_qss_selector(
        self,
        widget_class: str,
        name: str,
        value: str,
        pseudo_state: Optional[str] = None,
    ) -> str:
        """
        Generate QSS selector from Qt widget class, variant, and optional pseudo-state.

        Args:
            widget_class: Qt widget class name (e.g., 'QPushButton')
            variant: Widget variant name (e.g., 'danger')
            pseudo_state: Qt pseudo-state (e.g., ':hover', ':pressed')

        Returns:
            QSS selector string
        """
        base_selector = widget_class
        if name and value:
            base_selector = f'{widget_class}[{name}="{value}"]'

        if pseudo_state:
            base_selector = f"{base_selector}{pseudo_state}"

        return base_selector

    def format_qss_rule(
        self, selector: str, properties: Dict[str, str]
    ) -> str:
        """
        Format QSS rule with selector and properties.

        Args:
            selector: QSS selector string
            properties: Dictionary of QSS properties

        Returns:
            Formatted QSS rule string
        """
        if not properties:
            return ""

        lines = [f"{selector} {{"]

        # Define property order for better readability
        property_order = [
            # Background and colors first
            "background-color",
            "color",
            # Size properties
            # "min-width",
            # "min-height",
            "width",
            "height",
            # Spacing
            "margin",
            "margin-top",
            "margin-right",
            "margin-bottom",
            "margin-left",
            "padding",
            "padding-top",
            "padding-right",
            "padding-bottom",
            "padding-left",
            # Border properties
            "border",
            "border-width",
            "border-style",
            "border-color",
            "border-radius",
            "border-top-width",
            "border-right-width",
            "border-bottom-width",
            "border-left-width",
            "border-top-style",
            "border-right-style",
            "border-bottom-style",
            "border-left-style",
            "border-top-color",
            "border-right-color",
            "border-bottom-color",
            "border-left-color",
            "border-top-left-radius",
            "border-top-right-radius",
            "border-bottom-left-radius",
            "border-bottom-right-radius",
            # Font properties
            "font-family",
            "font-size",
            "font-weight",
            "font-style",
            "line-height",
            "letter-spacing",
            # Text properties
            "text-align",
            "text-decoration",
            "text-transform",
            # Other properties
            "opacity",
            "outline",
            "outline-color",
            "outline-width",
            "outline-style",
        ]

        # Add properties in preferred order
        added_props = set()
        for prop in property_order:
            if prop in properties:
                value = properties[prop]
                lines.append(f"    {prop}: {value};")
                added_props.add(prop)

        # Add any remaining properties alphabetically
        remaining_props = sorted(set(properties.keys()) - added_props)
        for prop in remaining_props:
            value = properties[prop]
            lines.append(f"    {prop}: {value};")

        lines.append("}")
        lines.append("")  # Empty line after each rule

        return "\n".join(lines)

    def process_selectors_recursively(
        self,
        widget_class: str,
        selectors: Dict[str, Any],
        states: Dict[str, Any],
        parent_selector_parts: Optional[List[Tuple[str, str]]] = None,
        parent_css_properties: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """
        Recursively process nested selectors and merge CSS properties.

        Args:
            widget_class: Qt widget class name
            selectors: Selector dictionary to process
            states: CSS states dictionary
            parent_selector_parts: List of (name, value) tuples from parent selectors
            parent_css_properties: Inherited CSS properties from parent

        Returns:
            Tuple of (all_rules, tweaks) dictionaries
        """
        if parent_selector_parts is None:
            parent_selector_parts = []
        if parent_css_properties is None:
            parent_css_properties = {}

        all_rules = {}
        tweaks = {}

        for name, sel in selectors.items():
            current_selector_parts = parent_selector_parts.copy()
            value = sel.get("value")

            # Add current selector part
            if name and value:
                current_selector_parts.append((name, value))

            # Get current CSS properties and merge with parent
            css_style = sel.get("CSSStyleDeclaration", {})
            merged_css_properties = parent_css_properties.copy()
            if css_style:
                # Convert and merge properties (child properties override parent)
                current_qss_properties = self.convert_css_properties(css_style)
                merged_css_properties.update(current_qss_properties)

            # Only generate rule if we have CSS properties
            if merged_css_properties:
                # Generate compound selector
                selector = self.generate_compound_qss_selector(
                    widget_class, current_selector_parts
                )
                tweaks[selector] = sel.get("qss tweak", [])
                qss_rule = self.format_qss_rule(
                    selector, merged_css_properties
                )
                all_rules[selector] = qss_rule

                # Process state-specific styles if not disabled
                if states and not sel.get("no states", False):
                    for css_state, state_styles in states.items():
                        if css_state in self.CSS_STATE_TO_QSS_PSEUDO:
                            state_qss_properties = self.convert_css_properties(
                                state_styles
                            )
                            if state_qss_properties:
                                pseudo_state = self.CSS_STATE_TO_QSS_PSEUDO[
                                    css_state
                                ]
                                state_selector = (
                                    self.generate_compound_qss_selector(
                                        widget_class,
                                        current_selector_parts,
                                        pseudo_state,
                                    )
                                )
                                state_qss_rule = self.format_qss_rule(
                                    state_selector, state_qss_properties
                                )
                                all_rules[state_selector] = state_qss_rule

            # Process nested selectors if they exist
            nested_selectors = sel.get("selector", {})
            if nested_selectors:
                nested_rules, nested_tweaks = (
                    self.process_selectors_recursively(
                        widget_class,
                        nested_selectors,
                        states,
                        current_selector_parts,
                        merged_css_properties,
                    )
                )
                all_rules.update(nested_rules)
                tweaks.update(nested_tweaks)

        return all_rules, tweaks

    def process_json_file(self, json_file: Path) -> Optional[str]:
        """
        Process a single JSON file and convert to QSS.

        Args:
            json_file: Path to JSON file

        Returns:
            QSS string or None if processing failed
        """
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            widget_class = data.get("Qt Widget", "QWidget")
            selectors = data.get("selector", {})
            states = data.get("states", {})
            self.ignore_props = data.get("ignore props", [])

            if not selectors and not states:
                logger.warning(f"No selectors or states found in {json_file}")
                return None

            # Use recursive processing for nested selectors
            all_rules, tweaks = self.process_selectors_recursively(
                widget_class, selectors, states
            )

            # Process tweaks
            for selector_name, qss in tweaks.items():
                if not qss:
                    continue
                buf: list = str(all_rules[selector_name]).splitlines()
                last = buf.index("}")
                for line in qss:
                    if "{" in line:
                        find_sel_prop = re.search(
                            r"([\w\d\-]+):\s*\{([^\.]+)\.([\w-]+)\}", line
                        )
                        if find_sel_prop:
                            prop = find_sel_prop.group(1)
                            src_sel = find_sel_prop.group(2)
                            src_prop = find_sel_prop.group(3)
                            src_buf = all_rules[src_sel]
                            find_val = re.search(
                                f"\s({src_prop}):\s*([^;]+)", src_buf
                            )
                            if find_val:
                                val = self.convert_color(find_val.group(2))
                                logger.info(
                                    f"  >>  {selector_name} find_val of {line!r}: {find_val.groups()} = {val}"
                                )
                                buf.insert(last, f"    {prop}: {val};")
                    else:
                        buf.insert(last, f"    {line.strip()}")
                all_rules[selector_name] = "\n".join(buf)

            all_rules_list = [s for s in all_rules.values()]

            if not all_rules_list:
                logger.warning(
                    f"No valid QSS rules generated from {json_file}"
                )
                return None

            total_rules = len(all_rules_list)
            logger.info(
                f"Processed {json_file.name}: {total_rules} rule(s) generated"
            )
            return "\n".join(all_rules_list)

        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            return None

    def process_directory(self, input_dir: str) -> None:
        """
        Process all JSON files in the input directory.

        Args:
            input_dir: Directory containing JSON files
        """
        input_path = Path(input_dir)

        if not input_path.exists():
            logger.error(f"Input directory does not exist: {input_path}")
            return

        json_files = list(input_path.glob("*.json"))

        if not json_files:
            logger.warning(f"No JSON files found in {input_path}")
            return

        logger.info(f"Found {len(json_files)} JSON files to process")

        all_qss_rules = []
        individual_files = []

        for json_file in sorted(json_files):
            qss_rule = self.process_json_file(json_file)
            if qss_rule:
                all_qss_rules.append(qss_rule)

                # Save individual QSS file
                qss_filename = json_file.stem.replace("_css", ".qss")
                qss_file_path = self.output_dir / qss_filename

                with open(qss_file_path, "w", encoding="utf-8") as f:
                    f.write(f"/* Generated from {json_file.name} */\n\n")
                    f.write(qss_rule)

                individual_files.append(qss_file_path)
                logger.info(f"Created individual QSS file: {qss_file_path}")

        all_qss_rules += EXTRA_RULES

        # Create comprehensive QSS file
        if all_qss_rules:
            comprehensive_file = self.output_dir / "complete_styles.qss"
            with open(comprehensive_file, "w", encoding="utf-8") as f:
                f.write(
                    "/* Complete QSS styles generated from CSS JSON files */\n"
                )
                f.write("/* This file contains all converted styles */\n\n")
                f.write("\n".join(all_qss_rules))

            logger.info(
                f"Created comprehensive QSS file: {comprehensive_file}"
            )
            logger.info(
                f"Created {len(individual_files)} individual QSS files"
            )
            logger.info(f"Total QSS rules generated: {len(all_qss_rules)}")


def main() -> None:
    """Main function to run the converter."""
    converter = CSSToQSSConverter()

    # Process JSON files from ayon_ui_qt/web_styles directory
    input_directory = "ayon_ui_qt/web_styles"

    logger.info("Starting CSS to QSS conversion...")
    converter.process_directory(input_directory)
    logger.info("Conversion completed!")


if __name__ == "__main__":
    main()

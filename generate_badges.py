import json
import base64
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, TypedDict


class BadgeConfig(TypedDict, total=False):
    name: str
    color: str
    logo_color: str
    url: str
    label: str  # Optional override for left-hand text
    label_color: str  # Optional background color for left part


import requests


def shorten_url(long_url: str, use_tinyurl: bool = True) -> str:
    """Shorten a URL using TinyURL's API

    Args:
        long_url: The URL to shorten
        use_tinyurl: If True, use TinyURL API to shorten URL. If False, return original URL.
    """
    if not use_tinyurl:
        return long_url

    try:
        response = requests.get(f"http://tinyurl.com/api-create.php?url={long_url}")
        if response.status_code == 200:
            return response.text.strip()
        return long_url  # Return original if shortening fails
    except Exception as e:
        print(f"Warning: URL shortening failed - {e}")
        return long_url


# Load badge configurations from JSON file
def load_badge_configs() -> Dict[str, BadgeConfig]:
    """Load badge configurations from JSONC file"""
    config_path = Path("badge_configs.jsonc")
    if not config_path.exists():
        raise FileNotFoundError("badge_configs.jsonc not found")

    # Read file and remove comments
    with open(config_path, "r") as f:
        content = f.read()

    # Remove single-line comments
    import re

    content = re.sub(r"^\s*//.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"//.*$", "", content)

    # Parse JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        raise


# Load configurations
BADGE_CONFIGS = load_badge_configs()


def convert_svg_fills(svg_content: str, color: str) -> str:
    """Convert all fill colors in SVG to specified color, including implicit fills"""
    try:
        root = ET.fromstring(svg_content)

        # Find all path and other shape elements
        for elem in root.iter():
            # Add fill color to elements without fill that can be filled
            if elem.tag.endswith(("path", "circle", "rect", "polygon", "ellipse")):
                # Only add fill if it's not explicitly set to "none"
                if "fill" not in elem.attrib or elem.attrib["fill"] != "none":
                    elem.attrib["fill"] = color
            # Update existing fill colors
            elif "fill" in elem.attrib and elem.attrib["fill"] != "none":
                elem.attrib["fill"] = color

        return ET.tostring(root, encoding="unicode")
    except ET.ParseError:
        print(f"Warning: Could not parse SVG - returning original content")
        return svg_content


def generate_badge_definition(
    name: str, config: BadgeConfig, base64_content: str = None
) -> str:
    """Generate essential badge definition"""
    badge_name = name.lower()

    # Standard logo or base64 SVG
    logo = (
        f"data:image/svg+xml;base64,{base64_content}" if base64_content else badge_name
    )

    # Get colors from config
    color = config["color"].strip("#")
    logo_color = config.get("logo_color", "#000000").strip("#")

    # Build query parameters
    params = ["style=for-the-badge", f"logo={logo}", f"logoColor={logo_color}"]

    # Add optional parameters if specified
    if "label" in config:
        params.append(f'label={config["label"].replace(" ", "_")}')
    if "label_color" in config:
        params.append(f'labelColor={config["label_color"].strip("#")}')

    # Join parameters with &
    query_string = "&".join(params)

    output = [f"[//]: # \"{config['name']} Colors\""]

    # Show color definitions
    output.append(f"[{badge_name}-badge-color]: {config.get('color', 'none')}")
    output.append(f"[{badge_name}-logo_color]: {config.get('logo_color', 'none')}")
    output.append(f"[{badge_name}-label_color]: {config.get('label_color', 'none')}")

    output.append(f"\n[//]: # \"{config['name']} Badge Definition\"")

    # Include badge URL and badge image
    output.append(f"[{badge_name}-url]: {config['url']}")
    output.append(
        f"[{badge_name}-badge]: https://img.shields.io/badge/{config['name']}-{color}?{query_string}"
    )

    return "\n".join(output) + "\n\n"


def process_icons(use_tinyurl: bool = True):
    """Process SVGs and generate badge definitions

    Args:
        use_tinyurl: If True, use TinyURL API to shorten badge URLs
    """

    # Setup directories and clear existing files
    icon_dir = Path("assets/icons")
    base64_dir = Path("assets/base64")
    base64_dir.mkdir(exist_ok=True)

    for old_file in base64_dir.glob("*.b64"):
        old_file.unlink()
        print(f"Removed old file: {old_file}")

    # Track processed badges and store definitions
    processed_badges = set()
    color_definitions = []
    badge_definitions = []
    base64_contents = {}

    # Process SVG icons first to get base64 contents
    if icon_dir.exists():
        svg_files = list(icon_dir.glob("*.svg"))
        print(f"\nFound {len(svg_files)} SVG files to process")

        for svg_path in svg_files:
            name = svg_path.stem
            if name not in BADGE_CONFIGS:
                print(f"Warning: No config found for {name}")
                continue

            print(f"\nProcessing {svg_path.name}...")

            # Read and process SVG
            with open(svg_path, "r") as f:
                svg_content = f.read()

            config = BADGE_CONFIGS[name]

            # Convert colors if specified
            if "logo_color" in config:
                modified_svg = convert_svg_fills(svg_content, config["logo_color"])
                suffix = config["logo_color"].strip("#")
            else:
                modified_svg = svg_content
                suffix = "original"

            # Store base64 content
            base64_str = base64.b64encode(modified_svg.encode()).decode()
            base64_contents[name] = base64_str

            # Save to file
            output_path = base64_dir / f"{name}_{suffix}.b64"
            with open(output_path, "w") as f:
                f.write(base64_str)
            print(f"✓ Generated {output_path}")

            processed_badges.add(name)

    # Generate all color definitions first
    for name, config in BADGE_CONFIGS.items():
        color_def = [f"[//]: # \"{config['name']} Colors\""]
        color_def.append(f"[{name}-badge-color]: {config.get('color', 'none')}")
        color_def.append(f"[{name}-logo_color]: {config.get('logo_color', 'none')}")
        color_def.append(f"[{name}-label_color]: {config.get('label_color', 'none')}\n")
        color_definitions.append("\n".join(color_def))

    # Then generate all badge definitions
    for name, config in BADGE_CONFIGS.items():
        badge_def = [f"[//]: # \"{config['name']} Badge Definition\""]
        badge_def.append(f"[{name}-url]: {config['url']}")

        # Build badge URL
        color = config["color"].strip("#")
        logo_color = config.get("logo_color", "#000000").strip("#")
        base64_content = base64_contents.get(name)

        logo = f"data:image/svg+xml;base64,{base64_content}" if base64_content else name

        params = ["style=for-the-badge", f"logo={logo}", f"logoColor={logo_color}"]

        if "label" in config:
            params.append(f'label={config["label"].replace(" ", "_")}')
        if "label_color" in config:
            params.append(f'labelColor={config["label_color"].strip("#")}')

        query_string = "&".join(params)
        long_url = (
            f"https://img.shields.io/badge/{config['name']}-{color}?{query_string}"
        )

        # Shorten the URL only if use_tinyurl is True
        badge_url = shorten_url(long_url, use_tinyurl)
        badge_def.append(f"[{name}-badge]: {badge_url}\n")
        badge_definitions.append("\n".join(badge_def))

    # Write the complete badges.md file
    with open("badges.md", "w") as f:
        f.write('[//]: # "Generated Badge Definitions"\n\n')
        f.write("".join(color_definitions))
        f.write("".join(badge_definitions))

        all_badges = []

        # Add usage examples
        f.write("# Usage Examples:\n")
        for name in BADGE_CONFIGS:
            f.write(f"## {BADGE_CONFIGS[name]['name'].replace('_', ' ')}\n")
            f.write(f"[![{name}][{name}-badge]][{name}-url]\n\n")
            all_badges.append(f"[![{name}][{name}-badge]][{name}-url]")

        # Add all badges section
        f.write("# All\n")
        f.write("\n".join(all_badges) + "\n\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate badge definitions")
    parser.add_argument(
        "--no-tinyurl",
        action="store_true",
        help="Do not use TinyURL API to shorten URLs",
    )

    args = parser.parse_args()

    process_icons(use_tinyurl=not args.no_tinyurl)
    print("\nDone! Badge definitions generated in badges.md")

import json
import base64
import os
import re
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
    # Get absolute path of script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "badge_configs.jsonc")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"badge_configs.jsonc not found at {config_path}")
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
    # Track statistics
    stats = {
        "new_svg": 0,
        "unchanged_svg": 0,
        "reused_url": 0,
        "new_url": 0,
        "simple_badge": 0,
        "warnings": 0,
    }

    # Resolve paths
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    base64_dir = script_dir / "base64"
    output_file = script_dir / "badges.md"

    # First read existing badge definitions to extract current TinyURLs
    existing_tinyurls = {}
    if output_file.exists():
        with open(output_file) as f:
            content = f.read()
            # Find all badge definitions using regex
            badge_defs = re.findall(
                r"\[(\w+)-badge\]: (https://tinyurl\.com/\w+)", content
            )
            existing_tinyurls = dict(badge_defs)

    base64_dir.mkdir(exist_ok=True)
    processed_badges = set()
    color_definitions = []
    badge_definitions = []
    base64_contents = {}

    # Read existing base64 files to compare content
    existing_base64 = {}
    for b64_file in base64_dir.glob("*.b64"):
        name = b64_file.stem.rsplit("_", 1)[0]
        with open(b64_file) as f:
            existing_base64[name] = f.read().strip()

    # Process SVG files
    if (script_dir / "icons").exists():
        svg_files = list((script_dir / "icons").glob("*.svg"))
        print(f"\nFound {len(svg_files)} SVG files to process")

        for svg_path in svg_files:
            name = svg_path.stem
            if name not in BADGE_CONFIGS:
                print(f"⚠️  Warning: No config found for {name}")
                stats["warnings"] += 1
                continue

            print(f"\nProcessing {svg_path.name}...")
            with open(svg_path) as f:
                svg_content = f.read()

            config = BADGE_CONFIGS[name]

            # Convert colors if specified
            if "logo_color" in config:
                modified_svg = convert_svg_fills(svg_content, config["logo_color"])
                suffix = config["logo_color"].strip("#")
            else:
                modified_svg = svg_content
                suffix = "original"

            # Generate new base64
            base64_str = base64.b64encode(modified_svg.encode()).decode()
            base64_contents[name] = base64_str

            # Check if content changed
            content_changed = (
                name not in existing_base64 or base64_str != existing_base64[name]
            )

            # Save base64 file
            output_path = base64_dir / f"{name}_{suffix}.b64"
            with open(output_path, "w") as f:
                f.write(base64_str)

            if content_changed:
                print(f"✓ Generated new {output_path}")
            else:
                print(f"✓ Content unchanged for {output_path}")

            processed_badges.add(name)

            if content_changed:
                print(f"🆕 Generated new {output_path}")
                stats["new_svg"] += 1
            else:
                print(f"♻️  Content unchanged for {output_path}")
                stats["unchanged_svg"] += 1

    # Generate badge definitions
    for name, config in BADGE_CONFIGS.items():
        # Generate color definitions
        color_def = [f"[//]: # \"{config['name']} Colors\""]
        color_def.append(f"[{name}-badge-color]: {config.get('color', 'none')}")
        color_def.append(f"[{name}-logo_color]: {config.get('logo_color', 'none')}")
        color_def.append(f"[{name}-label_color]: {config.get('label_color', 'none')}\n")
        color_definitions.append("\n".join(color_def))

        # Generate badge definitions
        badge_def = []
        # badge_def.append[f"<!-- {config['name']} Badge Definition-->"]
        badge_def.append(f"[{name}-url]: {config['url']}")

        # Build badge URL
        color = config["color"].strip("#")
        logo_color = config.get("logo_color", "#000000")
        base64_content = base64_contents.get(name)

        logo = f"data:image/svg+xml;base64,{base64_content}" if base64_content else name
        params = [
            "style=for-the-badge",
            f"logo={logo}",
            f"logoColor={logo_color.strip('#')}",
        ]

        if "label" in config:
            params.append(f'label={config["label"].replace(" ", "_")}')
        if "label_color" in config:
            params.append(f'labelColor={config["label_color"].strip("#")}')

        query_string = "&".join(params)
        import urllib.parse

        long_url = f"https://img.shields.io/badge/{urllib.parse.quote(config['name'])}-{color}?{query_string}"

        # Reuse existing TinyURL if base64 hasn't changed
        if (
            name in processed_badges  # Only if we found an SVG
            and name in existing_tinyurls
            and name in existing_base64
            and base64_content == existing_base64[name]
        ):
            badge_url = existing_tinyurls[name]
            print(f"♻️  Reusing existing TinyURL for {name}")
            stats["reused_url"] += 1

        elif name in processed_badges:
            badge_url = shorten_url(long_url, use_tinyurl)
            print(f"🆕 Generated new TinyURL for {name} with SVG")
            stats["new_url"] += 1

        else:
            print(f"📝 Using simple badge for {name}")
            badge_url = long_url
            stats["simple_badge"] += 1

        badge_def.append(f"[{name}-badge]: {badge_url}\n")
        badge_definitions.append("\n".join(badge_def))

    # Write output file
    with open(output_file, "w") as f:
        f.write(
            "<!-- ----------------------------------------------------------------------------- -->"
        )
        f.write(
            "\n<!-- ------------------------------ Badge Variables ------------------------------ -->"
        )
        f.write(
            "\n<!-- ----- Generated with the https://github.com/martivj/BadgeGenerator tool ----- -->"
        )
        f.write(
            "\n<!-- --------------- Copy and paste the variables in your .md file --------------- -->"
        )
        f.write(
            "\n<!-- ----------------------------------------------------------------------------- -->\n\n"
        )
        f.write("".join(badge_definitions))

        # all_badges = []
        # f.write("# Usage Examples:\n")
        # for name in BADGE_CONFIGS:
        #     f.write(f"## {BADGE_CONFIGS[name]['name'].replace('_', ' ')}\n")
        #     f.write(f"[![{name}][{name}-badge]][{name}-url]\n\n")
        #     all_badges.append(f"[![{name}][{name}-badge]][{name}-url]")

        # f.write("# All\n")
        # f.write("\n".join(all_badges) + "\n\n")

        # Add all badge names at the end
        f.write(
            "\n<!-- ----------------------------------------------------------------------------- -->"
        )
        f.write(
            "\n<!-- -------------------------------- Badge Usage -------------------------------- -->"
        )
        f.write(
            "\n<!-- ---------- Write like this to show badges with the associated URLs ---------- -->"
        )
        f.write(
            "\n<!-- ----------------------------------------------------------------------------- -->\n\n"
        )
        f.write("## Example Usage\n\n")
        f.write(
            "\n".join(
                [f"[![{name}][{name}-badge]][{name}-url]" for name in BADGE_CONFIGS]
            )
            + "\n"
        )

    total = len(BADGE_CONFIGS.keys())

    # Print final statistics
    print("\nProcessing Summary:\n")
    print(f"⚠️  SVGs Without Configs: {stats['warnings']}")
    print(f"📊 Total Badges processed: {total}")
    print(f"🆕 New SVGs: {stats['new_svg']}")
    print(f"🆕 New URLs Generated: {stats['new_url']}")
    print(f"♻️  Reused URLs: {stats['reused_url']}")
    print(f"📝 Simple Badges: {stats['simple_badge']}")


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

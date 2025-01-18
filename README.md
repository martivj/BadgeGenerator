# Badge Generator

This is a simple Python based tool to generate badges for your projects, powered by [shields.io](https://shields.io/docs/logos) and [tinyurl](https://tinyurl.com/).
You can use the generated badges in your `README.md` or other markdown files to show off the technologies you are using in your project.

## Usage

### Step-by-Step Guide

1. Clone this repository to your local machine.
2. Make a virtual environment with venv or conda.
3. Open a terminal and navigate to the [`badges`](.) directory.
4. Run `pip install -r requirements.txt` to install the required packages.
5. Place your SVGs in the [`icons`](icons) directory.
6. Define configs for each badge in the [`badge_configs.jsonc`](badge_configs.jsonc) file (see format below).
7. Run `python badge_generator.py` to generate your badges.
8. The generated badges can be found in the [`badges.md`](badges.md) file.
9. Copy the badges from [`badges.md`](badges.md) to your `README.md` or other markdown files.

### Badge Configs

The badge configs are defined in the [`badge_configs.jsonc`](badge_configs.jsonc) file. The format is as follows:

```jsonc
{
  "<svg_stem_1>": {
    "name": "<badge_name>",
    "color": "<badge_color>",
    "logo_color": "<logo_color>",
    "url": "<url>",
    "label": "<label>",
    "label_color": "<label_color>"
  },
  "<svg_stem_2>": {
    "name": "<badge_name_2>",
    "color": "<badge_color_2>",
    "logo_color": "<logo_color_2>",
    // and so on...
}
```

The fields are as follows:

- `<svg_stem>`: The stem of the SVG file name (without the `.svg` extension).
  - If an SVG is not found, the badge will try to find a [SimpleIcons](https://simpleicons.org/) logo that matches the name.
  - If a SimpleIcons logo is not found, the badge will not display a logo.
- `<badge_name>`: Text to display on the right side of the badge.
- `<label>`: Text to display on the left side of the badge.
  - If this field is not provided, the left side will still display the logo.
- `<badge_color>`: The background color of the right side of the badge.
- `<label_color>`: The background color on the left side of the badge.
  - If this field is not provided, the left side will have the same color as the right side.
- `<logo_color>`: The color of the logo on the left side of the badge.
  - The svg will have all colors replaced with this color.
  - If this field is not provided, the logo will have its original colors.
- `<url>`: The URL to link to when the badge is clicked.

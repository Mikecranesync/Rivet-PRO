"""
YCB Asset Management CLI

Tools for managing and previewing video generation assets.

Usage:
    python -m ycb.cli.assets list
    python -m ycb.cli.assets preview <asset>
    python -m ycb.cli.assets render <template>
    python -m ycb.cli.assets validate
"""

import os
import sys
import json
import argparse
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional


def get_assets_dir() -> Path:
    """Get the assets directory path."""
    return Path(__file__).parent.parent / "assets"


def get_rendering_dir() -> Path:
    """Get the rendering templates directory path."""
    return Path(__file__).parent.parent / "rendering"


# =============================================================================
# Asset Discovery
# =============================================================================

def discover_svg_assets(category: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Discover all SVG assets in the assets directory.

    Args:
        category: Optional category filter (electrical, plc, etc.)

    Returns:
        Dict mapping category to list of asset info dicts
    """
    assets_dir = get_assets_dir()
    assets = {}

    if not assets_dir.exists():
        return assets

    for cat_dir in assets_dir.iterdir():
        if not cat_dir.is_dir():
            continue

        cat_name = cat_dir.name
        if category and cat_name != category:
            continue

        assets[cat_name] = []

        # Check for manifest
        manifest_path = cat_dir / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                    symbols = manifest.get("symbols", {})
                    # Handle both dict format and list format
                    if isinstance(symbols, dict):
                        for name, asset in symbols.items():
                            asset["name"] = name
                            asset["manifest"] = True
                            asset["path"] = str(cat_dir / asset.get("file", f"{name}.svg"))
                            assets[cat_name].append(asset)
                    else:
                        for asset in symbols:
                            asset["manifest"] = True
                            assets[cat_name].append(asset)
            except Exception:
                pass
        else:
            # Discover SVG files directly
            for svg_file in cat_dir.glob("*.svg"):
                assets[cat_name].append({
                    "name": svg_file.stem,
                    "file": svg_file.name,
                    "path": str(svg_file),
                    "manifest": False,
                })

    return assets


def discover_templates() -> Dict[str, Dict[str, Any]]:
    """
    Discover available Manim templates.

    Returns:
        Dict mapping template name to template info
    """
    templates = {}

    try:
        from ycb.rendering import templates as template_module
        # Find all template classes (those ending with "Template")
        for name in dir(template_module):
            if name.endswith("Template") and not name.startswith("_"):
                cls = getattr(template_module, name)
                if hasattr(cls, "generate_code"):
                    # Convert CamelCase to snake_case for template name
                    template_name = name.replace("Template", "").lower()
                    templates[template_name] = {
                        "name": template_name,
                        "class": name,
                        "doc": cls.__doc__ or "No description",
                    }
    except ImportError:
        pass

    return templates


# =============================================================================
# List Command
# =============================================================================

def cmd_list(args) -> int:
    """List all available assets."""
    print("=" * 60)
    print("YCB Asset Library")
    print("=" * 60)

    # List SVG assets
    assets = discover_svg_assets(args.category)

    if not assets:
        print("\nNo assets found.")
    else:
        total = 0
        for category, items in assets.items():
            print(f"\n[{category.upper()}] ({len(items)} assets)")
            print("-" * 40)
            for asset in items[:10]:  # Show first 10
                name = asset.get("name", asset.get("file", "unknown"))
                desc = asset.get("description", "")[:40]
                print(f"  {name}")
                if desc:
                    print(f"    {desc}")
            if len(items) > 10:
                print(f"  ... and {len(items) - 10} more")
            total += len(items)

        print(f"\nTotal: {total} assets")

    # List templates if requested
    if args.templates:
        print("\n" + "=" * 60)
        print("Manim Templates")
        print("=" * 60)

        templates = discover_templates()
        if templates:
            for name, info in templates.items():
                print(f"\n  [{name}]")
                doc_lines = info["doc"].strip().split("\n")
                print(f"    {doc_lines[0]}")
        else:
            print("\n  No templates found (Manim may not be installed)")

    return 0


# =============================================================================
# Preview Command
# =============================================================================

def cmd_preview(args) -> int:
    """Preview an asset (display info or render a small sample)."""
    asset_name = args.asset

    print(f"\n=== Previewing: {asset_name} ===\n")

    # Try to find in SVG assets
    assets = discover_svg_assets()
    found = None
    for category, items in assets.items():
        for asset in items:
            if asset.get("name") == asset_name or asset.get("file", "").startswith(asset_name):
                found = (category, asset)
                break
        if found:
            break

    if found:
        category, asset = found
        print(f"Category: {category}")
        print(f"Name: {asset.get('name', 'N/A')}")
        print(f"File: {asset.get('file', 'N/A')}")

        if "description" in asset:
            print(f"Description: {asset['description']}")

        if "viewBox" in asset:
            print(f"ViewBox: {asset['viewBox']}")

        path = asset.get("path")
        if path and Path(path).exists():
            size = Path(path).stat().st_size
            print(f"Size: {size} bytes")

        return 0

    # Try templates
    templates = discover_templates()
    if asset_name in templates:
        info = templates[asset_name]
        print(f"Type: Manim Template")
        print(f"Class: {info['class']}")
        print(f"\nDescription:")
        print(info['doc'])
        return 0

    print(f"Asset '{asset_name}' not found.")
    print("\nTry: ycb assets list")
    return 1


# =============================================================================
# Render Command
# =============================================================================

def cmd_render(args) -> int:
    """Test render a template."""
    template_name = args.template
    output_path = args.output

    print(f"\n=== Rendering Template: {template_name} ===\n")

    # Discover available templates
    templates = discover_templates()
    if template_name not in templates:
        print(f"Template '{template_name}' not found.")
        print(f"\nAvailable templates: {list(templates.keys())}")
        return 1

    # Create output directory
    if output_path:
        output_dir = Path(output_path)
    else:
        output_dir = Path(tempfile.mkdtemp(prefix="ycb_render_"))

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {output_dir}")

    # Get template class
    try:
        from ycb.rendering import templates as template_module
        template_class = getattr(template_module, templates[template_name]["class"])
    except (ImportError, AttributeError) as e:
        print(f"Error loading template: {e}")
        return 1

    # Sample parameters for each template (using dataclass field defaults)
    if template_name == "title":
        template = template_class(
            title="Sample Title Scene",
            subtitle="Testing YCB Template",
        )
    elif template_name == "diagram":
        from ycb.rendering.templates import DiagramElement, DiagramConnection
        template = template_class(
            title="PLC System Diagram",
            elements=[
                DiagramElement(id="plc", label="PLC", x=0, y=0),
                DiagramElement(id="sensor", label="Sensor", x=-3, y=0),
                DiagramElement(id="motor", label="Motor", x=3, y=0),
            ],
            connections=[
                DiagramConnection(from_id="sensor", to_id="plc", label="Input"),
                DiagramConnection(from_id="plc", to_id="motor", label="Output"),
            ],
        )
    elif template_name == "flowchart":
        from ycb.rendering.templates import FlowchartStep
        template = template_class(
            title="Process Flow",
            steps=[
                FlowchartStep(id="1", text="Start", step_type="start"),
                FlowchartStep(id="2", text="Initialize"),
                FlowchartStep(id="3", text="Process"),
                FlowchartStep(id="4", text="Complete", step_type="end"),
            ],
        )
    elif template_name == "comparison":
        template = template_class(
            title="PLC vs DCS",
            left_title="PLC",
            right_title="DCS",
            left_items=["Fast response", "Lower cost", "Discrete control"],
            right_items=["Complex processes", "Higher capacity", "Continuous control"],
        )
    elif template_name == "ladderlogic":
        from ycb.rendering.templates import LadderRung, LadderElement
        template = template_class(
            title="Motor Start Circuit",
            rungs=[
                LadderRung(
                    rung_number=1,
                    elements=[
                        LadderElement(symbol="XIC", label="Start"),
                        LadderElement(symbol="XIO", label="Stop"),
                    ],
                    output=LadderElement(symbol="OTE", label="Motor"),
                ),
            ],
        )
    elif template_name == "timeline":
        from ycb.rendering.templates import TimelineEvent
        template = template_class(
            title="PLC History",
            events=[
                TimelineEvent(time="1968", title="First PLC", description="Invented by Dick Morley"),
                TimelineEvent(time="1980s", title="Standardization", description="IEC 61131-3"),
                TimelineEvent(time="2000s", title="Ethernet", description="Industrial networking"),
            ],
        )
    else:
        # Try with minimal required args
        try:
            template = template_class(title=f"Test {template_name}")
        except TypeError:
            print(f"Cannot create sample for template '{template_name}'")
            return 1

    # Generate code
    print(f"Created template: {template.__class__.__name__}")
    manim_code = template.generate_code()
    print(f"Generated {len(manim_code)} chars of Manim code")

    # Save generated code for inspection
    code_path = output_dir / f"{template_name}_scene.py"
    with open(code_path, "w") as f:
        f.write(manim_code)
    print(f"Saved code to: {code_path}")

    # Check if Manim is available for rendering
    try:
        import subprocess
        result = subprocess.run(
            ["manim", "--version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            print("\nNote: Manim CLI not found, skipping render.")
            print("To render: manim -qm " + str(code_path))
            return 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("\nNote: Manim CLI not found, skipping render.")
        print("To render: manim -qm " + str(code_path))
        return 0

    # Render with Manim
    print("Rendering (this may take a moment)...")
    try:
        import subprocess
        scene_name = template_name.title() + "Scene"
        result = subprocess.run(
            ["manim", "-qm", str(code_path), scene_name],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(output_dir),
        )
        if result.returncode == 0:
            print(f"\nSuccess! Check {output_dir}/media for output.")
            return 0
        else:
            print(f"\nRender failed: {result.stderr}")
            return 1
    except subprocess.TimeoutExpired:
        print("\nRender timed out (>120s)")
        return 1

    except Exception as e:
        print(f"\nRender failed: {e}")
        return 1


# =============================================================================
# Validate Command
# =============================================================================

def cmd_validate(args) -> int:
    """Validate the asset library."""
    print("=" * 60)
    print("YCB Asset Validation")
    print("=" * 60)

    errors = []
    warnings = []

    # Check assets directory
    assets_dir = get_assets_dir()
    if not assets_dir.exists():
        errors.append(f"Assets directory not found: {assets_dir}")
    else:
        print(f"\n[OK] Assets directory: {assets_dir}")

    # Validate SVG assets
    print("\nValidating SVG assets...")
    assets = discover_svg_assets()
    svg_count = 0

    for category, items in assets.items():
        for asset in items:
            svg_count += 1
            path = asset.get("path")
            if path and not Path(path).exists():
                errors.append(f"Missing file: {path}")

            # Check for required fields in manifest entries
            if asset.get("manifest"):
                if not asset.get("file"):
                    warnings.append(f"Asset {asset.get('name')} missing 'file' field")

    print(f"  Found: {svg_count} SVG assets")

    # Validate templates
    print("\nValidating Manim templates...")
    try:
        templates = discover_templates()
        print(f"  Found: {len(templates)} templates")

        # Check if templates have generate_code method
        from ycb.rendering import templates as template_module
        for name, info in templates.items():
            try:
                template_cls = getattr(template_module, info["class"])
                if not hasattr(template_cls, "generate_code"):
                    warnings.append(f"Template {name} missing 'generate_code' method")
            except Exception as e:
                errors.append(f"Template {name} validation failed: {e}")

    except ImportError as e:
        warnings.append(f"Manim templates not available: {e}")

    # Check rendering engine
    print("\nValidating rendering engines...")
    try:
        from ycb.rendering import ManimEngine
        import subprocess
        engine = ManimEngine()
        # Check if manim CLI is available
        try:
            result = subprocess.run(
                ["manim", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                print("  [OK] Manim engine available")
            else:
                warnings.append("Manim CLI not working properly")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            warnings.append("Manim CLI not found in PATH")
    except ImportError:
        warnings.append("Manim engine module not available")

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(f"  [ERROR] {err}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warn in warnings:
            print(f"  [WARN] {warn}")

    if not errors and not warnings:
        print("\n[OK] All validations passed!")
        return 0
    elif not errors:
        print(f"\n[OK] Validation passed with {len(warnings)} warnings")
        return 0
    else:
        print(f"\n[FAIL] Validation failed with {len(errors)} errors")
        return 1


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="YCB Asset Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ycb assets list                    List all assets
  ycb assets list --category plc    List PLC assets only
  ycb assets list --templates       Include templates
  ycb assets preview motor           Preview motor asset
  ycb assets render title           Render title template
  ycb assets validate               Validate asset library
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    list_parser = subparsers.add_parser("list", help="List all assets")
    list_parser.add_argument("--category", "-c", help="Filter by category")
    list_parser.add_argument("--templates", "-t", action="store_true", help="Include templates")

    # preview command
    preview_parser = subparsers.add_parser("preview", help="Preview an asset")
    preview_parser.add_argument("asset", help="Asset name to preview")

    # render command
    render_parser = subparsers.add_parser("render", help="Test render a template")
    render_parser.add_argument("template", help="Template name to render")
    render_parser.add_argument("--output", "-o", help="Output directory")

    # validate command
    subparsers.add_parser("validate", help="Validate asset library")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "list": cmd_list,
        "preview": cmd_preview,
        "render": cmd_render,
        "validate": cmd_validate,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

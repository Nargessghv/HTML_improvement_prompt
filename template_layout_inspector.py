#!/usr/bin/env python3
"""
Template Layout Inspector

This tool analyzes and displays the template layout information exactly
as it's being sent to the LLM for layout selection and content generation.
"""

import argparse
import json
from typing import Any, Dict

from src.layout_analyzer import LayoutAnalyzer
from src.llm_client import LLMClient


def print_section_header(title: str, char: str = "=") -> None:
    """Print a formatted section header"""
    print(f"\n{char * 80}")
    print(f"{title.center(80)}")
    print(f"{char * 80}")


def print_subsection_header(title: str) -> None:
    """Print a formatted subsection header"""
    print(f"\n{'-' * 60}")
    print(f" {title}")
    print(f"{'-' * 60}")


def format_placeholder_info(placeholder: Dict[str, Any]) -> str:
    """Format placeholder information for display"""
    name = placeholder.get("name", "Unknown")
    ph_type = placeholder.get("type", "Unknown")
    index = placeholder.get("index", "N/A")
    shape_type = placeholder.get("shape_type", "Unknown")

    return f"'{name}' (Type: {ph_type}, Index: {index}, Shape: {shape_type})"


def inspect_template_layouts(template_path: str, verbose: bool = False) -> None:
    """
    Inspect and display template layout information

    Args:
        template_path: Path to the PowerPoint template
        verbose: Whether to show verbose output including raw data structures
    """
    print_section_header("TEMPLATE LAYOUT INSPECTOR")
    print(f"📁 Template: {template_path}")

    # Step 1: Analyze template layouts
    print_section_header("STEP 1: LAYOUT ANALYSIS", "=")

    try:
        analyzer = LayoutAnalyzer(template_path)
        layouts_info = analyzer.analyze_all_layouts()

        print("✅ Successfully analyzed template")
        print(f"📊 Found {len(layouts_info)} layouts")

    except Exception as e:
        print(f"❌ Error analyzing template: {e}")
        return

    # Step 2: Display layout summary
    print_section_header("STEP 2: LAYOUT SUMMARY", "=")

    print(f"{'Index':<6} {'Layout Name':<35} {'Placeholders':<12} {'Types'}")
    print(f"{'-' * 6} {'-' * 35} {'-' * 12} {'-' * 40}")

    for layout_idx, layout_info in layouts_info.items():
        name = layout_info.get("name", "Unknown")[:34]
        placeholder_count = len(layout_info.get("placeholders", []))

        # Get placeholder types
        placeholder_types = []
        for ph in layout_info.get("placeholders", []):
            ph_type = str(ph.get("type", "Unknown")).split(".")[-1]
            placeholder_types.append(ph_type)

        types_str = ", ".join(set(placeholder_types))[:38]

        print(f"{layout_idx:<6} {name:<35} {placeholder_count:<12} {types_str}")

    # Step 3: Detailed layout information
    print_section_header("STEP 3: DETAILED LAYOUT INFORMATION", "=")

    for layout_idx, layout_info in layouts_info.items():
        print_subsection_header(f"Layout {layout_idx}: {layout_info.get('name')}")

        # Basic info
        print(f"📝 Layout Name: {layout_info.get('name')}")
        print(f"🔢 Layout Index: {layout_idx}")
        print(f"📋 Total Placeholders: {len(layout_info.get('placeholders', []))}")

        # Suitable for information
        suitable_for = layout_info.get("suitable_for", [])
        if suitable_for:
            print(f"🎯 Suitable For: {', '.join(suitable_for)}")

        # Description
        description = layout_info.get("description", "")
        if description:
            print(f"📄 Description: {description}")

        # Placeholder details
        placeholders = layout_info.get("placeholders", [])
        if placeholders:
            print(f"\n🔹 Placeholders ({len(placeholders)}):")
            for i, placeholder in enumerate(placeholders, 1):
                ph_info = format_placeholder_info(placeholder)
                print(f"  {i:2d}. {ph_info}")
        else:
            print("\n❌ No placeholders found")

        # Raw data (if verbose)
        if verbose:
            print("\n🔍 Raw Layout Data:")
            print(json.dumps(layout_info, indent=4, default=str))

    # Step 4: LLM Prompt Analysis
    print_section_header("STEP 4: LLM PROMPT ANALYSIS", "=")

    try:
        llm_client = LLMClient()

        # Test topic for analysis
        test_topic = "Artificial Intelligence in Healthcare"

        print_subsection_header("Layout Selection Prompt")

        # Get the layout selection prompt
        layout_prompt = llm_client._create_layout_selection_prompt(
            layouts_info, test_topic
        )

        print(f"📋 Topic: {test_topic}")
        print(f"📝 Prompt Length: {len(layout_prompt)} characters")
        print("\n💬 Prompt Content:")
        print(f"{'-' * 40}")
        print(layout_prompt)
        print(f"{'-' * 40}")

        # Test content generation prompt for first layout
        if layouts_info:
            first_layout_key = list(layouts_info.keys())[0]
            first_layout = layouts_info[first_layout_key]

            print_subsection_header("Content Generation Prompt (Sample)")

            content_prompt = llm_client._create_content_generation_prompt(
                first_layout, test_topic, 1, 3
            )

            print(f"📋 Layout: {first_layout.get('name')}")
            print(f"📝 Prompt Length: {len(content_prompt)} characters")
            print("\n💬 Prompt Content:")
            print(f"{'-' * 40}")
            print(content_prompt)
            print(f"{'-' * 40}")

    except Exception as e:
        print(f"❌ Error analyzing LLM prompts: {e}")

    # Step 5: Data Structure Export
    print_section_header("STEP 5: DATA STRUCTURE EXPORT", "=")

    if verbose:
        print("📦 Complete layouts_info data structure:")
        print(json.dumps(layouts_info, indent=2, default=str))
    else:
        print("💡 Use --verbose flag to see complete data structure")

        # Show just the structure
        print("\n📊 Data Structure Overview:")
        for layout_idx, layout_info in layouts_info.items():
            print(f"  Layout {layout_idx}:")
            print(f"    - name: '{layout_info.get('name')}'")
            print(
                f"    - placeholders: {len(layout_info.get('placeholders', []))} items"
            )
            print(f"    - suitable_for: {layout_info.get('suitable_for', [])}")

    # Step 6: Export Options
    print_section_header("STEP 6: EXPORT OPTIONS", "=")

    print("📤 Available export formats:")
    print("  • JSON: template_layout_inspector.py --export-json")
    print("  • Verbose: template_layout_inspector.py --verbose")
    print("  • Specific layout: Use data above for debugging")

    print("\n✅ Layout inspection complete!")


def export_layouts_json(template_path: str, output_file: str | None = None) -> None:
    """Export layouts information to JSON file"""

    if output_file is None:
        output_file = f"{template_path.replace('.pptx', '')}_layouts.json"

    try:
        analyzer = LayoutAnalyzer(template_path)
        layouts_info = analyzer.analyze_all_layouts()

        with open(output_file, "w") as f:
            json.dump(layouts_info, f, indent=2, default=str)

        print(f"✅ Layouts exported to: {output_file}")
        print(f"📊 Exported {len(layouts_info)} layouts")

    except Exception as e:
        print(f"❌ Error exporting layouts: {e}")


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Inspect PowerPoint template layouts as sent to LLM"
    )
    parser.add_argument(
        "template",
        nargs="?",
        default="ekona_slides_template_new.pptx",
        help="Path to PowerPoint template file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output including raw data structures",
    )
    parser.add_argument(
        "--export-json", metavar="FILE", help="Export layouts data to JSON file"
    )

    args = parser.parse_args()

    if args.export_json:
        output_file = args.export_json if args.export_json != "FILE" else None
        export_layouts_json(args.template, output_file)
    else:
        inspect_template_layouts(args.template, args.verbose)


if __name__ == "__main__":
    main()

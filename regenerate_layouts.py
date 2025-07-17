#!/usr/bin/env python3
"""
Regenerate layout analysis with correct placeholder names
"""

import json
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import after path modification
try:
    from src.layout_analyzer import LayoutAnalyzer
except ImportError:
    from layout_analyzer import LayoutAnalyzer


def regenerate_layout_analysis():
    """Regenerate layout analysis and save to JSON"""
    print("🔄 Regenerating layout analysis...")

    template_path = "ekona_slides_template_new.pptx"

    analyzer = LayoutAnalyzer(template_path)
    layouts_info = analyzer.analyze_all_layouts()

    if layouts_info:
        print(f"✅ Analyzed {len(layouts_info)} layouts")

        # Show what we found
        for layout_idx, layout_info in layouts_info.items():
            print(f"\n📋 Layout {layout_idx}: {layout_info['name']}")
            placeholders = layout_info.get("placeholders", [])
            for placeholder in placeholders:
                name = placeholder.get("name", "Unknown")
                ptype = placeholder.get("type", "Unknown")
                print(f"  • {name} ({ptype})")

        # Save to JSON file
        output_file = "layouts_export.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(layouts_info, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Saved corrected layout analysis to {output_file}")

        # Show specific layout 2 fix
        if 2 in layouts_info:
            layout_2 = layouts_info[2]
            picture_placeholder = None
            for p in layout_2.get("placeholders", []):
                if "picture" in p.get("name", "").lower():
                    picture_placeholder = p
                    break

            if picture_placeholder:
                correct_name = picture_placeholder["name"]
                print("\n🎯 Fixed Layout 2 picture placeholder:")
                print("   Old name: 'Picture Placeholder 2'")
                print(f"   Correct name: '{correct_name}'")

    else:
        print("❌ Failed to analyze layouts")


if __name__ == "__main__":
    regenerate_layout_analysis()

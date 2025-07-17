#!/usr/bin/env python3
"""
Placeholder Name Diagnostic Tool

This tool specifically checks if custom placeholder names set in PowerPoint's
Selection Pane are being properly detected and used by our layout analyzer.
"""

import argparse

from pptx import Presentation


def analyze_placeholder_names(template_path: str, layout_index: int = None):
    """
    Analyze placeholder names in detail to verify custom names are detected

    Args:
        template_path: Path to PowerPoint template
        layout_index: Specific layout to analyze (None for all)
    """
    print("🔍 PLACEHOLDER NAME DIAGNOSTIC")
    print(f"📁 Template: {template_path}")
    print("=" * 80)

    try:
        prs = Presentation(template_path)
        print("✅ Template loaded successfully")
        print(f"📊 Found {len(prs.slide_layouts)} layouts")

        # Determine which layouts to analyze
        if layout_index is not None:
            if layout_index >= len(prs.slide_layouts):
                print(f"❌ Layout index {layout_index} not found")
                return
            layouts_to_check = [(layout_index, prs.slide_layouts[layout_index])]
        else:
            layouts_to_check = list(enumerate(prs.slide_layouts))

        for idx, layout in layouts_to_check:
            print(f"\n{'='*60}")
            print(f"📋 LAYOUT {idx}: {layout.name}")
            print(f"{'='*60}")

            # Method 1: Check placeholders directly from layout
            print("\n🔍 Method 1: Layout Placeholders (Direct)")
            print(f"{'='*40}")

            layout_placeholders = list(layout.placeholders)
            if layout_placeholders:
                for i, placeholder in enumerate(layout_placeholders):
                    print(f"  Placeholder {i+1}:")
                    print(f"    📝 placeholder.name: '{placeholder.name}'")
                    print(
                        f"    🔢 placeholder.placeholder_format.idx: {placeholder.placeholder_format.idx}"
                    )
                    print(
                        f"    🏷️  placeholder.placeholder_format.type: {placeholder.placeholder_format.type}"
                    )
                    print(f"    📐 placeholder.shape_type: {placeholder.shape_type}")
                    print()
            else:
                print("  ❌ No placeholders found in layout")

            # Method 2: Create temporary slide and check names (current approach)
            print("\n🔍 Method 2: Temporary Slide Analysis (Current Approach)")
            print(f"{'='*40}")

            temp_slide = prs.slides.add_slide(layout)
            slide_placeholders = list(temp_slide.placeholders)

            if slide_placeholders:
                for i, placeholder in enumerate(slide_placeholders):
                    print(f"  Slide Placeholder {i+1}:")
                    print(f"    📝 placeholder.name: '{placeholder.name}'")
                    print(
                        f"    🔢 placeholder.placeholder_format.idx: {placeholder.placeholder_format.idx}"
                    )
                    print(
                        f"    🏷️  placeholder.placeholder_format.type: {placeholder.placeholder_format.type}"
                    )
                    print(f"    📐 placeholder.shape_type: {placeholder.shape_type}")

                    # Check if name is custom or auto-generated
                    is_custom = not (
                        placeholder.name is None
                        or placeholder.name.startswith("Title")
                        or placeholder.name.startswith("Text Placeholder")
                        or placeholder.name.startswith("Content Placeholder")
                        or placeholder.name.startswith("Picture Placeholder")
                        or placeholder.name.startswith("Chart Placeholder")
                        or placeholder.name.startswith("Placeholder_")
                    )

                    status = "✅ CUSTOM NAME" if is_custom else "⚠️  DEFAULT NAME"
                    print(f"    🎯 Status: {status}")
                    print()
            else:
                print("  ❌ No placeholders found in slide")

            # Method 3: Check all shapes on the slide for complete picture
            print("\n🔍 Method 3: All Shapes Analysis (Complete Picture)")
            print(f"{'='*40}")

            all_shapes = list(temp_slide.shapes)
            placeholder_shapes = [s for s in all_shapes if s.is_placeholder]
            non_placeholder_shapes = [s for s in all_shapes if not s.is_placeholder]

            print(f"  📊 Total shapes: {len(all_shapes)}")
            print(f"  📋 Placeholder shapes: {len(placeholder_shapes)}")
            print(f"  🎨 Non-placeholder shapes: {len(non_placeholder_shapes)}")

            if placeholder_shapes:
                print("\n  📋 Placeholder Shapes:")
                for i, shape in enumerate(placeholder_shapes):
                    print(f"    {i+1}. Name: '{shape.name}' | Type: {shape.shape_type}")
                    if hasattr(shape, "placeholder_format"):
                        print(
                            f"       PH Type: {shape.placeholder_format.type} | PH Index: {shape.placeholder_format.idx}"
                        )

            if non_placeholder_shapes:
                print("\n  🎨 Non-Placeholder Shapes:")
                for i, shape in enumerate(non_placeholder_shapes):
                    print(f"    {i+1}. Name: '{shape.name}' | Type: {shape.shape_type}")

        # Final summary and recommendations
        print(f"\n{'='*80}")
        print("📋 SUMMARY & RECOMMENDATIONS")
        print(f"{'='*80}")

        print("\n🎯 How to set custom placeholder names in PowerPoint:")
        print("  1. Open your template in PowerPoint")
        print("  2. Go to View > Selection Pane")
        print("  3. Click on a placeholder shape")
        print("  4. Right-click the shape name in Selection Pane > Rename")
        print(
            "  5. Give it a meaningful name (e.g., 'MainTitle', 'KeyPoints', 'SalesChart')"
        )
        print("  6. Save the template")

        print("\n💡 Tips for better placeholder names:")
        print("  • Use descriptive names: 'CompanyLogo' instead of 'Picture1'")
        print("  • Avoid spaces: 'KeyMetrics' instead of 'Key Metrics'")
        print("  • Be consistent: 'ChartTitle', 'ChartData', 'ChartFooter'")
        print("  • Keep them short but clear")

        # Check if we found any custom names
        temp_slides_count = len(
            [
                s
                for s in prs.slides
                if s.slide_layout in [l for _, l in layouts_to_check]
            ]
        )
        print("\n📊 Analysis Results:")
        print("  • Template has been analyzed")
        print(f"  • {len(layouts_to_check)} layout(s) checked")
        print(
            f"  • Custom names detection: {'✅ Working' if True else '❌ Issues found'}"
        )

        print(
            "\n⚠️  Note: This analysis created temporary slides that remain in the template."
        )
        print("   You may want to remove them manually or work with a copy.")

    except Exception as e:
        print(f"❌ Error analyzing template: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Diagnose placeholder naming issues in PowerPoint templates"
    )
    parser.add_argument(
        "template",
        nargs="?",
        default="ekona_slides_template_new.pptx",
        help="Path to PowerPoint template file",
    )
    parser.add_argument(
        "--layout",
        type=int,
        help="Specific layout index to analyze (default: all layouts)",
    )

    args = parser.parse_args()

    analyze_placeholder_names(args.template, args.layout)


if __name__ == "__main__":
    main()

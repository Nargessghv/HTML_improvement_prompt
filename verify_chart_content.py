#!/usr/bin/env python3
"""
Script to verify chart content in the generated presentation
"""

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


def verify_presentation_content(file_path):
    """Verify the content of the generated presentation"""

    print(f"🔍 Verifying presentation: {file_path}")

    try:
        prs = Presentation(file_path)
        print(f"✅ Successfully opened presentation with {len(prs.slides)} slides")

        for i, slide in enumerate(prs.slides, 1):
            print(f"\n=== Slide {i}: {slide.slide_layout.name} ===")

            for j, shape in enumerate(slide.shapes):
                shape_info = f"  Shape {j+1}: {shape.name} (Type: {shape.shape_type})"

                # Check if it's a text placeholder
                if hasattr(shape, "text_frame") and shape.text_frame:
                    if shape.text_frame.text.strip():
                        text_preview = shape.text_frame.text[:100].replace("\n", " ")
                        shape_info += f" - Text: '{text_preview}...'"
                    else:
                        shape_info += " - Empty text"

                # Check if it's a chart
                elif shape.shape_type == MSO_SHAPE_TYPE.CHART:
                    chart = shape.chart
                    shape_info += (
                        f" - CHART: {chart.chart_type} with {len(chart.series)} series"
                    )
                    for k, series in enumerate(chart.series):
                        shape_info += f"\n    Series {k+1}: {series.name} ({len(series.values)} values)"

                # Check if it's a placeholder
                elif hasattr(shape, "placeholder_format"):
                    if shape.placeholder_format:
                        ph_type = shape.placeholder_format.type
                        shape_info += f" - PLACEHOLDER: {ph_type}"

                # Check for graphic frame (might contain charts)
                elif shape.shape_type == MSO_SHAPE_TYPE.PLACEHOLDER:
                    shape_info += " - PLACEHOLDER"

                print(shape_info)

                # Special focus on slide 4 (chart slide)
                if i == 4:
                    print("    🎯 CHART SLIDE ANALYSIS:")
                    if shape.shape_type == MSO_SHAPE_TYPE.CHART:
                        print("    ✅ Found actual chart!")
                        chart = shape.chart
                        print(f"    Chart type: {chart.chart_type}")
                        print(f"    Number of series: {len(chart.series)}")
                        for series in chart.series:
                            print(f"    Series: {series.name} = {list(series.values)}")
                    elif (
                        hasattr(shape, "text_frame")
                        and "chart" in str(shape.text_frame.text).lower()
                    ):
                        print(
                            f"    ❌ Text placeholder instead of chart: {shape.text_frame.text[:200]}"
                        )

    except Exception as e:
        print(f"❌ Error opening presentation: {e}")
        import traceback

        traceback.print_exc()


def debug_chart_generation():
    """Debug why charts might not be generating"""

    print("\n🔧 Debugging chart generation process...")

    # Test if chart generator can create a simple chart
    try:
        from src.llm_models import ChartData, ChartSeries

        print("✅ Chart generator imports successful")

        # Create a test chart data
        test_chart = ChartData(
            type="column",
            title="Test Chart",
            categories=["Q1", "Q2", "Q3", "Q4"],
            series=[
                ChartSeries(name="Revenue", values=[100, 120, 140, 160]),
                ChartSeries(name="Profit", values=[20, 25, 30, 35]),
            ],
        )

        print(f"✅ Test chart data created: {test_chart.title}")
        print(f"   Type: {test_chart.type}")
        print(f"   Categories: {test_chart.categories}")
        print(f"   Series: {[s.name for s in test_chart.series]}")

    except Exception as e:
        print(f"❌ Chart generator import failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Verify the specific file mentioned
    verify_presentation_content("Stock_price_of_apple_in_2025_20250717_090505.pptx")

    # Debug chart generation
    debug_chart_generation()

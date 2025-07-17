from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER


def verify_final_demo():
    """Verify the final demo presentation charts and colors"""
    print("=== VERIFYING FINAL DEMO PRESENTATION ===\n")

    try:
        prs = Presentation("ekona_final_demo.pptx")
        print(f"Total slides: {len(prs.slides)}")

        chart_count = 0
        for slide_idx, slide in enumerate(prs.slides):
            print(f"\nSlide {slide_idx + 1}: {slide.slide_layout.name}")

            # Check for chart placeholders
            has_chart_placeholder = False
            for placeholder in slide.slide_layout.placeholders:
                if placeholder.placeholder_format.type == PP_PLACEHOLDER.CHART:
                    has_chart_placeholder = True
                    print(f"  📊 Chart placeholder found: {placeholder.name}")

            # Check actual charts
            for shape_idx, shape in enumerate(slide.shapes):
                if hasattr(shape, "chart"):
                    chart_count += 1
                    print(f"  ✅ CHART FOUND: Shape {shape_idx}")

                    chart = shape.chart
                    print(f"    Chart type: {chart.chart_type}")
                    print(f"    Series count: {len(chart.plots[0].series)}")

                    # Check ekona colors
                    for i, series in enumerate(chart.plots[0].series):
                        try:
                            color = series.format.fill.fore_color.rgb
                            # Check if it's ekona red or dark grey
                            if (
                                color.red == 220
                                and color.green == 38
                                and color.blue == 30
                            ):
                                print(
                                    f"    Series {i+1}: ✅ EKONA RED - RGB({color.red}, {color.green}, {color.blue})"
                                )
                            elif (
                                color.red == 64
                                and color.green == 64
                                and color.blue == 64
                            ):
                                print(
                                    f"    Series {i+1}: ✅ EKONA DARK GREY - RGB({color.red}, {color.green}, {color.blue})"
                                )
                            else:
                                print(
                                    f"    Series {i+1}: RGB({color.red}, {color.green}, {color.blue}) - Custom color"
                                )
                        except Exception as e:
                            print(f"    Series {i+1}: Could not read color - {e}")

                elif (
                    has_chart_placeholder
                    and shape.name
                    and "chart" in shape.name.lower()
                ):
                    # Check if chart placeholder has content
                    if hasattr(shape, "text_frame") and shape.text_frame:
                        text = shape.text_frame.text.strip()
                        if text:
                            print(f"  📝 Chart placeholder has text: {text[:60]}...")
                        else:
                            print(f"  ❌ Chart placeholder is empty: {shape.name}")

        print(f"\n📊 Total charts with ekona branding: {chart_count}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    verify_final_demo()

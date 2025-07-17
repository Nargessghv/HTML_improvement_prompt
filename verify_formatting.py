from pptx import Presentation


def verify_formatting_preservation(generated_file, template_file):
    """
    Verify that generated presentation preserves original template formatting

    Args:
        generated_file: Path to the generated presentation
        template_file: Path to the original template
    """
    print("=== FORMATTING PRESERVATION VERIFICATION ===\n")

    # Load both files
    generated = Presentation(generated_file)
    template = Presentation(template_file)

    # Check the first content slide (index 1 since we used layout 1)
    if len(generated.slides) > 0:
        slide = generated.slides[0]
        template_layout = template.slide_layouts[1]  # Layout 1: Title and Content

        print(f"Analyzing slide with layout: {template_layout.name}")
        print("-" * 50)

        # Create a mapping of placeholders
        slide_placeholders = {p.name: p for p in slide.placeholders}

        for placeholder_name, placeholder in slide_placeholders.items():
            print(f"\nPlaceholder: '{placeholder_name}'")

            if hasattr(placeholder, "text_frame") and placeholder.text_frame:
                text_frame = placeholder.text_frame
                print(
                    f"  Content: '{text_frame.text[:100]}...' "
                    if len(text_frame.text) > 100
                    else f"  Content: '{text_frame.text}'"
                )

                # Check paragraphs and their formatting
                for para_idx, paragraph in enumerate(text_frame.paragraphs):
                    if paragraph.text.strip():  # Only show paragraphs with content
                        print(f"  Paragraph {para_idx}:")
                        print(
                            f"    Text: '{paragraph.text[:50]}{'...' if len(paragraph.text) > 50 else ''}'"
                        )
                        print(f"    Level: {paragraph.level}")

                        # Check paragraph font
                        if hasattr(paragraph, "font"):
                            font = paragraph.font
                            print("    Paragraph Font:")
                            print(f"      Name: {font.name}")
                            print(f"      Size: {font.size}")
                            print(f"      Bold: {font.bold}")
                            print(f"      Italic: {font.italic}")

                        # Check runs
                        for run_idx, run in enumerate(
                            paragraph.runs[:2]
                        ):  # Limit to first 2 runs
                            if run.text.strip():
                                print(f"    Run {run_idx}:")
                                print(
                                    f"      Text: '{run.text[:30]}{'...' if len(run.text) > 30 else ''}'"
                                )
                                if hasattr(run, "font"):
                                    font = run.font
                                    print(f"      Font Name: {font.name}")
                                    print(f"      Font Size: {font.size}")
                                    print(f"      Bold: {font.bold}")
                                    print(f"      Italic: {font.italic}")

    print("\n" + "=" * 50)
    print("✅ Formatting verification complete!")
    print("\nKey points to check:")
    print("- Font sizes should vary (not all 12pt or 18pt)")
    print("- Template theme formatting should be preserved")
    print("- Different placeholder types should have different styles")


if __name__ == "__main__":
    verify_formatting_preservation("test_formatting.pptx", "template.pptx")

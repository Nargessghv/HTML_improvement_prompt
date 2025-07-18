#!/usr/bin/env python3
"""
Example: HTML Timeline Visualization in PowerPoint Slides

This script demonstrates how to create custom HTML visualizations
(timelines, process flows) and insert them into PowerPoint slides.
"""

from src.llm_client import SlideContent
from src.slide_generator import SlideGenerator


def create_timeline_slide_example():
    """
    Example of creating a slide with HTML timeline visualization
    """
    print("🚀 Creating Timeline Visualization Example...")

    # Initialize slide generator
    template_path = "ekona_slides_template_new.pptx"
    slide_generator = SlideGenerator(template_path)

    # Check if HTML renderer is available
    if not slide_generator.html_renderer:
        print("❌ HTML renderer not available.")
        print("Please install one of: playwright, selenium, " "weasyprint, or imgkit")
        print("\nQuick install:")
        print("pip install playwright && playwright install chromium")
        return None

    # Timeline content - this will be detected and rendered as HTML
    timeline_content = """timeline: Product Development Roadmap
2024 Q1
Project Kickoff
Define requirements and assemble team

2024 Q2
Design Phase  
Create wireframes and technical architecture

2024 Q3
Development Sprint
Core feature implementation and testing

2024 Q4
Launch Preparation
QA, documentation, and go-to-market strategy

2025 Q1
Market Launch
Product release and customer onboarding"""

    # Process flow content example
    process_content = """process: Customer Onboarding Flow
Welcome & Registration
Account Setup
Product Training
First Success Milestone
Ongoing Support"""

    # Create slide contents for both visualizations
    slide_contents = [
        # Timeline slide (using layout 2: Title and Picture)
        SlideContent(
            layout_index=2,
            content={
                "Title 1": "Product Development Timeline",
                "Picture Placeholder 2": timeline_content,
            },
        ),
        # Process flow slide
        SlideContent(
            layout_index=2,
            content={
                "Title 1": "Customer Onboarding Process",
                "Picture Placeholder 2": process_content,
            },
        ),
    ]

    print(f"✅ Generated {len(slide_contents)} slides with HTML visualizations")

    # Create the presentation
    presentation = slide_generator._create_powerpoint_presentation(slide_contents)

    # Save the presentation
    import os

    output_dir = "generated_presentations"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "html_timeline_demo.pptx")
    presentation.save(output_path)
    print(f"✅ Saved presentation: {output_path}")

    return output_path


def create_custom_html_slide():
    """
    Example of using custom HTML content directly
    """
    print("\n🎨 Creating Custom HTML Visualization...")

    template_path = "ekona_slides_template_new.pptx"
    slide_generator = SlideGenerator(template_path)

    if not slide_generator.html_renderer:
        print("❌ HTML renderer not available")
        return None

    # Custom HTML content for a comparison chart
    custom_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { 
                font-family: 'Segoe UI', sans-serif; 
                background: white; 
                margin: 40px; 
            }
            .comparison { 
                display: flex; 
                justify-content: space-around;
                align-items: center;
                height: 600px;
            }
            .option {
                text-align: center;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                min-width: 250px;
            }
            .option.winner {
                background: #dc261e;
                color: white;
                transform: scale(1.1);
            }
            .option.standard {
                background: #f8f8f8;
                color: #404040;
            }
            .score {
                font-size: 3em;
                font-weight: bold;
                margin: 20px 0;
            }
            h2 {
                margin: 0 0 20px 0;
                font-size: 1.8em;
            }
            .vs {
                font-size: 3em;
                color: #dc261e;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="comparison">
            <div class="option standard">
                <h2>Traditional Approach</h2>
                <div class="score">73%</div>
                <p>Manual processes<br/>Limited scalability<br/>Higher costs</p>
            </div>
            
            <div class="vs">VS</div>
            
            <div class="option winner">
                <h2>Ekona Solution</h2>
                <div class="score">96%</div>
                <p>AI-powered automation<br/>Infinite scalability<br/>
                Cost optimization</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Create slide with custom HTML
    slide_content = SlideContent(
        layout_index=2,
        content={
            "Title 1": "Solution Comparison",
            "Picture Placeholder 2": custom_html,
        },
    )

    presentation = slide_generator._create_powerpoint_presentation([slide_content])

    import os

    output_dir = "generated_presentations"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "custom_html_demo.pptx")
    presentation.save(output_path)
    print(f"✅ Saved custom HTML presentation: {output_path}")

    return output_path


def test_html_rendering_methods():
    """
    Test which HTML rendering methods are available
    """
    print("\n🔧 Testing HTML Rendering Methods...")

    from src.html_renderer import HTMLRenderer

    try:
        renderer = HTMLRenderer()
        print(f"✅ Active method: {renderer.active_method}")
        print("Available methods:")
        for method, available in renderer.available_methods.items():
            status = "✅" if available else "❌"
            print(f"  {status} {method}")
    except Exception as e:
        print(f"❌ HTML renderer initialization failed: {e}")


if __name__ == "__main__":
    print("🤖 HTML Visualization in PowerPoint - Demo Script")
    print("=" * 50)

    # Test available rendering methods
    test_html_rendering_methods()

    # Create timeline example
    try:
        timeline_output = create_timeline_slide_example()
        if timeline_output:
            print(f"\n📋 Open {timeline_output} to see the timeline visualization!")
    except Exception as e:
        print(f"❌ Timeline example failed: {e}")

    # Create custom HTML example
    try:
        custom_output = create_custom_html_slide()
        if custom_output:
            print(f"📋 Open {custom_output} to see the custom visualization!")
    except Exception as e:
        print(f"❌ Custom HTML example failed: {e}")

    print("\n🎯 How to Use HTML Visualizations:")
    print(
        "1. Install an HTML renderer: pip install playwright && "
        "playwright install chromium"
    )
    print(
        "2. Use keywords like 'timeline:', 'process:' in picture " "placeholder content"
    )
    print("3. Or provide direct HTML content for custom visualizations")
    print("4. The system will automatically render HTML as images in slides")

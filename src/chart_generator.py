"""
Chart Generator Module

This module creates actual PowerPoint charts using the python-pptx library
with ekona brand colors (red, dark grey, black, white + tonal variations).
"""

from typing import Any, Dict, List

from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches


class EkonaColors:
    """ekona brand color palette"""

    # Primary colors
    RED = RGBColor(220, 38, 30)  # ekona primary red
    DARK_GREY = RGBColor(64, 64, 64)  # ekona dark grey
    BLACK = RGBColor(0, 0, 0)  # black
    WHITE = RGBColor(255, 255, 255)  # white

    # Tonal variations
    LIGHT_RED = RGBColor(240, 100, 95)  # lighter red
    MEDIUM_RED = RGBColor(230, 69, 62)  # medium red
    LIGHT_GREY = RGBColor(128, 128, 128)  # light grey
    MEDIUM_GREY = RGBColor(96, 96, 96)  # medium grey
    OFF_WHITE = RGBColor(248, 248, 248)  # off white

    @classmethod
    def get_chart_colors(cls, count: int) -> List[RGBColor]:
        """
        Get a list of ekona brand colors for chart series

        Args:
            count: Number of colors needed

        Returns:
            List of RGBColor objects
        """
        base_colors = [
            cls.RED,
            cls.DARK_GREY,
            cls.MEDIUM_RED,
            cls.LIGHT_GREY,
            cls.LIGHT_RED,
            cls.MEDIUM_GREY,
            cls.BLACK,
        ]

        # Repeat colors if needed
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])

        return colors


class ChartGenerator:
    """Creates PowerPoint charts with ekona brand styling"""

    def __init__(self):
        """Initialize the chart generator"""
        self.ekona_colors = EkonaColors()

    def create_chart(self, placeholder, chart_data: Dict[str, Any]) -> bool:
        """
        Create a chart in the given placeholder

        Args:
            placeholder: PowerPoint chart placeholder
            chart_data: Dictionary containing chart specifications

        Returns:
            True if chart was created successfully, False otherwise
        """
        try:
            # Extract chart specifications
            chart_type = chart_data.get("type", "column").lower()
            chart_title = chart_data.get("title", "Chart")
            categories = chart_data.get("categories", [])
            series_data = chart_data.get("series", [])

            if not categories or not series_data:
                print("Warning: No chart data provided, skipping chart creation")
                return False

            # Map chart type to python-pptx type
            pptx_chart_type = self._get_chart_type(chart_type)

            # Create chart data
            chart_data_obj = CategoryChartData()
            chart_data_obj.categories = categories

            # Add series data
            for i, series in enumerate(series_data):
                series_name = series.get("name", f"Series {i+1}")
                series_values = series.get("values", [])
                chart_data_obj.add_series(series_name, series_values)

            # Create the chart
            graphic_frame = placeholder.insert_chart(pptx_chart_type, chart_data_obj)

            # Get the actual chart object from the graphic frame
            actual_chart = graphic_frame.chart

            # Apply ekona styling to the actual chart
            self._apply_ekona_styling(actual_chart, chart_title, len(series_data))

            print(f"Successfully created {chart_type} chart: {chart_title}")
            return True

        except Exception as e:
            print(f"Error creating chart: {e}")
            return False

    def _get_chart_type(self, chart_type: str) -> XL_CHART_TYPE:
        """
        Map string chart type to python-pptx chart type

        Args:
            chart_type: String representation of chart type

        Returns:
            XL_CHART_TYPE enum value
        """
        chart_types = {
            "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
            "bar": XL_CHART_TYPE.BAR_CLUSTERED,
            "line": XL_CHART_TYPE.LINE_MARKERS,
            "pie": XL_CHART_TYPE.PIE,
            "area": XL_CHART_TYPE.AREA,
            "scatter": XL_CHART_TYPE.XY_SCATTER,
            "doughnut": XL_CHART_TYPE.DOUGHNUT,
            "stacked_column": XL_CHART_TYPE.COLUMN_STACKED,
            "stacked_bar": XL_CHART_TYPE.BAR_STACKED,
        }

        return chart_types.get(chart_type, XL_CHART_TYPE.COLUMN_CLUSTERED)

    def _apply_ekona_styling(self, chart, title: str, series_count: int) -> None:
        """
        Apply ekona brand styling to chart

        Args:
            chart: PowerPoint chart object
            title: Chart title
            series_count: Number of data series
        """
        try:
            # Set chart title - handle different chart object types
            try:
                if hasattr(chart, "chart_title") and chart.chart_title:
                    chart_title_frame = chart.chart_title.text_frame
                    chart_title_frame.text = title
                    # Style title with ekona colors
                    title_font = chart_title_frame.paragraphs[0].font
                    title_font.color.rgb = self.ekona_colors.DARK_GREY
                    title_font.bold = True
                    title_font.size = Inches(0.2)  # 14pt
                elif hasattr(chart, "has_title") and chart.has_title:
                    chart.chart_title.text_frame.text = title
                    title_font = chart.chart_title.text_frame.paragraphs[0].font
                    title_font.color.rgb = self.ekona_colors.DARK_GREY
                    title_font.bold = True
                    title_font.size = Inches(0.2)  # 14pt
                else:
                    print(f"Chart title could not be set - chart type: {type(chart)}")
            except Exception as e:
                print(f"Warning: Could not set chart title: {e}")

            # Apply ekona colors to data series
            colors = self.ekona_colors.get_chart_colors(series_count)

            try:
                if hasattr(chart, "plots") and chart.plots:
                    for i, series in enumerate(chart.plots[0].series):
                        if i < len(colors):
                            try:
                                # CRITICAL: Set fill to solid BEFORE applying color
                                series.format.fill.solid()
                                series.format.fill.fore_color.rgb = colors[i]

                                # Set series border
                                series.format.line.color.rgb = (
                                    self.ekona_colors.DARK_GREY
                                )
                                series.format.line.width = Inches(0.01)  # 1pt

                                print(
                                    f"Applied ekona color to series {i+1}: {colors[i]}"
                                )

                            except Exception as e:
                                print(
                                    f"Warning: Could not apply color to series {i+1}: {e}"
                                )
                else:
                    print("Warning: Chart has no plots or series to style")
            except Exception as e:
                print(f"Warning: Could not style chart series: {e}")

            # Style axes
            self._style_chart_axes(chart)

            # Style legend
            try:
                if hasattr(chart, "has_legend") and chart.has_legend:
                    legend_font = chart.legend.font
                    legend_font.color.rgb = self.ekona_colors.DARK_GREY
                    legend_font.size = Inches(0.15)  # 11pt
            except Exception as e:
                print(f"Warning: Could not style legend: {e}")

        except Exception as e:
            print(f"Warning: Could not apply full styling to chart: {e}")

    def _style_chart_axes(self, chart) -> None:
        """
        Style chart axes with ekona colors

        Args:
            chart: PowerPoint chart object
        """
        try:
            # Style category axis (X-axis)
            if hasattr(chart, "category_axis"):
                cat_axis = chart.category_axis
                if hasattr(cat_axis, "tick_labels"):
                    cat_axis.tick_labels.font.color.rgb = self.ekona_colors.DARK_GREY
                    cat_axis.tick_labels.font.size = Inches(0.12)  # 9pt

                # Axis line color
                if hasattr(cat_axis, "format"):
                    cat_axis.format.line.color.rgb = self.ekona_colors.MEDIUM_GREY

            # Style value axis (Y-axis)
            if hasattr(chart, "value_axis"):
                val_axis = chart.value_axis
                if hasattr(val_axis, "tick_labels"):
                    val_axis.tick_labels.font.color.rgb = self.ekona_colors.DARK_GREY
                    val_axis.tick_labels.font.size = Inches(0.12)  # 9pt

                # Axis line color
                if hasattr(val_axis, "format"):
                    val_axis.format.line.color.rgb = self.ekona_colors.MEDIUM_GREY

        except Exception as e:
            print(f"Warning: Could not style chart axes: {e}")

    def create_sample_chart_data(
        self, chart_purpose: str, topic: str
    ) -> Dict[str, Any]:
        """
        Create sample chart data for testing

        Args:
            chart_purpose: Purpose of the chart (e.g., "growth", "comparison")
            topic: Presentation topic for context

        Returns:
            Dictionary with sample chart data
        """
        sample_data = {
            "type": "column",
            "title": f"{topic} - Data Visualization",
            "categories": ["Q1", "Q2", "Q3", "Q4"],
            "series": [
                {"name": "Growth", "values": [10, 25, 40, 55]},
                {"name": "Target", "values": [15, 30, 45, 60]},
            ],
        }

        return sample_data

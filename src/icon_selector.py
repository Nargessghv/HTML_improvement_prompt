"""
Icon Selector Module

This module integrates with LLM to intelligently select appropriate icons
for slide content, particularly for layout 8 (icon + text layout).
"""

from typing import Dict, List, Optional

from .icon_manager import IconManager
from .llm_client import LLMClient


class IconSelector:
    """Intelligently selects icons for slide content using LLM"""

    def __init__(
        self,
        icon_manager: Optional[IconManager] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize IconSelector

        Args:
            icon_manager: IconManager instance (will create if not provided)
            llm_client: LLMClient instance (will create if not provided)
        """
        self.icon_manager = icon_manager or IconManager()
        self.llm_client = llm_client or LLMClient()

    def select_icons_for_content(
        self, slide_content: Dict[str, str], topic: str
    ) -> Dict[str, str]:
        """
        Select appropriate icons for slide content

        Args:
            slide_content: Dictionary mapping placeholder names to content
            topic: Overall presentation topic for context

        Returns:
            Dictionary mapping icon placeholder names to selected icon names
        """
        # Extract text content from icon-related placeholders
        icon_selections = {}
        text_content = []

        # Find text placeholders that correspond to icons
        for placeholder_name, content in slide_content.items():
            if "text beside icon" in placeholder_name.lower():
                text_content.append(content)

        if not text_content:
            # Fallback: use general topic-based icons
            return self._get_fallback_icons(slide_content, topic)

        # Use LLM to select appropriate icons
        selected_icons = self._llm_select_icons(text_content, topic)

        # Map selected icons to icon placeholders
        icon_placeholder_names = [
            name
            for name in slide_content
            if "icon" in name.lower() and "text" not in name.lower()
        ]

        for i, placeholder_name in enumerate(icon_placeholder_names):
            if i < len(selected_icons):
                icon_selections[placeholder_name] = selected_icons[i]
            else:
                # Fallback to default icons if we don't have enough
                fallback_icons = ["target", "users", "lightbulb", "check"]
                icon_selections[placeholder_name] = fallback_icons[
                    i % len(fallback_icons)
                ]

        return icon_selections

    def _llm_select_icons(self, text_content: List[str], topic: str) -> List[str]:
        """
        Use LLM to select appropriate icons for given text content

        Args:
            text_content: List of text content for each icon
            topic: Overall presentation topic

        Returns:
            List of selected icon names
        """
        # Get available icon categories and suggestions
        available_categories = list(
            self.icon_manager.icons_database.get("categories", {}).keys()
        )

        # Create suggestions for each text content
        all_suggestions = []
        for text in text_content:
            suggestions = self.icon_manager.get_icon_suggestions(text)
            all_suggestions.extend(suggestions)

        # Remove duplicates while preserving order
        unique_suggestions = list(dict.fromkeys(all_suggestions))

        # Create LLM prompt for icon selection
        prompt = self._create_icon_selection_prompt(
            text_content, topic, unique_suggestions, available_categories
        )

        try:
            # Get icon selections from LLM
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_icon_selection_system_prompt(),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                temperature=0.1,
            )

            content = response.choices[0].message.content
            response_text = content.strip() if content else ""

            # Parse the response to extract icon names
            selected_icons = self._parse_icon_selection_response(response_text)

            # Validate that selected icons exist
            validated_icons = []
            for icon_name in selected_icons:
                if icon_name in self.icon_manager.icons_database.get("all_icons", []):
                    validated_icons.append(icon_name)
                else:
                    # Find similar icon if exact match not found
                    similar_icon = self._find_similar_icon(icon_name)
                    if similar_icon:
                        validated_icons.append(similar_icon)
                    else:
                        # Fallback to content-based suggestion
                        suggestion = self.icon_manager.get_icon_suggestions(
                            text_content[len(validated_icons)]
                            if len(validated_icons) < len(text_content)
                            else "general"
                        )
                        if suggestion:
                            validated_icons.append(suggestion[0])
                        else:
                            validated_icons.append("circle")  # Ultimate fallback

            return validated_icons[
                : len(text_content)
            ]  # Return exactly the number needed

        except Exception as e:
            print(f"Error in LLM icon selection: {e}")
            return self._get_content_based_icons(text_content)

    def _create_icon_selection_prompt(
        self,
        text_content: List[str],
        topic: str,
        suggestions: List[str],
        categories: List[str],
    ) -> str:
        """
        Create prompt for LLM icon selection

        Args:
            text_content: List of text content for each icon
            topic: Overall presentation topic
            suggestions: Suggested icon names
            categories: Available icon categories

        Returns:
            Formatted prompt string
        """
        text_list = "\n".join(
            [f"Text {i+1}: {text}" for i, text in enumerate(text_content)]
        )
        suggestions_text = ", ".join(suggestions[:20])  # Limit to first 20 suggestions

        return f"""
Topic: {topic}

Select the most appropriate icons for these text items:
{text_list}

Available icon suggestions: {suggestions_text}

🚨 CRITICAL REQUIREMENT: Use ONLY lucide-static icon names that exist 
in the library. You have knowledge of lucide-static icons - only use names 
from that library.

VALID lucide-static examples: users, trending-up, lightbulb, check-circle, 
arrow-right, bar-chart, settings, heart, star, target, zap, shield, 
clock, mail, phone, database, cpu, server, code, search, eye, etc.

INVALID examples (DO NOT USE): money, tools, time, exclamation

Instructions:
1. Choose icons that best represent the meaning/concept of each text
2. Consider the overall topic: {topic}
3. Prefer simple, clear, professional icons
4. Return ONLY the icon names, one per line
5. Return exactly {len(text_content)} icon names
6. Use hyphens for multi-word icon names (e.g., "bar-chart" not "bar chart")
7. 🚨 ONLY use icon names that exist in lucide-static library

Example response:
trending-up
users
lightbulb
"""

    def _get_icon_selection_system_prompt(self) -> str:
        """
        Get system prompt for icon selection

        Returns:
            System prompt string
        """
        return """You are an expert UI/UX designer specializing in icon selection 
for business presentations. Your task is to select the most appropriate and 
visually coherent icons that best represent the given text content.

🚨 CRITICAL: You must ONLY use icon names from the lucide-static library. 
You have knowledge of this library - stick to icons that actually exist in 
lucide-static.

VALID lucide-static icons include: users, trending-up, lightbulb, 
check-circle, arrow-right, bar-chart, settings, heart, star, target, zap, 
shield, clock, mail, phone, database, cpu, server, code, search, eye, 
activity, gauge, grid, layers, link, share, etc.

DO NOT use icons like: money, tools, time, exclamation (these don't exist 
in lucide-static)

Consider:
- Semantic meaning of the text
- Professional business context
- Visual clarity and recognition
- Consistency across selections
- Modern design principles

Always respond with simple icon names using hyphens for spaces 
(e.g., "check-circle", "trending-up", "user-check")."""

    def _parse_icon_selection_response(self, response_text: str) -> List[str]:
        """
        Parse LLM response to extract icon names

        Args:
            response_text: Raw LLM response

        Returns:
            List of icon names
        """
        lines = response_text.strip().split("\n")
        icon_names = []

        for line in lines:
            line = line.strip()
            # Remove numbers, bullets, and other formatting
            if line and not line.startswith("#"):
                # Extract just the icon name
                parts = line.split()
                if parts:
                    # Take the last part which should be the icon name
                    icon_name = parts[-1].lower()
                    # Clean up the icon name
                    icon_name = (
                        icon_name.replace(":", "").replace(",", "").replace(".", "")
                    )
                    if icon_name and icon_name not in ["icon", "name"]:
                        icon_names.append(icon_name)

        return icon_names

    def _find_similar_icon(self, target_icon: str) -> Optional[str]:
        """
        Find similar icon if exact match not found

        Args:
            target_icon: Target icon name to find similar match for

        Returns:
            Similar icon name or None if not found
        """
        all_icons = self.icon_manager.icons_database.get("all_icons", [])
        target_lower = target_icon.lower().replace("-", "").replace("_", "")

        # Look for partial matches
        for icon_name in all_icons:
            icon_lower = icon_name.lower().replace("-", "").replace("_", "")
            if target_lower in icon_lower or icon_lower in target_lower:
                return icon_name

        return None

    def _get_content_based_icons(self, text_content: List[str]) -> List[str]:
        """
        Get icons based on content analysis (fallback method)

        Args:
            text_content: List of text content

        Returns:
            List of suggested icon names
        """
        icons = []
        for text in text_content:
            suggestions = self.icon_manager.get_icon_suggestions(text)
            if suggestions:
                icons.append(suggestions[0])
            else:
                icons.append("circle")  # Ultimate fallback

        return icons

    def _get_fallback_icons(
        self, slide_content: Dict[str, str], topic: str
    ) -> Dict[str, str]:
        """
        Get fallback icons when no specific content is available

        Args:
            slide_content: Slide content dictionary
            topic: Presentation topic

        Returns:
            Dictionary mapping icon placeholders to icon names
        """
        # Default business presentation icons
        default_icons = [
            "target",
            "trending-up",
            "users",
            "lightbulb",
            "check",
            "star",
            "zap",
            "briefcase",
        ]

        icon_selections = {}
        icon_placeholder_names = [
            name
            for name in slide_content
            if "icon" in name.lower() and "text" not in name.lower()
        ]

        for i, placeholder_name in enumerate(icon_placeholder_names):
            icon_selections[placeholder_name] = default_icons[i % len(default_icons)]

        return icon_selections

    def prepare_icons_for_slide(
        self, icon_selections: Dict[str, str], size: int = 128
    ) -> Dict[str, Optional[str]]:
        """
        Prepare selected icons for slide insertion

        Args:
            icon_selections: Dictionary mapping placeholder names to icon names
            size: Icon size in pixels

        Returns:
            Dictionary mapping placeholder names to PNG file paths
        """
        prepared_icons = {}

        for placeholder_name, icon_name in icon_selections.items():
            # Prepare the icon (convert to PNG if needed)
            icon_path = self.icon_manager.prepare_icon(icon_name, size)
            prepared_icons[placeholder_name] = icon_path

            if icon_path:
                print(f"✅ Prepared icon '{icon_name}' for '{placeholder_name}'")
            else:
                print(
                    f"⚠️ Failed to prepare icon '{icon_name}' for '{placeholder_name}'"
                )

        return prepared_icons

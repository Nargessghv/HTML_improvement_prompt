"""
Icon Manager Module

This module handles icon selection, conversion, and caching for PowerPoint slides.
It converts Lucide SVG icons to PNG format with Swiss red color.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import for SVG to PNG conversion
try:
    import cairosvg

    CONVERSION_AVAILABLE = True
except ImportError:
    CONVERSION_AVAILABLE = False
    print("Warning: cairosvg not available. Icon conversion disabled.")


class IconManager:
    """Manages icon selection, conversion, and caching"""

    # Swiss red color (ekona brand color)
    SWISS_RED = "#E53E3E"  # Standard Swiss red

    def __init__(
        self,
        icons_source_dir: str = "./node_modules/lucide-static/icons",
        cache_dir: str = "./icon_cache",
    ):
        """
        Initialize IconManager

        Args:
            icons_source_dir: Directory containing source SVG icons
            cache_dir: Directory for cached PNG icons
        """
        self.icons_source_dir = Path(icons_source_dir)
        self.cache_dir = Path(cache_dir)
        self.icons_db_path = self.cache_dir / "icons_database.json"

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)

        # Initialize or load icon database
        self.icons_database = self._load_or_create_database()

    def _load_or_create_database(self) -> Dict[str, Any]:
        """
        Load existing icon database or create a new one

        Returns:
            Dictionary containing categorized icon information
        """
        if self.icons_db_path.exists():
            try:
                with open(self.icons_db_path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                print("Warning: Corrupted icon database. Creating new one.")

        # Create new database by scanning available icons
        return self._create_icon_database()

    def _create_icon_database(self) -> Dict[str, Any]:
        """
        Create categorized database of available icons

        Returns:
            Dictionary with categorized icon information
        """
        print("Creating icon database from Lucide icons...")

        if not self.icons_source_dir.exists():
            print(f"Warning: Icons source directory not found: {self.icons_source_dir}")
            return {"categories": {}, "all_icons": []}

        # Get all SVG files
        svg_files = list(self.icons_source_dir.glob("*.svg"))
        all_icons = [f.stem for f in svg_files]

        # Categorize icons by keywords
        categories = {
            "business": [],
            "technology": [],
            "communication": [],
            "data": [],
            "ui_elements": [],
            "arrows": [],
            "social": [],
            "finance": [],
            "general": [],
        }

        # Define keyword mappings for categories
        category_keywords = {
            "business": [
                "briefcase",
                "building",
                "chart",
                "graph",
                "presentation",
                "target",
                "trending",
                "users",
                "team",
                "office",
            ],
            "technology": [
                "cpu",
                "database",
                "server",
                "code",
                "robot",
                "computer",
                "settings",
                "gear",
                "tool",
                "wrench",
                "monitor",
            ],
            "communication": [
                "message",
                "mail",
                "phone",
                "chat",
                "speak",
                "voice",
                "megaphone",
                "bell",
                "notification",
            ],
            "data": [
                "bar-chart",
                "pie-chart",
                "analytics",
                "stats",
                "graph",
                "trend",
                "file",
                "folder",
                "document",
            ],
            "ui_elements": [
                "check",
                "x",
                "plus",
                "minus",
                "star",
                "heart",
                "thumb",
                "eye",
                "edit",
                "trash",
                "download",
            ],
            "arrows": ["arrow", "chevron", "triangle", "move", "corner", "expand"],
            "social": ["share", "link", "globe", "network", "users", "person"],
            "finance": [
                "dollar",
                "euro",
                "pound",
                "credit-card",
                "bank",
                "coin",
                "wallet",
                "payment",
            ],
        }

        # Categorize each icon
        for icon_name in all_icons:
            categorized = False
            for category, keywords in category_keywords.items():
                if any(keyword in icon_name for keyword in keywords):
                    categories[category].append(icon_name)
                    categorized = True
                    break

            if not categorized:
                categories["general"].append(icon_name)

        database = {
            "categories": categories,
            "all_icons": all_icons,
            "total_count": len(all_icons),
            "created_at": str(Path().absolute()),
        }

        # Save database
        try:
            with open(self.icons_db_path, "w") as f:
                json.dump(database, f, indent=2)
            print(f"✅ Icon database created with {len(all_icons)} icons")
        except OSError as e:
            print(f"Warning: Could not save icon database: {e}")

        return database

    def get_icons_by_category(self, category: str) -> List[str]:
        """
        Get icons in a specific category

        Args:
            category: Category name

        Returns:
            List of icon names in the category
        """
        return self.icons_database.get("categories", {}).get(category, [])

    def search_icons(self, keywords: List[str], limit: int = 10) -> List[str]:
        """
        Search for icons by keywords

        Args:
            keywords: List of keywords to search for
            limit: Maximum number of icons to return

        Returns:
            List of matching icon names
        """
        all_icons = self.icons_database.get("all_icons", [])
        matches = []

        for icon_name in all_icons:
            # Check if any keyword matches the icon name
            if any(keyword.lower() in icon_name.lower() for keyword in keywords):
                matches.append(icon_name)
                if len(matches) >= limit:
                    break

        return matches

    def convert_svg_to_png(self, icon_name: str, size: int = 64) -> Optional[str]:
        """
        Convert SVG icon to PNG with Swiss red color

        Args:
            icon_name: Name of the icon (without .svg extension)
            size: Output size in pixels

        Returns:
            Path to converted PNG file or None if conversion failed
        """
        if not CONVERSION_AVAILABLE:
            print("Icon conversion not available. Please install cairosvg and Pillow.")
            return None

        svg_path = self.icons_source_dir / f"{icon_name}.svg"
        png_path = self.cache_dir / f"{icon_name}_{size}px_red.png"

        # Return cached version if it exists
        if png_path.exists():
            return str(png_path)

        if not svg_path.exists():
            print(f"Warning: SVG icon not found: {svg_path}")
            return None

        try:
            # Read SVG content
            with open(svg_path) as f:
                svg_content = f.read()

            # Replace color with Swiss red
            # Lucide icons typically use currentColor or black
            svg_content = svg_content.replace("currentColor", self.SWISS_RED)
            svg_content = svg_content.replace("#000000", self.SWISS_RED)
            svg_content = svg_content.replace("#000", self.SWISS_RED)
            svg_content = svg_content.replace("black", self.SWISS_RED)

            # Convert SVG to PNG
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode("utf-8"),
                output_width=size,
                output_height=size,
            )

            # Save PNG file
            with open(png_path, "wb") as f:
                f.write(png_data)

            print(f"✅ Converted {icon_name} to PNG ({size}px)")
            return str(png_path)

        except Exception as e:
            print(f"Error converting {icon_name}: {e}")
            return None

    def get_icon_suggestions(
        self, content_text: str, category_hint: Optional[str] = None
    ) -> List[str]:
        """
        Get icon suggestions based on content text

        Args:
            content_text: Text content to analyze for icon suggestions
            category_hint: Optional category hint

        Returns:
            List of suggested icon names
        """
        # Define content-to-icon mappings
        content_mappings = {
            "data": ["bar-chart", "pie-chart", "trending-up", "database"],
            "analytics": ["bar-chart", "line-chart", "trending-up", "activity"],
            "growth": ["trending-up", "arrow-up", "target", "zap"],
            "users": ["users", "user", "team", "people"],
            "technology": ["cpu", "server", "code", "settings"],
            "communication": ["message-circle", "mail", "phone", "megaphone"],
            "security": ["shield", "lock", "key", "eye"],
            "performance": ["zap", "trending-up", "activity", "gauge"],
            "innovation": ["lightbulb", "rocket", "star", "sparkles"],
            "efficiency": ["clock", "zap", "check-circle", "target"],
            "collaboration": ["users", "handshake", "share", "link"],
            "insights": ["eye", "search", "brain", "lightbulb"],
            "automation": ["robot", "settings", "gear", "cpu"],
            "integration": ["link", "puzzle", "grid", "layers"],
        }

        suggestions = []

        # Look for direct keyword matches
        for keyword, icons in content_mappings.items():
            if keyword in content_text.lower():
                suggestions.extend(icons[:2])  # Take top 2 icons per keyword

        # If category hint provided, add icons from that category
        if category_hint and category_hint in self.icons_database.get("categories", {}):
            category_icons = self.get_icons_by_category(category_hint)
            suggestions.extend(category_icons[:3])  # Add top 3 from category

        # Remove duplicates and limit results
        unique_suggestions = list(dict.fromkeys(suggestions))[:8]

        # If no suggestions found, provide some general business icons
        if not unique_suggestions:
            unique_suggestions = [
                "target",
                "trending-up",
                "users",
                "lightbulb",
                "check",
                "star",
                "zap",
                "briefcase",
            ]

        return unique_suggestions

    def get_cached_icon_path(self, icon_name: str, size: int = 64) -> Optional[str]:
        """
        Get path to cached PNG icon

        Args:
            icon_name: Name of the icon
            size: Size in pixels

        Returns:
            Path to cached PNG or None if not cached
        """
        png_path = self.cache_dir / f"{icon_name}_{size}px_red.png"
        return str(png_path) if png_path.exists() else None

    def prepare_icon(self, icon_name: str, size: int = 64) -> Optional[str]:
        """
        Prepare an icon for use (convert if needed, return cached path)

        Args:
            icon_name: Name of the icon
            size: Size in pixels

        Returns:
            Path to ready-to-use PNG icon
        """
        # Check if already cached
        cached_path = self.get_cached_icon_path(icon_name, size)
        if cached_path:
            return cached_path

        # Convert and cache
        return self.convert_svg_to_png(icon_name, size)

    def cleanup_cache(self, keep_recent_days: int = 30) -> None:
        """
        Clean up old cached icons

        Args:
            keep_recent_days: Keep icons modified within this many days
        """
        import time

        current_time = time.time()
        cutoff_time = current_time - (keep_recent_days * 24 * 60 * 60)

        for png_file in self.cache_dir.glob("*.png"):
            if png_file.stat().st_mtime < cutoff_time:
                try:
                    png_file.unlink()
                    print(f"Cleaned up old icon: {png_file.name}")
                except OSError:
                    pass  # Ignore errors during cleanup

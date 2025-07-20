"""
Configuration Module

Centralized configuration management for agent-based slide generation
with support for environment variables and validation.
"""

import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class LLMConfig:
    """Configuration for LLM settings"""

    model: str = "gpt-4o"
    max_tokens: int = 50000
    temperature: float = 0.1
    api_key: Optional[str] = None

    def __post_init__(self):
        """Validate and set defaults"""
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")

        # Override with environment variables if available
        self.model = os.getenv("OPENAI_MODEL", self.model)
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(self.max_tokens)))
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", str(self.temperature)))


@dataclass
class MonitoringConfig:
    """Configuration for Langfuse monitoring"""

    enabled: bool = True
    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    host: str = "https://cloud.langfuse.com"

    def __post_init__(self):
        """Validate and set defaults"""
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        self.host = os.getenv("LANGFUSE_HOST", self.host)

        # Disable monitoring if keys are missing
        if not self.public_key or not self.secret_key:
            self.enabled = False


@dataclass
class AgentConfig:
    """Configuration for agent behavior"""

    enable_quality_review: bool = True
    max_retries: int = 3
    enable_parallel_processing: bool = False
    content_validation: bool = True

    def __post_init__(self):
        """Load from environment variables"""
        self.enable_quality_review = (
            os.getenv("AGENT_QUALITY_REVIEW", "true").lower() == "true"
        )
        self.max_retries = int(os.getenv("AGENT_MAX_RETRIES", str(self.max_retries)))
        self.enable_parallel_processing = (
            os.getenv("AGENT_PARALLEL", "false").lower() == "true"
        )
        self.content_validation = (
            os.getenv("AGENT_VALIDATION", "true").lower() == "true"
        )


@dataclass
class SlideGenerationConfig:
    """Main configuration for slide generation workflow"""

    llm: LLMConfig
    monitoring: MonitoringConfig
    agents: AgentConfig
    default_template: str = "ekona_slides_template_new.pptx"
    output_directory: str = "generated_presentations"

    def __post_init__(self):
        """Set defaults from environment"""
        self.default_template = os.getenv("DEFAULT_TEMPLATE", self.default_template)
        self.output_directory = os.getenv("OUTPUT_DIRECTORY", self.output_directory)


def get_config() -> SlideGenerationConfig:
    """
    Get the current configuration with all settings loaded

    Returns:
        Complete configuration object
    """
    return SlideGenerationConfig(
        llm=LLMConfig(), monitoring=MonitoringConfig(), agents=AgentConfig()
    )


def validate_config(config: SlideGenerationConfig) -> List[str]:
    """
    Validate configuration and return list of warnings/errors

    Args:
        config: Configuration to validate

    Returns:
        List of validation messages
    """
    messages = []

    # Check LLM configuration
    if not config.llm.api_key:
        messages.append("❌ OPENAI_API_KEY is required but not set")

    # Check monitoring configuration
    if not config.monitoring.enabled:
        messages.append("⚠️  Langfuse monitoring disabled (missing API keys)")
    else:
        messages.append("✅ Langfuse monitoring enabled")

    # Check template file
    if not os.path.exists(config.default_template):
        messages.append(f"⚠️  Default template not found: {config.default_template}")

    # Check output directory
    if not os.path.exists(config.output_directory):
        messages.append(
            f"📁 Output directory will be created: {config.output_directory}"
        )

    return messages


def print_config_status():
    """Print current configuration status for debugging"""
    config = get_config()
    messages = validate_config(config)

    print("🔧 Configuration Status:")
    print("=" * 40)

    print(f"🤖 LLM Model: {config.llm.model}")
    print(f"🎯 Max Tokens: {config.llm.max_tokens}")
    print(f"🌡️  Temperature: {config.llm.temperature}")

    print(f"\n📊 Monitoring: {'Enabled' if config.monitoring.enabled else 'Disabled'}")
    if config.monitoring.enabled:
        print(f"🔗 Host: {config.monitoring.host}")

    print("\n🤖 Agents:")
    quality_status = "Enabled" if config.agents.enable_quality_review else "Disabled"
    print(f"   Quality Review: {quality_status}")
    print(f"   Max Retries: {config.agents.max_retries}")
    parallel_status = (
        "Enabled" if config.agents.enable_parallel_processing else "Disabled"
    )
    print(f"   Parallel Processing: {parallel_status}")

    print("\n📁 Paths:")
    print(f"   Template: {config.default_template}")
    print(f"   Output: {config.output_directory}")

    print("\n📋 Validation:")
    for message in messages:
        print(f"   {message}")


def create_env_template():
    """Create a .env template file with all configuration options"""
    template_content = """# PowerPoint Slide Generator Configuration

# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_FAST=gpt-4o-mini
OPENAI_MAX_TOKENS=10000
OPENAI_TEMPERATURE=0.1

# Langfuse Monitoring (Optional but recommended)
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com

# Agent Configuration
AGENT_QUALITY_REVIEW=true
AGENT_MAX_RETRIES=3
AGENT_PARALLEL=false
AGENT_VALIDATION=true

# File Paths
DEFAULT_TEMPLATE=ekona_slides_template_new.pptx
OUTPUT_DIRECTORY=generated_presentations

# HTML Debug Configuration
# Set to 'true' to save generated HTML files for debugging/comparison
HTML_DEBUG=true

# Note: Copy this to .env and fill in your actual API keys
# OPENAI_MODEL: Main model for content generation
# OPENAI_MODEL_FAST: Fast model for simple tasks like icons
"""

    with open(".env.template", "w") as f:
        f.write(template_content)

    print("📄 Created .env.template with configuration options")
    print("💡 Copy to .env and add your API keys to get started")


if __name__ == "__main__":
    # Print configuration status when run directly
    print_config_status()
    print("\n" + "=" * 40)
    create_env_template()

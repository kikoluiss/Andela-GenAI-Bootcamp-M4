"""
Configuration constants and environment setup.
"""
import os

from dotenv import load_dotenv

# Load environment variables once at module import
load_dotenv()

# Default model name used across the application
DEFAULT_MODEL = "gpt-4.1-mini"

# Langfuse configuration
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")


"""
API Configuration - Re-exports from shared config module.

This module maintains backward compatibility for existing imports:
    from .config import settings
    from .config import Settings, get_settings

All configuration is now managed in the shared.config module.
"""

import sys
from pathlib import Path

# Add project root to path so we can import shared module
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Re-export from shared config
from shared.config import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]

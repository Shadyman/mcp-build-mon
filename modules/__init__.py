"""
Build Monitor Modules - Self-Documenting Feature Components

This package contains the modularized feature components of the MCP Build Monitor Server.
Each module is self-documenting with help_data, examples, and AI integration metadata.
"""

# Import all components for easy access
from .resource_monitor import ResourceMonitor
from .build_tracker import IncrementalBuildTracker
from .build_history import BuildHistoryManager
from .dependency_tracker import DependencyTracker
from .health_tracker import HealthScoreTracker
from .build_session import BuildSession
from .fix_suggestions import FixSuggestionsDatabase

# Optional build context module
try:
    from .build_context import BuildContextPreserver
    __all__ = [
        'ResourceMonitor',
        'IncrementalBuildTracker', 
        'BuildHistoryManager',
        'DependencyTracker',
        'HealthScoreTracker',
        'BuildSession',
        'FixSuggestionsDatabase',
        'BuildContextPreserver'
    ]
except ImportError:
    __all__ = [
        'ResourceMonitor',
        'IncrementalBuildTracker', 
        'BuildHistoryManager',
        'DependencyTracker',
        'HealthScoreTracker',
        'BuildSession',
        'FixSuggestionsDatabase'
    ]
#!/usr/bin/env python3
"""
BuildMon - Main Controller and AI Metadata Aggregator

This module serves as the central controller for the MCP Build Monitor system,
providing unified access to all feature modules and serving as the single source
of truth for AI assistant integration.
"""

import json
import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Import all feature modules (handle both package and standalone usage)
try:
    from .modules import (
        ResourceMonitor,
        IncrementalBuildTracker,
        BuildHistoryManager,
        DependencyTracker,
        HealthScoreTracker,
        BuildSession,
        FixSuggestionsDatabase
    )
    try:
        from .modules.build_context import BuildContextPreserver
        HAS_BUILD_CONTEXT = True
    except ImportError:
        HAS_BUILD_CONTEXT = False
except ImportError:
    # Standalone usage
    from modules import (
        ResourceMonitor,
        IncrementalBuildTracker,
        BuildHistoryManager,
        DependencyTracker,
        HealthScoreTracker,
        BuildSession,
        FixSuggestionsDatabase
    )
    try:
        from modules.build_context import BuildContextPreserver
        HAS_BUILD_CONTEXT = True
    except ImportError:
        HAS_BUILD_CONTEXT = False


class BuildMonManager:
    """
    Main controller for the MCP Build Monitor system.
    
    Provides:
    - Module discovery and management
    - Configuration loading/saving
    - Help system coordination
    - AI metadata aggregation
    - CLI interface coordination
    """
    
    def __init__(self, config_file: str = None, project_root: str = None):
        """Initialize the BuildMon manager.
        
        Args:
            config_file: Path to configuration file. If None, uses default location.
            project_root: Path to project root directory. If None, uses current working directory.
        """
        if config_file is None:
            config_file = Path(__file__).parent / "settings.json"
        
        if project_root is None:
            project_root = os.getcwd()
        
        self.config_file = Path(config_file)
        self.project_root = Path(project_root)
        self.config = self._load_config()
        self.modules = self._initialize_modules()
        self.version = "1.0.0"
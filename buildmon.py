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
    
    def __init__(self, config_file: str = None):
        """Initialize the BuildMon manager.
        
        Args:
            config_file: Path to configuration file. If None, uses default location.
        """
        if config_file is None:
            config_file = Path(__file__).parent / "settings.json"
        
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.modules = self._initialize_modules()
        self.version = "1.0.0"
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from settings.json."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Return default configuration
            default_config = {
                "version": "1.0.0",
                "modules": {
                    "resource_monitor": {"enabled": True},
                    "build_tracker": {"enabled": True}, 
                    "build_history": {"enabled": True},
                    "dependency_tracker": {"enabled": True},
                    "health_tracker": {"enabled": True},
                    "fix_suggestions": {"enabled": True}
                }
            }
            if HAS_BUILD_CONTEXT:
                default_config["modules"]["build_context"] = {"enabled": True}
            
            # Save default config
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to settings.json."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save configuration: {e}")
    
    def _initialize_modules(self) -> Dict[str, Any]:
        """Initialize all available modules based on configuration."""
        modules = {}
        
        # Core modules mapping
        module_classes = {
            "resource_monitor": ResourceMonitor,
            "build_tracker": IncrementalBuildTracker,
            "build_history": BuildHistoryManager,
            "dependency_tracker": DependencyTracker,
            "health_tracker": HealthScoreTracker,
            "fix_suggestions": FixSuggestionsDatabase
        }
        
        # Add build context if available
        if HAS_BUILD_CONTEXT:
            module_classes["build_context"] = BuildContextPreserver
        
        # Initialize enabled modules
        for module_name, module_class in module_classes.items():
            if self.config["modules"].get(module_name, {}).get("enabled", True):
                try:
                    modules[module_name] = {
                        "instance": module_class(),
                        "class": module_class,
                        "enabled": True
                    }
                except Exception as e:
                    print(f"Warning: Could not initialize {module_name}: {e}")
                    modules[module_name] = {
                        "instance": None,
                        "class": module_class,
                        "enabled": False,
                        "error": str(e)
                    }
            else:
                modules[module_name] = {
                    "instance": None,
                    "class": module_class,
                    "enabled": False
                }
        
        return modules
    
    def get_ai_metadata(self) -> Dict[str, Any]:
        """
        Get comprehensive AI assistant integration metadata.
        
        This is the single source of truth for AI assistants to understand
        the complete build monitoring system capabilities.
        
        Returns:
            Complete metadata structure for AI assistant integration
        """
        enabled_modules = [name for name, mod in self.modules.items() 
                          if mod.get("enabled", False)]
        
        metadata = {
            "system_info": {
                "name": "MCP Build Monitor",
                "version": self.version,
                "enabled_modules": enabled_modules,
                "total_modules": len(self.modules),
                "configuration_file": str(self.config_file)
            },
            "modules": {},
            "workflows": self._generate_ai_workflows(),
            "troubleshooting": self._aggregate_troubleshooting(),
            "token_efficiency": self._calculate_token_metrics()
        }
        
        # Aggregate help_data from all enabled modules
        for name, module_info in self.modules.items():
            if module_info.get("enabled") and module_info.get("instance"):
                instance = module_info["instance"]
                if hasattr(instance, 'help_data'):
                    metadata["modules"][name] = instance.help_data
                else:
                    # Fallback metadata for modules without help_data
                    metadata["modules"][name] = {
                        "name": module_info["class"].__name__,
                        "description": "Feature module (metadata not available)",
                        "enabled": True
                    }
        
        return metadata
    
    def get_module_help(self, module_name: str) -> Dict[str, Any]:
        """Get detailed help for specific module.
        
        Args:
            module_name: Name of module to get help for
            
        Returns:
            Module help data or error message
        """
        if module_name not in self.modules:
            return {"error": f"Module '{module_name}' not found"}
        
        module_info = self.modules[module_name]
        if not module_info.get("enabled"):
            return {
                "error": f"Module '{module_name}' is disabled",
                "help": "Use --enable-tool to enable this module"
            }
        
        instance = module_info.get("instance")
        if instance and hasattr(instance, 'help_data'):
            return instance.help_data
        
        # Fallback help
        return {
            "name": module_info["class"].__name__,
            "description": "Help data not available for this module",
            "class": module_info["class"].__name__
        }
    
    def list_modules(self, include_disabled: bool = True) -> Dict[str, Any]:
        """List all modules with their status.
        
        Args:
            include_disabled: Whether to include disabled modules
            
        Returns:
            Dictionary of modules with status information
        """
        result = {}
        
        for name, module_info in self.modules.items():
            if not include_disabled and not module_info.get("enabled"):
                continue
                
            status_info = {
                "enabled": module_info.get("enabled", False),
                "class": module_info["class"].__name__,
                "initialized": module_info.get("instance") is not None
            }
            
            if module_info.get("error"):
                status_info["error"] = module_info["error"]
            
            # Add basic info from help_data if available
            instance = module_info.get("instance")
            if instance and hasattr(instance, 'help_data'):
                help_data = instance.help_data
                status_info.update({
                    "name": help_data.get("name", "Unknown"),
                    "description": help_data.get("description", "No description"),
                    "features": help_data.get("features", [])
                })
            
            result[name] = status_info
        
        return result
    
    def enable_module(self, module_name: str) -> Tuple[bool, str]:
        """Enable a module.
        
        Args:
            module_name: Name of module to enable
            
        Returns:
            (success, message) tuple
        """
        if module_name not in self.modules:
            return False, f"Module '{module_name}' not found"
        
        # Update configuration
        self.config["modules"][module_name]["enabled"] = True
        self._save_config(self.config)
        
        # Reinitialize module
        module_class = self.modules[module_name]["class"]
        try:
            self.modules[module_name]["instance"] = module_class()
            self.modules[module_name]["enabled"] = True
            self.modules[module_name].pop("error", None)
            return True, f"Module '{module_name}' enabled successfully"
        except Exception as e:
            self.modules[module_name]["error"] = str(e)
            return False, f"Failed to enable '{module_name}': {e}"
    
    def disable_module(self, module_name: str) -> Tuple[bool, str]:
        """Disable a module.
        
        Args:
            module_name: Name of module to disable
            
        Returns:
            (success, message) tuple
        """
        if module_name not in self.modules:
            return False, f"Module '{module_name}' not found"
        
        # Update configuration
        self.config["modules"][module_name]["enabled"] = False
        self._save_config(self.config)
        
        # Disable module
        self.modules[module_name]["instance"] = None
        self.modules[module_name]["enabled"] = False
        
        return True, f"Module '{module_name}' disabled successfully"
    
    def get_config_value(self, key_path: str) -> Any:
        """Get configuration value using dot notation.
        
        Args:
            key_path: Configuration key path (e.g., 'modules.resource_monitor.enabled')
            
        Returns:
            Configuration value or None if not found
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return None
    
    def set_config_value(self, key_path: str, value: Any) -> Tuple[bool, str]:
        """Set configuration value using dot notation.
        
        Args:
            key_path: Configuration key path (e.g., 'modules.resource_monitor.enabled')
            value: Value to set
            
        Returns:
            (success, message) tuple
        """
        keys = key_path.split('.')
        config_ref = self.config
        
        try:
            # Navigate to parent of target key
            for key in keys[:-1]:
                if key not in config_ref:
                    config_ref[key] = {}
                config_ref = config_ref[key]
            
            # Set the value
            config_ref[keys[-1]] = value
            self._save_config(self.config)
            
            return True, f"Configuration '{key_path}' set to '{value}'"
        except Exception as e:
            return False, f"Failed to set configuration: {e}"
    
    def _generate_ai_workflows(self) -> List[Dict[str, Any]]:
        """Generate common workflow patterns for AI assistants."""
        workflows = [
            {
                "name": "Quick Package Build",
                "description": "Build specific CMake package quickly",
                "scenario": "Building single package like websocket or crypto",
                "mcp_tool": "build_monitor/start",
                "parameters": {
                    "targets": ["package_name/fast"],
                    "background": False
                },
                "expected_duration": "30-60 seconds",
                "relevant_modules": ["resource_monitor", "build_tracker", "fix_suggestions"],
                "interpretation_tips": [
                    "Focus on error categorization for quick fixes",
                    "Resource usage typically minimal for single packages",
                    "Fix suggestions most valuable for missing dependencies"
                ]
            },
            {
                "name": "Full System Build",
                "description": "Complete build with all packages",
                "scenario": "Major changes requiring full compilation",
                "mcp_tool": "build_monitor/start", 
                "parameters": {
                    "cmake": True,
                    "targets": [],
                    "background": "auto"
                },
                "expected_duration": "3-8 minutes",
                "relevant_modules": ["resource_monitor", "health_tracker", "dependency_tracker"],
                "interpretation_tips": [
                    "Health score most meaningful for full builds",
                    "Resource monitoring critical for long builds",
                    "Dependency changes often trigger need for full builds"
                ]
            }
        ]
        
        return workflows
    
    def _aggregate_troubleshooting(self) -> Dict[str, Any]:
        """Aggregate troubleshooting information from all modules."""
        troubleshooting = {
            "common_issues": [
                {
                    "issue": "Build conflicts detected",
                    "solution": "Wait for other processes or use force=true",
                    "relevant_modules": ["resource_monitor"]
                },
                {
                    "issue": "CMake configuration failed", 
                    "solution": "Check dependency installations and use fix suggestions",
                    "relevant_modules": ["fix_suggestions", "dependency_tracker"]
                },
                {
                    "issue": "Low health score",
                    "solution": "Review error patterns and recent changes",
                    "relevant_modules": ["health_tracker", "build_tracker", "fix_suggestions"]
                }
            ],
            "module_specific": {}
        }
        
        # Collect troubleshooting from modules with help_data
        for name, module_info in self.modules.items():
            if module_info.get("enabled") and module_info.get("instance"):
                instance = module_info["instance"]
                if hasattr(instance, 'help_data'):
                    help_data = instance.help_data
                    if "troubleshooting" in help_data:
                        troubleshooting["module_specific"][name] = help_data["troubleshooting"]
        
        return troubleshooting
    
    def _calculate_token_metrics(self) -> Dict[str, Any]:
        """Calculate token efficiency metrics across all modules."""
        metrics = {
            "total_modules": len([m for m in self.modules.values() if m.get("enabled")]),
            "estimated_token_range": "15-45 tokens per build response",
            "efficiency_features": [
                "Conditional field inclusion based on relevance",
                "Ultra-compact formats (e.g., 'res': '85%/1.5g')",
                "Smart thresholds to avoid noise",
                "Aggregated data instead of raw values"
            ]
        }
        
        # Collect token estimates from modules
        module_estimates = {}
        for name, module_info in self.modules.items():
            if module_info.get("enabled") and module_info.get("instance"):
                instance = module_info["instance"]
                if hasattr(instance, 'help_data'):
                    help_data = instance.help_data
                    if "token_cost" in help_data:
                        module_estimates[name] = help_data["token_cost"]
        
        if module_estimates:
            metrics["module_estimates"] = module_estimates
        
        return metrics
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status for diagnostics."""
        return {
            "version": self.version,
            "config_file": str(self.config_file),
            "modules": self.list_modules(include_disabled=True),
            "configuration": self.config,
            "enabled_count": len([m for m in self.modules.values() if m.get("enabled")])
        }


# Main CLI interface for standalone usage
def main():
    """Main CLI entry point for buildmon management."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MCP Build Monitor Management Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python buildmon.py --list-tools
  python buildmon.py --help resource_monitor  
  python buildmon.py --enable-tool fix_suggestions
  python buildmon.py --ai-metadata
        """
    )
    
    parser.add_argument("--list-tools", action="store_true", help="List all modules and their status")
    parser.add_argument("--help-module", metavar="MODULE", help="Get help for specific module")
    parser.add_argument("--enable-tool", metavar="MODULE", help="Enable a module")
    parser.add_argument("--disable-tool", metavar="MODULE", help="Disable a module")
    parser.add_argument("--ai-metadata", action="store_true", help="Get AI assistant integration metadata")
    parser.add_argument("--config-get", metavar="KEY", help="Get configuration value")
    parser.add_argument("--config-set", nargs=2, metavar=("KEY", "VALUE"), help="Set configuration value")
    parser.add_argument("--status", action="store_true", help="Get system status")
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = BuildMonManager()
    
    # Handle commands
    if args.list_tools:
        modules = manager.list_modules()
        print("📦 MCP Build Monitor Modules:")
        print("="*50)
        for name, info in modules.items():
            status = "✅ Enabled" if info["enabled"] else "❌ Disabled"
            print(f"{name:20} {status:12} {info.get('description', '')}")
    
    elif args.help_module:
        help_data = manager.get_module_help(args.help_module)
        print(f"📚 Help for {args.help_module}:")
        print("="*50)
        print(json.dumps(help_data, indent=2))
    
    elif args.enable_tool:
        success, message = manager.enable_module(args.enable_tool)
        print("✅" if success else "❌", message)
    
    elif args.disable_tool:
        success, message = manager.disable_module(args.disable_tool)
        print("✅" if success else "❌", message)
    
    elif args.ai_metadata:
        metadata = manager.get_ai_metadata()
        print(json.dumps(metadata, indent=2))
    
    elif args.config_get:
        value = manager.get_config_value(args.config_get)
        print(f"{args.config_get}: {value}")
    
    elif args.config_set:
        key, value = args.config_set
        # Try to parse value as JSON for proper types
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value  # Keep as string
        
        success, message = manager.set_config_value(key, parsed_value)
        print("✅" if success else "❌", message)
    
    elif args.status:
        status = manager.get_system_status()
        print("🖥️  MCP Build Monitor Status:")
        print("="*50)
        print(json.dumps(status, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
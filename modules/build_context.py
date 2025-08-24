"""
Build Context Preserver Module - Optional Feature: Build Environment Preservation

Preserves and restores build context including environment variables, working directory,
and build state for consistent reproducible builds across sessions.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


class BuildContextPreserver:
    """Preserves build context for reproducible builds (optional feature)."""
    
    def __init__(self, context_file: str = None):
        """Initialize build context preserver.
        
        Args:
            context_file: Path to context storage file. If None, uses default location.
        """
        if context_file is None:
            context_file = Path.cwd() / "build_context.json"
            
        self.context_file = Path(context_file)
        self.context_data = self._load_context_data()
        
        # Self-documentation metadata for AI assistants
        self.help_data = {
            "name": "Build Context Preserver",
            "description": "Preserves and restores build environment for consistent reproducible builds",
            "version": "1.0.0",
            "features": [
                "Environment variable preservation and restoration",
                "Working directory and build path tracking",
                "Build tool version recording (cmake, make, gcc)",
                "System information capture for reproducibility",
                "Build configuration snapshot and diff detection"
            ],
            "configuration": {
                "preserve_env_vars": {
                    "type": "list",
                    "default": ["CC", "CXX", "CFLAGS", "CXXFLAGS", "CMAKE_PREFIX_PATH"],
                    "description": "Environment variables to preserve"
                },
                "capture_system_info": {
                    "type": "bool",
                    "default": True,
                    "description": "Capture system information for reproducibility"
                },
                "auto_restore": {
                    "type": "bool",
                    "default": False,
                    "description": "Automatically restore context on initialization"
                }
            },
            "output_format": {
                "context_preserved": "Boolean indicating if context was saved",
                "context_changes": "List of detected environment changes",
                "reproducibility_score": "Score 0-100 for build reproducibility"
            },
            "token_cost": "2-4 tokens per build response (when context changes detected)",
            "ai_metadata": {
                "purpose": "Ensure consistent build environment across different sessions and machines",
                "when_to_use": "Useful for teams or CI/CD environments requiring reproducible builds",
                "interpretation": {
                    "context_preserved": "Build environment successfully captured",
                    "context_changes": "Environment differences detected since last build",
                    "high_reproducibility": ">90% score indicates very consistent environment",
                    "environment_drift": "Significant changes in build environment detected"
                },
                "recommendations": {
                    "environment_changes": "Review and standardize build environment",
                    "tool_version_changes": "Update documentation with new tool requirements",
                    "path_differences": "Ensure consistent library and tool paths"
                }
            },
            "examples": [
                {
                    "scenario": "First context capture",
                    "output": {"context_preserved": True, "reproducibility_score": 100},
                    "interpretation": "Baseline build context established"
                },
                {
                    "scenario": "Environment change detected",
                    "output": {
                        "context_preserved": True,
                        "context_changes": ["CMAKE_PREFIX_PATH modified", "GCC version updated"],
                        "reproducibility_score": 85
                    },
                    "interpretation": "Build environment changed, may affect reproducibility"
                }
            ],
            "troubleshooting": {
                "permission_errors": "Ensure write access to context file location",
                "environment_conflicts": "Check for conflicting environment variable definitions",
                "tool_not_found": "Verify build tools are in PATH and accessible"
            }
        }
    
    def _load_context_data(self) -> Dict[str, Any]:
        """Load build context data from file."""
        try:
            if self.context_file.exists():
                with open(self.context_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        
        # Return default structure
        return {
            "version": "1.0.0",
            "contexts": {},
            "current_context": None,
            "metadata": {
                "last_preserved": 0,
                "total_contexts": 0
            }
        }
    
    def _save_context_data(self):
        """Save context data to file."""
        try:
            self.context_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.context_file, 'w') as f:
                json.dump(self.context_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save build context data: {e}")
    
    def preserve_build_context(self, context_name: str = None) -> Dict[str, Any]:
        """Preserve current build context.
        
        Args:
            context_name: Name for this context. If None, uses timestamp.
            
        Returns:
            Context preservation result
        """
        if context_name is None:
            context_name = f"context_{int(time.time())}"
        
        current_time = time.time()
        
        # Capture current context
        context = {
            "timestamp": current_time,
            "working_directory": str(Path.cwd()),
            "environment_variables": self._capture_environment_variables(),
            "system_info": self._capture_system_info(),
            "build_tools": self._capture_build_tool_versions(),
            "build_paths": self._capture_build_paths()
        }
        
        # Store context
        self.context_data["contexts"][context_name] = context
        self.context_data["current_context"] = context_name
        self.context_data["metadata"]["last_preserved"] = current_time
        self.context_data["metadata"]["total_contexts"] = len(self.context_data["contexts"])
        
        self._save_context_data()
        
        return {
            "context_preserved": True,
            "context_name": context_name,
            "preserved_items": len(context["environment_variables"]) + len(context["build_tools"]),
            "timestamp": current_time
        }
    
    def detect_context_changes(self, reference_context: str = None) -> List[Dict[str, Any]]:
        """Detect changes in build context since reference.
        
        Args:
            reference_context: Context name to compare against. If None, uses current.
            
        Returns:
            List of detected changes
        """
        if reference_context is None:
            reference_context = self.context_data.get("current_context")
        
        if not reference_context or reference_context not in self.context_data["contexts"]:
            return []
        
        ref_context = self.context_data["contexts"][reference_context]
        current_env = self._capture_environment_variables()
        current_tools = self._capture_build_tool_versions()
        current_paths = self._capture_build_paths()
        
        changes = []
        
        # Check environment variable changes
        ref_env = ref_context.get("environment_variables", {})
        for var, value in current_env.items():
            if var in ref_env:
                if ref_env[var] != value:
                    changes.append({
                        "type": "environment_variable",
                        "name": var,
                        "old_value": ref_env[var],
                        "new_value": value,
                        "change": "modified"
                    })
            else:
                changes.append({
                    "type": "environment_variable",
                    "name": var,
                    "old_value": None,
                    "new_value": value,
                    "change": "added"
                })
        
        for var, value in ref_env.items():
            if var not in current_env:
                changes.append({
                    "type": "environment_variable",
                    "name": var,
                    "old_value": value,
                    "new_value": None,
                    "change": "removed"
                })
        
        # Check build tool version changes
        ref_tools = ref_context.get("build_tools", {})
        for tool, version in current_tools.items():
            if tool in ref_tools:
                if ref_tools[tool] != version:
                    changes.append({
                        "type": "build_tool",
                        "name": tool,
                        "old_value": ref_tools[tool],
                        "new_value": version,
                        "change": "version_updated"
                    })
        
        # Check working directory change
        current_wd = str(Path.cwd())
        ref_wd = ref_context.get("working_directory")
        if ref_wd and ref_wd != current_wd:
            changes.append({
                "type": "working_directory",
                "name": "working_directory",
                "old_value": ref_wd,
                "new_value": current_wd,
                "change": "changed"
            })
        
        return changes
    
    def calculate_reproducibility_score(self, changes: List[Dict[str, Any]]) -> int:
        """Calculate reproducibility score based on context changes.
        
        Args:
            changes: List of changes from detect_context_changes()
            
        Returns:
            Reproducibility score 0-100
        """
        if not changes:
            return 100
        
        score = 100
        
        for change in changes:
            change_type = change.get("type", "unknown")
            change_action = change.get("change", "modified")
            
            if change_type == "environment_variable":
                if change_action == "modified":
                    # Critical env vars have higher impact
                    var_name = change.get("name", "")
                    if var_name in ["CC", "CXX", "CMAKE_PREFIX_PATH"]:
                        score -= 15
                    else:
                        score -= 5
                elif change_action in ["added", "removed"]:
                    score -= 10
            
            elif change_type == "build_tool":
                if change_action == "version_updated":
                    tool_name = change.get("name", "")
                    if tool_name in ["cmake", "gcc", "clang"]:
                        score -= 20  # Major tool version changes
                    else:
                        score -= 10
            
            elif change_type == "working_directory":
                score -= 5  # Minor impact for directory changes
        
        return max(0, score)
    
    def _capture_environment_variables(self) -> Dict[str, str]:
        """Capture relevant environment variables."""
        important_vars = [
            "CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS",
            "CMAKE_PREFIX_PATH", "CMAKE_MODULE_PATH", "CMAKE_BUILD_TYPE",
            "PATH", "LD_LIBRARY_PATH", "PKG_CONFIG_PATH",
            "MAKEFLAGS", "PARALLEL_JOBS"
        ]
        
        env_vars = {}
        for var in important_vars:
            value = os.environ.get(var)
            if value is not None:
                env_vars[var] = value
        
        return env_vars
    
    def _capture_system_info(self) -> Dict[str, str]:
        """Capture system information."""
        import platform
        
        system_info = {
            "system": platform.system(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python_version": platform.python_version()
        }
        
        # Try to get distribution info on Linux
        try:
            if platform.system() == "Linux":
                import distro
                system_info["distribution"] = distro.id()
                system_info["distribution_version"] = distro.version()
        except ImportError:
            pass
        
        return system_info
    
    def _capture_build_tool_versions(self) -> Dict[str, str]:
        """Capture versions of build tools."""
        tools = {}
        
        # CMake version
        try:
            result = os.popen("cmake --version 2>/dev/null | head -1").read().strip()
            if result:
                tools["cmake"] = result
        except:
            pass
        
        # Make version
        try:
            result = os.popen("make --version 2>/dev/null | head -1").read().strip()
            if result:
                tools["make"] = result
        except:
            pass
        
        # GCC version
        try:
            result = os.popen("gcc --version 2>/dev/null | head -1").read().strip()
            if result:
                tools["gcc"] = result
        except:
            pass
        
        # G++ version
        try:
            result = os.popen("g++ --version 2>/dev/null | head -1").read().strip()
            if result:
                tools["g++"] = result
        except:
            pass
        
        # Clang version (if available)
        try:
            result = os.popen("clang --version 2>/dev/null | head -1").read().strip()
            if result:
                tools["clang"] = result
        except:
            pass
        
        return tools
    
    def _capture_build_paths(self) -> Dict[str, str]:
        """Capture important build-related paths."""
        paths = {}
        
        # Current working directory
        paths["working_directory"] = str(Path.cwd())
        
        # Build directory (if exists)
        build_dir = Path.cwd() / "build"
        if build_dir.exists():
            paths["build_directory"] = str(build_dir)
        
        # CMake binary path
        cmake_path = os.popen("which cmake 2>/dev/null").read().strip()
        if cmake_path:
            paths["cmake_path"] = cmake_path
        
        # Make binary path
        make_path = os.popen("which make 2>/dev/null").read().strip()
        if make_path:
            paths["make_path"] = make_path
        
        return paths
    
    def restore_build_context(self, context_name: str) -> bool:
        """Restore a previously saved build context.
        
        Args:
            context_name: Name of context to restore
            
        Returns:
            True if successfully restored, False otherwise
        """
        if context_name not in self.context_data["contexts"]:
            return False
        
        context = self.context_data["contexts"][context_name]
        
        try:
            # Restore environment variables
            env_vars = context.get("environment_variables", {})
            for var, value in env_vars.items():
                os.environ[var] = value
            
            # Change to saved working directory
            saved_wd = context.get("working_directory")
            if saved_wd and Path(saved_wd).exists():
                os.chdir(saved_wd)
            
            # Update current context
            self.context_data["current_context"] = context_name
            self._save_context_data()
            
            return True
            
        except Exception as e:
            print(f"Error restoring build context: {e}")
            return False
    
    def list_contexts(self) -> Dict[str, Any]:
        """List all saved build contexts."""
        contexts_info = {}
        
        for name, context in self.context_data["contexts"].items():
            contexts_info[name] = {
                "timestamp": context.get("timestamp", 0),
                "working_directory": context.get("working_directory", "unknown"),
                "env_var_count": len(context.get("environment_variables", {})),
                "tool_count": len(context.get("build_tools", {})),
                "is_current": name == self.context_data.get("current_context")
            }
        
        return contexts_info
    
    def delete_context(self, context_name: str) -> bool:
        """Delete a saved build context.
        
        Args:
            context_name: Name of context to delete
            
        Returns:
            True if successfully deleted, False otherwise
        """
        if context_name not in self.context_data["contexts"]:
            return False
        
        del self.context_data["contexts"][context_name]
        
        # Update current context if it was deleted
        if self.context_data.get("current_context") == context_name:
            self.context_data["current_context"] = None
        
        # Update metadata
        self.context_data["metadata"]["total_contexts"] = len(self.context_data["contexts"])
        
        self._save_context_data()
        return True
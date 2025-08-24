"""
Incremental Build Tracker Module - Feature 4: Incremental Build Intelligence

Tracks file changes since last successful build to provide intelligent rebuild recommendations
and impact assessment. Helps optimize build times through smart incremental compilation.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set


class IncrementalBuildTracker:
    """Tracks file changes for intelligent incremental build recommendations."""
    
    def __init__(self, tracker_file: str = None, project_root: str = None):
        """Initialize incremental build tracker.
        
        Args:
            tracker_file: Path to tracker storage file. If None, uses default location.
            project_root: Root directory of the project. If None, uses current directory.
        """
        if tracker_file is None:
            tracker_file = Path.cwd() / "build_tracker.json"
        if project_root is None:
            project_root = Path.cwd()
            
        self.tracker_file = Path(tracker_file)
        self.project_root = Path(project_root)
        self.tracker_data = self._load_tracker_data()
        
        # Self-documentation metadata for AI assistants
        self.help_data = {
            "name": "Incremental Build Tracker",
            "description": "Tracks file changes for intelligent incremental build recommendations and optimization",
            "version": "1.0.0",
            "features": [
                "File modification timestamp tracking across builds",
                "Intelligent build recommendation engine (full/incremental/targeted)",
                "Change impact assessment (none/low/medium/high)",
                "Source file vs configuration file change detection",
                "Build optimization through targeted rebuild suggestions"
            ],
            "configuration": {
                "monitored_extensions": {
                    "type": "list",
                    "default": [".c", ".cpp", ".h", ".hpp", ".cmake", ".txt"],
                    "description": "File extensions to monitor for changes"
                },
                "config_files": {
                    "type": "list", 
                    "default": ["CMakeLists.txt", "*.cmake"],
                    "description": "Configuration files that trigger full rebuilds"
                },
                "ignore_patterns": {
                    "type": "list",
                    "default": ["build/", ".git/", "__pycache__/"],
                    "description": "Directory patterns to ignore"
                }
            },
            "output_format": {
                "changed_files": "List of modified files since last build",
                "build_recommendation": "full_rebuild, incremental_rebuild, or targeted_rebuild",
                "change_impact": "none, low, medium, or high"
            },
            "token_cost": "5-12 tokens per build response (when changes detected)",
            "ai_metadata": {
                "purpose": "Optimize build times through intelligent change detection and targeted rebuilds",
                "when_to_use": "Automatically enabled when file changes detected since last successful build",
                "interpretation": {
                    "full_rebuild": "Configuration changes require complete rebuild",
                    "incremental_rebuild": "Source changes allow incremental compilation",
                    "targeted_rebuild": "Specific packages/modules affected, rebuild only those",
                    "change_impact_high": "Many files changed or core dependencies modified",
                    "change_impact_low": "Few isolated changes, minimal rebuild needed"
                },
                "recommendations": {
                    "frequent_full_rebuilds": "Consider build system optimization or dependency cleanup",
                    "no_incremental_benefit": "Check if incremental compilation is properly configured",
                    "large_change_sets": "Consider smaller, more focused commits for faster iteration"
                }
            },
            "examples": [
                {
                    "scenario": "Single source file modified",
                    "output": {
                        "changed_files": ["src/websocket.cpp"],
                        "build_recommendation": "incremental_rebuild", 
                        "change_impact": "low"
                    },
                    "interpretation": "Fast incremental build recommended"
                },
                {
                    "scenario": "CMakeLists.txt modified",
                    "output": {
                        "changed_files": ["CMakeLists.txt"],
                        "build_recommendation": "full_rebuild",
                        "change_impact": "high"
                    },
                    "interpretation": "Configuration change requires full rebuild"
                },
                {
                    "scenario": "Multiple package files changed", 
                    "output": {
                        "changed_files": ["src/crypto.cpp", "src/websocket.cpp"],
                        "build_recommendation": "targeted_rebuild",
                        "change_impact": "medium"
                    },
                    "interpretation": "Rebuild specific affected packages only"
                }
            ],
            "troubleshooting": {
                "no_change_detection": "Ensure file permissions allow reading modification times",
                "always_full_rebuild": "Check if configuration files are being modified unnecessarily",
                "missing_files": "Verify project_root path is correct and files exist"
            }
        }
    
    def _load_tracker_data(self) -> Dict[str, Any]:
        """Load build tracker data from file."""
        try:
            if self.tracker_file.exists():
                with open(self.tracker_file, 'r') as f:
                    data = json.load(f)
                    # Ensure required structure
                    if "file_timestamps" not in data:
                        data["file_timestamps"] = {}
                    if "last_successful_builds" not in data:
                        data["last_successful_builds"] = {}
                    if "metadata" not in data:
                        data["metadata"] = {"last_scan": 0}
                    return data
        except (json.JSONDecodeError, IOError):
            pass
        
        # Return default structure
        return {
            "file_timestamps": {},
            "last_successful_builds": {},
            "metadata": {
                "last_scan": 0,
                "version": "1.0.0"
            }
        }
    
    def _save_tracker_data(self):
        """Save tracker data to file."""
        try:
            self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tracker_file, 'w') as f:
                json.dump(self.tracker_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save build tracker data: {e}")
    
    def _get_monitored_files(self) -> List[Path]:
        """Get list of files to monitor for changes."""
        monitored_extensions = {'.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx', 
                              '.cmake', '.txt', '.in', '.py'}
        
        monitored_files = []
        
        # Walk through project directory
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore_path(root_path / d)]
            
            for file in files:
                file_path = root_path / file
                
                # Check if file should be monitored
                if (file_path.suffix.lower() in monitored_extensions or
                    file_path.name in ['CMakeLists.txt', 'Makefile']):
                    if not self._should_ignore_path(file_path):
                        monitored_files.append(file_path)
        
        return monitored_files
    
    def _should_ignore_path(self, path: Path) -> bool:
        """Check if path should be ignored based on ignore patterns."""
        ignore_patterns = ['build', '.git', '__pycache__', '.pytest_cache', 
                          'node_modules', '.vscode', '.idea']
        
        path_str = str(path.relative_to(self.project_root))
        
        for pattern in ignore_patterns:
            if pattern in path_str or path_str.startswith(pattern):
                return True
        
        return False
    
    def detect_changes_since_build(self, targets: List[str]) -> Optional[Dict[str, Any]]:
        """Detect file changes since last successful build."""
        # Get target key for tracking
        target_key = self._get_target_key(targets)
        
        # Get last successful build timestamp
        last_build_time = self.tracker_data["last_successful_builds"].get(target_key, 0)
        
        if last_build_time == 0:
            # No previous build recorded
            return None
        
        # Scan for changed files
        changed_files = []
        config_files_changed = []
        current_time = time.time()
        
        monitored_files = self._get_monitored_files()
        
        for file_path in monitored_files:
            try:
                if not file_path.exists():
                    continue
                    
                file_mtime = file_path.stat().st_mtime
                relative_path = str(file_path.relative_to(self.project_root))
                
                # Check if file was modified since last successful build
                if file_mtime > last_build_time:
                    changed_files.append(relative_path)
                    
                    # Check if it's a configuration file
                    if (file_path.name == 'CMakeLists.txt' or 
                        file_path.suffix == '.cmake' or
                        file_path.name == 'Makefile'):
                        config_files_changed.append(relative_path)
                
            except (OSError, ValueError):
                continue
        
        if not changed_files:
            return None
        
        # Update metadata
        self.tracker_data["metadata"]["last_scan"] = current_time
        self._save_tracker_data()
        
        return {
            "changed_files": changed_files,
            "config_files_changed": config_files_changed,
            "total_changes": len(changed_files),
            "last_build_time": last_build_time,
            "scan_time": current_time
        }
    
    def get_build_recommendation(self, change_data: Optional[Dict[str, Any]]) -> str:
        """Get intelligent build recommendation based on changes."""
        if not change_data:
            return "no_changes"
        
        changed_files = change_data.get("changed_files", [])
        config_files_changed = change_data.get("config_files_changed", [])
        
        if not changed_files:
            return "no_changes"
        
        # Configuration files always require full rebuild
        if config_files_changed:
            return "full_rebuild"
        
        # Check change patterns for targeted recommendations
        source_files = [f for f in changed_files if self._is_source_file(f)]
        header_files = [f for f in changed_files if self._is_header_file(f)]
        
        # Many changes or header files suggest full rebuild
        if len(changed_files) > 10 or len(header_files) > 3:
            return "full_rebuild"
        
        # Check if changes are clustered in specific packages/directories
        if self._changes_are_clustered(changed_files):
            return "targeted_rebuild"
        
        # Few isolated source file changes
        if len(source_files) <= 3 and len(header_files) <= 1:
            return "incremental_rebuild"
        
        # Default to incremental for moderate changes
        return "incremental_rebuild"
    
    def get_change_impact(self, change_data: Optional[Dict[str, Any]]) -> str:
        """Assess the impact level of changes."""
        if not change_data:
            return "none"
        
        changed_files = change_data.get("changed_files", [])
        config_files_changed = change_data.get("config_files_changed", [])
        
        if not changed_files:
            return "none"
        
        # Configuration changes are always high impact
        if config_files_changed:
            return "high"
        
        # Assess based on number and type of changes
        header_files = [f for f in changed_files if self._is_header_file(f)]
        total_files = len(changed_files)
        
        if total_files >= 10 or len(header_files) >= 5:
            return "high"
        elif total_files >= 5 or len(header_files) >= 2:
            return "medium"
        elif total_files >= 1:
            return "low"
        else:
            return "none"
    
    def record_successful_build(self, targets: List[str]):
        """Record successful build completion for target tracking."""
        target_key = self._get_target_key(targets)
        current_time = time.time()
        
        # Update last successful build timestamp
        self.tracker_data["last_successful_builds"][target_key] = current_time
        
        # Update file timestamps for changed files
        monitored_files = self._get_monitored_files()
        for file_path in monitored_files:
            try:
                if file_path.exists():
                    relative_path = str(file_path.relative_to(self.project_root))
                    self.tracker_data["file_timestamps"][relative_path] = file_path.stat().st_mtime
            except (OSError, ValueError):
                continue
        
        # Update metadata
        self.tracker_data["metadata"]["last_successful_build"] = current_time
        self.tracker_data["metadata"]["total_successful_builds"] = \
            self.tracker_data["metadata"].get("total_successful_builds", 0) + 1
        
        self._save_tracker_data()
    
    def _get_target_key(self, targets: List[str]) -> str:
        """Generate consistent target key for tracking."""
        if not targets:
            return "default_build"
        
        # Sort targets for consistency
        sorted_targets = sorted(targets)
        return "_".join(sorted_targets).replace("/", "_").replace("package_", "pkg_")
    
    def _is_source_file(self, file_path: str) -> bool:
        """Check if file is a source code file."""
        source_extensions = {'.c', '.cpp', '.cc', '.cxx'}
        return Path(file_path).suffix.lower() in source_extensions
    
    def _is_header_file(self, file_path: str) -> bool:
        """Check if file is a header file."""
        header_extensions = {'.h', '.hpp', '.hxx'}
        return Path(file_path).suffix.lower() in header_extensions
    
    def _changes_are_clustered(self, changed_files: List[str]) -> bool:
        """Check if file changes are clustered in specific directories/packages."""
        if len(changed_files) <= 2:
            return False
        
        # Group files by their parent directory
        directories = {}
        for file_path in changed_files:
            parent_dir = str(Path(file_path).parent)
            if parent_dir not in directories:
                directories[parent_dir] = 0
            directories[parent_dir] += 1
        
        # Check if 80% or more changes are in 1-2 directories
        total_changes = len(changed_files)
        sorted_dirs = sorted(directories.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_dirs) >= 2:
            top_two_changes = sorted_dirs[0][1] + sorted_dirs[1][1]
            return top_two_changes / total_changes >= 0.8
        elif len(sorted_dirs) == 1:
            return sorted_dirs[0][1] / total_changes >= 0.8
        
        return False
    
    def get_tracking_statistics(self) -> Dict[str, Any]:
        """Get build tracking statistics for analysis."""
        return {
            "tracked_targets": list(self.tracker_data["last_successful_builds"].keys()),
            "total_monitored_files": len(self.tracker_data.get("file_timestamps", {})),
            "last_scan": self.tracker_data["metadata"].get("last_scan", 0),
            "total_successful_builds": self.tracker_data["metadata"].get("total_successful_builds", 0),
            "version": self.tracker_data["metadata"].get("version", "1.0.0")
        }
    
    def clear_tracking_data(self, targets: List[str] = None):
        """Clear tracking data for specific targets or all targets."""
        if targets is None:
            # Clear all tracking data
            self.tracker_data["file_timestamps"] = {}
            self.tracker_data["last_successful_builds"] = {}
            self.tracker_data["metadata"]["total_successful_builds"] = 0
        else:
            # Clear specific target
            target_key = self._get_target_key(targets)
            if target_key in self.tracker_data["last_successful_builds"]:
                del self.tracker_data["last_successful_builds"][target_key]
        
        self._save_tracker_data()
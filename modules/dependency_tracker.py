"""
Dependency Tracker Module - Feature 7: Dependency Change Detection

Monitors changes to dependency-related files (CMakeLists.txt, package configs, etc.) 
and provides intelligent recommendations for handling dependency updates.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


class DependencyTracker:
    """Tracks dependency-related file changes and provides rebuild recommendations."""
    
    def __init__(self, tracker_file: str = None, project_root: str = None):
        """Initialize dependency tracker.
        
        Args:
            tracker_file: Path to tracker storage file. If None, uses default location.
            project_root: Root directory of the project. If None, uses current directory.
        """
        if tracker_file is None:
            tracker_file = Path.cwd() / "dependency_tracker.json"
        if project_root is None:
            project_root = Path.cwd()
            
        self.tracker_file = Path(tracker_file)
        self.project_root = Path(project_root)
        self.tracker_data = self._load_tracker_data()
        
        # Self-documentation metadata for AI assistants
        self.help_data = {
            "name": "Dependency Tracker",
            "description": "Monitors dependency-related file changes and provides intelligent rebuild recommendations",
            "version": "1.0.0",
            "features": [
                "CMakeLists.txt and build configuration change detection",
                "Package configuration file monitoring (*.pc, *.cmake)",
                "Dependency impact assessment (full_rebuild, package_specific, dependency_update)",
                "Build system recommendation engine",
                "Integration with package managers (apt, brew, vcpkg detection)"
            ],
            "configuration": {
                "dependency_files": {
                    "type": "list",
                    "default": ["CMakeLists.txt", "*.cmake", "*.pc", "conanfile.*", "vcpkg.json"],
                    "description": "Patterns for dependency-related files to monitor"
                },
                "build_config_files": {
                    "type": "list",
                    "default": ["configure.ac", "Makefile.in", "meson.build"],
                    "description": "Build system configuration files"
                },
                "check_interval": {
                    "type": "int",
                    "default": 3600,
                    "description": "Seconds between dependency checks"
                }
            },
            "output_format": {
                "dependency_changes": "Array of dependency change objects",
                "change.file": "Path to changed dependency file",
                "change.type": "build_config, package_config, or dependency_manifest",
                "change.impact": "full_rebuild, package_specific, or dependency_update",
                "change.recommendation": "Specific action to take"
            },
            "token_cost": "8-15 tokens per build response (when changes detected)",
            "ai_metadata": {
                "purpose": "Detect dependency changes requiring special build handling or environment updates",
                "when_to_use": "Automatically enabled when dependency-related files are modified",
                "interpretation": {
                    "build_config": "CMakeLists.txt or Makefile changes affecting build process",
                    "package_config": "External library configuration changes",
                    "dependency_manifest": "Package manager files (conanfile, vcpkg.json) changed",
                    "full_rebuild": "Changes require complete project rebuild",
                    "package_specific": "Only specific packages/modules affected",
                    "dependency_update": "External dependencies need to be updated/reinstalled"
                },
                "recommendations": {
                    "frequent_config_changes": "Consider stabilizing build configuration",
                    "external_deps_changed": "Update package manager dependencies before building",
                    "build_system_evolution": "Document major build system changes for team"
                }
            },
            "examples": [
                {
                    "scenario": "CMakeLists.txt modified",
                    "output": {
                        "dependency_changes": [{
                            "file": "CMakeLists.txt",
                            "type": "build_config",
                            "impact": "full_rebuild",
                            "recommendation": "Run cmake -S $(pwd) -B $(pwd)/build && make clean && make"
                        }]
                    },
                    "interpretation": "Build configuration changed, full rebuild required"
                },
                {
                    "scenario": "Package config file updated",
                    "output": {
                        "dependency_changes": [{
                            "file": "FindOpenSSL.cmake", 
                            "type": "package_config",
                            "impact": "package_specific",
                            "recommendation": "Clear CMake cache and rebuild affected packages"
                        }]
                    },
                    "interpretation": "OpenSSL package configuration changed, targeted rebuild"
                },
                {
                    "scenario": "Dependency manifest changed",
                    "output": {
                        "dependency_changes": [{
                            "file": "conanfile.txt",
                            "type": "dependency_manifest", 
                            "impact": "dependency_update",
                            "recommendation": "Run conan install && cmake .. && make"
                        }]
                    },
                    "interpretation": "External dependencies changed, update required"
                }
            ],
            "troubleshooting": {
                "no_changes_detected": "Verify dependency files exist and are being monitored",
                "false_positives": "Check if temporary files are being included in monitoring",
                "missing_recommendations": "Ensure file patterns match actual project structure"
            }
        }
    
    def _load_tracker_data(self) -> Dict[str, Any]:
        """Load dependency tracker data from file."""
        try:
            if self.tracker_file.exists():
                with open(self.tracker_file, 'r') as f:
                    data = json.load(f)
                    # Ensure required structure
                    if "dependency_files" not in data:
                        data["dependency_files"] = {}
                    if "last_check" not in data:
                        data["last_check"] = 0
                    if "metadata" not in data:
                        data["metadata"] = {}
                    return data
        except (json.JSONDecodeError, IOError):
            pass
        
        # Return default structure
        return {
            "dependency_files": {},
            "last_check": 0,
            "metadata": {
                "version": "1.0.0",
                "total_checks": 0
            }
        }
    
    def _save_tracker_data(self):
        """Save tracker data to file."""
        try:
            self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tracker_file, 'w') as f:
                json.dump(self.tracker_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save dependency tracker data: {e}")
    
    def _get_dependency_files(self) -> List[Path]:
        """Get list of dependency-related files to monitor."""
        dependency_patterns = [
            'CMakeLists.txt',
            '*.cmake',
            'configure.ac',
            'configure.in',
            'Makefile.in',
            'Makefile.am',
            'meson.build',
            'BUILD',
            'BUILD.bazel',
            'conanfile.txt',
            'conanfile.py',
            'vcpkg.json',
            'vcpkg-configuration.json',
            'requirements.txt',
            'setup.py',
            'pyproject.toml',
            'Cargo.toml',
            'package.json',
            '*.pc',
            '*.pc.in'
        ]
        
        dependency_files = []
        
        # Walk through project directory
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            
            # Skip build and other irrelevant directories
            dirs[:] = [d for d in dirs if not self._should_ignore_directory(d)]
            
            for file in files:
                file_path = root_path / file
                
                # Check if file matches dependency patterns
                for pattern in dependency_patterns:
                    if self._matches_pattern(file, pattern):
                        dependency_files.append(file_path)
                        break
        
        return dependency_files
    
    def _should_ignore_directory(self, dirname: str) -> bool:
        """Check if directory should be ignored."""
        ignore_dirs = {'build', '.git', '__pycache__', '.pytest_cache', 
                      'node_modules', '.vscode', '.idea', '.vs', 'venv', '.venv'}
        return dirname in ignore_dirs
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches dependency file pattern."""
        if '*' in pattern:
            # Simple wildcard matching
            if pattern.startswith('*.'):
                return filename.endswith(pattern[1:])
            elif pattern.endswith('*'):
                return filename.startswith(pattern[:-1])
        else:
            return filename == pattern
        return False
    
    def detect_dependency_changes(self) -> Optional[List[Dict[str, Any]]]:
        """Detect changes in dependency-related files."""
        current_time = time.time()
        dependency_files = self._get_dependency_files()
        changes = []
        
        for file_path in dependency_files:
            try:
                if not file_path.exists():
                    continue
                
                relative_path = str(file_path.relative_to(self.project_root))
                file_mtime = file_path.stat().st_mtime
                
                # Check if file has been modified since last check
                last_mtime = self.tracker_data["dependency_files"].get(relative_path, 0)
                
                if file_mtime > last_mtime:
                    change_info = self._analyze_dependency_change(file_path, relative_path)
                    if change_info:
                        changes.append(change_info)
                    
                    # Update tracking data
                    self.tracker_data["dependency_files"][relative_path] = file_mtime
                
            except (OSError, ValueError):
                continue
        
        # Update metadata
        self.tracker_data["last_check"] = current_time
        self.tracker_data["metadata"]["total_checks"] = \
            self.tracker_data["metadata"].get("total_checks", 0) + 1
        
        if changes:
            self._save_tracker_data()
            return changes
        
        return None
    
    def _analyze_dependency_change(self, file_path: Path, relative_path: str) -> Optional[Dict[str, Any]]:
        """Analyze a dependency file change and determine impact."""
        filename = file_path.name
        
        # Determine change type
        change_type = self._classify_dependency_file(filename)
        
        # Determine impact and recommendation
        impact, recommendation = self._assess_change_impact(filename, change_type)
        
        return {
            "file": relative_path,
            "type": change_type,
            "impact": impact,
            "recommendation": recommendation,
            "timestamp": time.time()
        }
    
    def _classify_dependency_file(self, filename: str) -> str:
        """Classify the type of dependency file."""
        filename_lower = filename.lower()
        
        # Build configuration files
        if filename in ['CMakeLists.txt', 'configure.ac', 'configure.in', 
                       'Makefile.in', 'Makefile.am', 'meson.build']:
            return "build_config"
        
        # Package configuration files
        if (filename.endswith('.cmake') or filename.endswith('.pc') or 
            filename.endswith('.pc.in')):
            return "package_config"
        
        # Dependency manifests
        if filename in ['conanfile.txt', 'conanfile.py', 'vcpkg.json', 
                       'vcpkg-configuration.json', 'requirements.txt', 
                       'setup.py', 'pyproject.toml', 'Cargo.toml', 'package.json']:
            return "dependency_manifest"
        
        # Build system files
        if filename in ['BUILD', 'BUILD.bazel']:
            return "build_system"
        
        return "unknown"
    
    def _assess_change_impact(self, filename: str, change_type: str) -> tuple[str, str]:
        """Assess the impact of a dependency change and provide recommendation."""
        filename_lower = filename.lower()
        
        if change_type == "build_config":
            if filename == "CMakeLists.txt":
                return "full_rebuild", "Run cmake -S $(pwd) -B $(pwd)/build && make clean && make"
            elif filename in ["configure.ac", "configure.in"]:
                return "full_rebuild", "Run autoreconf -fiv && ./configure && make clean && make"
            elif filename == "meson.build":
                return "full_rebuild", "Run meson setup --reconfigure builddir && ninja -C builddir clean && ninja -C builddir"
            else:
                return "full_rebuild", "Clean and rebuild entire project"
        
        elif change_type == "package_config":
            if "find" in filename_lower and filename.endswith('.cmake'):
                package_name = filename.replace('Find', '').replace('.cmake', '')
                return "package_specific", f"Clear CMake cache and rebuild packages using {package_name}"
            elif filename.endswith('.pc'):
                package_name = filename.replace('.pc', '')
                return "package_specific", f"Update pkg-config cache and rebuild {package_name} dependencies"
            else:
                return "package_specific", "Clear configuration cache and rebuild affected packages"
        
        elif change_type == "dependency_manifest":
            if filename.startswith("conanfile"):
                return "dependency_update", "Run conan install && cmake -S $(pwd) -B $(pwd)/build && make"
            elif filename.startswith("vcpkg"):
                return "dependency_update", "Run vcpkg integrate install && cmake -S $(pwd) -B $(pwd)/build && make"
            elif filename == "requirements.txt":
                return "dependency_update", "Run pip install -r requirements.txt && rebuild"
            elif filename == "package.json":
                return "dependency_update", "Run npm install && rebuild"
            elif filename == "Cargo.toml":
                return "dependency_update", "Run cargo build"
            else:
                return "dependency_update", "Update dependencies and rebuild"
        
        elif change_type == "build_system":
            return "full_rebuild", "Regenerate build files and rebuild entire project"
        
        else:
            return "unknown", "Manual investigation required"
    
    def get_dependency_status(self) -> Dict[str, Any]:
        """Get current dependency tracking status."""
        monitored_files = self._get_dependency_files()
        
        status = {
            "monitored_files_count": len(monitored_files),
            "tracked_files": list(self.tracker_data["dependency_files"].keys()),
            "last_check": self.tracker_data["last_check"],
            "total_checks": self.tracker_data["metadata"].get("total_checks", 0),
            "version": self.tracker_data["metadata"].get("version", "1.0.0")
        }
        
        # Group files by type
        file_types = {}
        for file_path in monitored_files:
            file_type = self._classify_dependency_file(file_path.name)
            if file_type not in file_types:
                file_types[file_type] = []
            file_types[file_type].append(str(file_path.relative_to(self.project_root)))
        
        status["files_by_type"] = file_types
        
        return status
    
    def force_dependency_scan(self) -> List[Dict[str, Any]]:
        """Force a dependency scan regardless of timestamps."""
        # Clear tracking data to force detection of all files
        self.tracker_data["dependency_files"] = {}
        
        # Perform scan
        changes = self.detect_dependency_changes()
        
        return changes or []
    
    def clear_dependency_tracking(self):
        """Clear all dependency tracking data."""
        self.tracker_data["dependency_files"] = {}
        self.tracker_data["last_check"] = 0
        self.tracker_data["metadata"]["total_checks"] = 0
        self._save_tracker_data()
    
    def add_custom_dependency_pattern(self, pattern: str):
        """Add a custom file pattern to monitor."""
        # This would be used to extend monitoring to project-specific files
        # Implementation would require extending the _get_dependency_files method
        # For now, this is a placeholder for future extensibility
        pass
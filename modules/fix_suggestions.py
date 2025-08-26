"""
Fix Suggestions Database Module - Feature 8: Intelligent Fix Suggestions

Provides pattern recognition for common build errors and suggests actionable fixes
with confidence scores and step-by-step resolution commands.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class FixSuggestionsDatabase:
    """Database of fix suggestions for common build errors with pattern matching."""
    
    def __init__(self, suggestions_file: str = None):
        """Initialize fix suggestions database.
        
        Args:
            suggestions_file: Path to suggestions storage file. If None, uses default location.
        """
        if suggestions_file is None:
            suggestions_file = Path(__file__).parent / "fix_suggestions.json"
            
        self.suggestions_file = Path(suggestions_file)
        self.suggestions_db = self._load_suggestions_db()
        
        # Self-documentation metadata for AI assistants
        self.help_data = {
            "name": "Fix Suggestions Database",
            "description": "Intelligent error pattern recognition with actionable fix suggestions",
            "version": "1.0.0",
            "features": [
                "Pattern-based error recognition with regex matching",
                "Confidence scoring for fix suggestions (0-100%)",
                "Step-by-step fix commands with complexity assessment",
                "Context-aware suggestions based on file paths and error types",
                "Extensible database of common C/C++ build error patterns"
            ],
            "configuration": {
                "min_confidence_threshold": {
                    "type": "int",
                    "default": 60,
                    "description": "Minimum confidence score to include suggestions"
                },
                "max_suggestions_per_error": {
                    "type": "int",
                    "default": 3,
                    "description": "Maximum number of suggestions per error"
                },
                "enable_learning": {
                    "type": "bool",
                    "default": False,
                    "description": "Enable learning from successful fixes (future feature)"
                }
            },
            "output_format": {
                "pattern": "Pattern identifier for the error",
                "suggested_fix": "Human-readable fix description",
                "fix_commands": "Array of shell commands to execute",
                "fix_type": "quick, medium, or complex",
                "confidence": "Confidence score 0-100"
            },
            "token_cost": "10-20 tokens per error with suggestions",
            "ai_metadata": {
                "purpose": "Provide immediate, actionable solutions for common build errors",
                "when_to_use": "Automatically applied when error patterns match known issues",
                "interpretation": {
                    "high_confidence": ">90% confidence: Execute immediately, very reliable",
                    "medium_confidence": "70-90% confidence: Review before execution",
                    "low_confidence": "<70% confidence: Use as guidance, verify applicability",
                    "fix_type_quick": "1-2 commands, usually safe to execute",
                    "fix_type_medium": "3-5 commands, review for environment compatibility",
                    "fix_type_complex": "6+ commands or system changes, careful consideration required"
                },
                "recommendations": {
                    "multiple_suggestions": "Try suggestions in confidence order",
                    "repeated_errors": "Consider adding project-specific patterns",
                    "low_success_rate": "Review and refine pattern matching rules"
                }
            },
            "examples": [
                {
                    "scenario": "Missing OpenSSL development headers",
                    "error": "fatal error: openssl/ssl.h: No such file or directory",
                    "output": {
                        "pattern": "missing_openssl_headers",
                        "suggested_fix": "Install OpenSSL development packages",
                        "fix_commands": ["sudo apt update", "sudo apt install -y libssl-dev openssl"],
                        "fix_type": "quick",
                        "confidence": 95
                    },
                    "interpretation": "High confidence quick fix for missing system dependency"
                },
                {
                    "scenario": "CMake can't find package",
                    "error": "CMake Error: Could not find package OpenSSL",
                    "output": {
                        "pattern": "cmake_missing_package", 
                        "suggested_fix": "Install missing package and clear CMake cache",
                        "fix_commands": ["sudo apt install -y libssl-dev", "rm -rf build/CMakeCache.txt", "cmake .."],
                        "fix_type": "medium",
                        "confidence": 88
                    },
                    "interpretation": "Medium confidence fix requiring cache clear"
                }
            ],
            "troubleshooting": {
                "no_suggestions": "Error pattern not recognized, consider extending database",
                "inappropriate_suggestions": "Review pattern matching rules for false positives",
                "outdated_commands": "Update suggestion database for current system versions"
            }
        }
    
    def _load_suggestions_db(self) -> Dict[str, Any]:
        """Load or create fix suggestions database."""
        try:
            if self.suggestions_file.exists():
                with open(self.suggestions_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        
        # Create default database with common patterns
        default_db = self._create_default_suggestions_db()
        self._save_suggestions_db(default_db)
        return default_db
    
    def _save_suggestions_db(self, db: Dict[str, Any]):
        """Save suggestions database to file."""
        try:
            self.suggestions_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.suggestions_file, 'w') as f:
                json.dump(db, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save fix suggestions database: {e}")
    
    def _create_default_suggestions_db(self) -> Dict[str, Any]:
        """Create default database of common build error fixes."""
        return {
            "version": "1.0.0",
            "patterns": {
                # Missing system headers
                "missing_openssl_headers": {
                    "regex_patterns": [
                        r"fatal error: openssl/ssl\.h: No such file or directory",
                        r"openssl/ssl\.h: No such file or directory",
                        r"#include.*openssl.*not found"
                    ],
                    "suggested_fix": "Install OpenSSL development packages",
                    "fix_commands": [
                        "sudo apt update",
                        "sudo apt install -y libssl-dev openssl",
                        "pkg-config --modversion openssl"
                    ],
                    "fix_type": "quick",
                    "confidence": 95,
                    "applicable_systems": ["ubuntu", "debian"]
                },
                "missing_zlib_headers": {
                    "regex_patterns": [
                        r"fatal error: zlib\.h: No such file or directory",
                        r"zlib\.h: No such file or directory"
                    ],
                    "suggested_fix": "Install zlib development package",
                    "fix_commands": [
                        "sudo apt update",
                        "sudo apt install -y zlib1g-dev"
                    ],
                    "fix_type": "quick",
                    "confidence": 95,
                    "applicable_systems": ["ubuntu", "debian"]
                },
                "missing_pthread": {
                    "regex_patterns": [
                        r"undefined reference to `pthread_",
                        r"ld:.*cannot find -lpthread"
                    ],
                    "suggested_fix": "Link pthread library or install development packages",
                    "fix_commands": [
                        "sudo apt install -y libc6-dev",
                        "# Add -lpthread to linker flags in CMakeLists.txt"
                    ],
                    "fix_type": "medium",
                    "confidence": 85,
                    "applicable_systems": ["ubuntu", "debian", "linux"]
                },
                
                # CMake configuration errors
                "cmake_missing_package": {
                    "regex_patterns": [
                        r"CMake Error.*Could not find package (\w+)",
                        r"Could not find a package configuration file provided by \"(\w+)\""
                    ],
                    "suggested_fix": "Install missing package development libraries",
                    "fix_commands": [
                        "# Install development package (example for OpenSSL):",
                        "sudo apt install -y libssl-dev",
                        "rm -rf build/CMakeCache.txt",
                        "cmake -S $(pwd) -B $(pwd)/build"
                    ],
                    "fix_type": "medium",
                    "confidence": 88,
                    "applicable_systems": ["ubuntu", "debian"]
                },
                "cmake_prefix_path": {
                    "regex_patterns": [
                        r"CMake Error.*CMAKE_PREFIX_PATH",
                        r"Set CMAKE_PREFIX_PATH to a directory containing"
                    ],
                    "suggested_fix": "Set CMAKE_PREFIX_PATH to library installation directory",
                    "fix_commands": [
                        "export CMAKE_PREFIX_PATH=/usr/local:/opt/local:$CMAKE_PREFIX_PATH",
                        "cmake -S $(pwd) -B $(pwd)/build",
                        "# Or add -DCMAKE_PREFIX_PATH=/path/to/libraries to cmake command"
                    ],
                    "fix_type": "medium",
                    "confidence": 78,
                    "applicable_systems": ["linux", "macos"]
                },
                "cmake_build_type": {
                    "regex_patterns": [
                        r"CMAKE_BUILD_TYPE is not set",
                        r"Warning.*CMAKE_BUILD_TYPE"
                    ],
                    "suggested_fix": "Set CMAKE_BUILD_TYPE for optimized builds",
                    "fix_commands": [
                        "cmake -DCMAKE_BUILD_TYPE=Release ..",
                        "# Or for debug builds: cmake -DCMAKE_BUILD_TYPE=Debug .."
                    ],
                    "fix_type": "quick",
                    "confidence": 90,
                    "applicable_systems": ["all"]
                },
                
                # Linker errors
                "undefined_reference": {
                    "regex_patterns": [
                        r"undefined reference to `(\w+)",
                        r"ld:.*undefined symbol: (\w+)"
                    ],
                    "suggested_fix": "Link missing library or check function implementation",
                    "fix_commands": [
                        "# Check if library is installed:",
                        "pkg-config --list-all | grep <library_name>",
                        "# Add library to CMakeLists.txt:",
                        "# target_link_libraries(<target> <library_name>)"
                    ],
                    "fix_type": "medium",
                    "confidence": 70,
                    "applicable_systems": ["all"]
                },
                "multiple_definition": {
                    "regex_patterns": [
                        r"multiple definition of `(\w+)",
                        r"duplicate symbol: (\w+)"
                    ],
                    "suggested_fix": "Remove duplicate function definitions or fix header guards",
                    "fix_commands": [
                        "# Check for duplicate function implementations",
                        "grep -r \"function_name\" src/",
                        "# Add header guards or use inline for header-only functions"
                    ],
                    "fix_type": "complex",
                    "confidence": 75,
                    "applicable_systems": ["all"]
                },
                
                # Build system errors
                "make_no_rule": {
                    "regex_patterns": [
                        r"make.*No rule to make target",
                        r"No targets specified and no makefile found"
                    ],
                    "suggested_fix": "Run cmake to generate Makefile or check target names",
                    "fix_commands": [
                        "cd build",
                        "cmake -S $(pwd) -B $(pwd)/build",
                        "make --help | grep -A5 'Available targets'"
                    ],
                    "fix_type": "quick",
                    "confidence": 88,
                    "applicable_systems": ["all"]
                },
                "permission_denied": {
                    "regex_patterns": [
                        r"Permission denied",
                        r"cannot create.*Permission denied"
                    ],
                    "suggested_fix": "Fix file/directory permissions",
                    "fix_commands": [
                        "sudo chown -R $USER:$USER .",
                        "chmod -R 755 .",
                        "# Or run with appropriate permissions"
                    ],
                    "fix_type": "quick",
                    "confidence": 92,
                    "applicable_systems": ["linux", "macos"]
                },
                
                # System resource errors
                "disk_space": {
                    "regex_patterns": [
                        r"No space left on device",
                        r"disk full"
                    ],
                    "suggested_fix": "Free up disk space",
                    "fix_commands": [
                        "df -h .",
                        "du -h --max-depth=1 .",
                        "# Clean build directory: rm -rf build/*",
                        "# Or clean system: sudo apt autoremove && sudo apt autoclean"
                    ],
                    "fix_type": "medium",
                    "confidence": 95,
                    "applicable_systems": ["all"]
                },
                "memory_exhausted": {
                    "regex_patterns": [
                        r"virtual memory exhausted",
                        r"out of memory",
                        r"Cannot allocate memory"
                    ],
                    "suggested_fix": "Reduce parallel jobs or increase system memory",
                    "fix_commands": [
                        "# Reduce parallel jobs:",
                        "make -j2",
                        "# Or increase swap space if available"
                    ],
                    "fix_type": "quick",
                    "confidence": 90,
                    "applicable_systems": ["all"]
                }
            },
            "metadata": {
                "last_updated": "2025-01-01",
                "pattern_count": 11,
                "default_confidence_threshold": 60
            }
        }
    
    def get_fix_suggestions(self, error_message: str, file_path: str = "", 
                          error_category: str = "") -> List[Dict[str, Any]]:
        """Get fix suggestions for an error message.
        
        Args:
            error_message: The error message to analyze
            file_path: File path where error occurred (for context)
            error_category: Error category from categorization
            
        Returns:
            List of fix suggestion dictionaries with confidence scores
        """
        suggestions = []
        
        if "patterns" not in self.suggestions_db:
            return suggestions
        
        # Check each pattern in the database
        for pattern_id, pattern_data in self.suggestions_db["patterns"].items():
            confidence = self._calculate_confidence(error_message, file_path, pattern_data)
            
            if confidence >= 60:  # Minimum confidence threshold
                suggestion = {
                    "pattern": pattern_id,
                    "suggested_fix": pattern_data["suggested_fix"],
                    "fix_commands": pattern_data["fix_commands"],
                    "fix_type": pattern_data["fix_type"],
                    "confidence": confidence
                }
                
                # Add context-specific adjustments
                if error_category:
                    suggestion["error_category"] = error_category
                
                suggestions.append(suggestion)
        
        # Sort by confidence score (highest first)
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Limit to top 3 suggestions
        return suggestions[:3]
    
    def _calculate_confidence(self, error_message: str, file_path: str, 
                            pattern_data: Dict[str, Any]) -> int:
        """Calculate confidence score for a pattern match."""
        base_confidence = pattern_data.get("confidence", 50)
        
        # Check regex pattern matches
        regex_patterns = pattern_data.get("regex_patterns", [])
        pattern_matches = 0
        
        for pattern in regex_patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                pattern_matches += 1
        
        if pattern_matches == 0:
            return 0
        
        # Calculate confidence based on pattern matches
        match_ratio = pattern_matches / len(regex_patterns)
        confidence = int(base_confidence * match_ratio)
        
        # Apply context bonuses/penalties
        confidence += self._apply_context_adjustments(error_message, file_path, pattern_data)
        
        # Ensure confidence is within valid range
        return max(0, min(100, confidence))
    
    def _apply_context_adjustments(self, error_message: str, file_path: str, 
                                 pattern_data: Dict[str, Any]) -> int:
        """Apply context-based confidence adjustments."""
        adjustment = 0
        
        # File extension context
        if file_path:
            file_ext = Path(file_path).suffix.lower()
            
            # C/C++ specific patterns get bonus for C/C++ files
            if file_ext in ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp']:
                if any(keyword in pattern_data.get("suggested_fix", "").lower() 
                      for keyword in ['library', 'header', 'linker']):
                    adjustment += 5
        
        # Error message specificity bonuses
        if len(error_message) > 100:  # More detailed error messages
            adjustment += 3
        
        if "fatal error" in error_message.lower():
            adjustment += 2
        
        # System applicability
        applicable_systems = pattern_data.get("applicable_systems", [])
        if "all" in applicable_systems or "linux" in applicable_systems:
            adjustment += 2
        
        return adjustment
    
    def add_custom_pattern(self, pattern_id: str, pattern_data: Dict[str, Any]) -> bool:
        """Add a custom fix pattern to the database.
        
        Args:
            pattern_id: Unique identifier for the pattern
            pattern_data: Pattern data including regex_patterns, suggested_fix, etc.
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            required_fields = ["regex_patterns", "suggested_fix", "fix_commands", 
                             "fix_type", "confidence"]
            
            # Validate required fields
            for field in required_fields:
                if field not in pattern_data:
                    return False
            
            # Add to database
            if "patterns" not in self.suggestions_db:
                self.suggestions_db["patterns"] = {}
            
            self.suggestions_db["patterns"][pattern_id] = pattern_data
            
            # Update metadata
            if "metadata" not in self.suggestions_db:
                self.suggestions_db["metadata"] = {}
            
            self.suggestions_db["metadata"]["pattern_count"] = \
                len(self.suggestions_db["patterns"])
            
            # Save to file
            self._save_suggestions_db(self.suggestions_db)
            
            return True
            
        except Exception as e:
            print(f"Error adding custom pattern: {e}")
            return False
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about the fix suggestions database."""
        if "patterns" not in self.suggestions_db:
            return {"error": "No patterns in database"}
        
        patterns = self.suggestions_db["patterns"]
        
        # Analyze pattern types
        fix_types = {}
        confidence_distribution = {"high": 0, "medium": 0, "low": 0}
        
        for pattern_data in patterns.values():
            # Count fix types
            fix_type = pattern_data.get("fix_type", "unknown")
            fix_types[fix_type] = fix_types.get(fix_type, 0) + 1
            
            # Count confidence distribution
            confidence = pattern_data.get("confidence", 0)
            if confidence >= 90:
                confidence_distribution["high"] += 1
            elif confidence >= 70:
                confidence_distribution["medium"] += 1
            else:
                confidence_distribution["low"] += 1
        
        return {
            "total_patterns": len(patterns),
            "fix_types": fix_types,
            "confidence_distribution": confidence_distribution,
            "version": self.suggestions_db.get("metadata", {}).get("version", "unknown"),
            "last_updated": self.suggestions_db.get("metadata", {}).get("last_updated", "unknown")
        }
    
    def test_pattern_match(self, pattern_id: str, test_error: str) -> Dict[str, Any]:
        """Test if a specific pattern matches a test error message.
        
        Args:
            pattern_id: Pattern identifier to test
            test_error: Error message to test against
            
        Returns:
            Test results including confidence and match details
        """
        if ("patterns" not in self.suggestions_db or 
            pattern_id not in self.suggestions_db["patterns"]):
            return {"error": f"Pattern '{pattern_id}' not found"}
        
        pattern_data = self.suggestions_db["patterns"][pattern_id]
        confidence = self._calculate_confidence(test_error, "", pattern_data)
        
        # Check which regex patterns matched
        matched_patterns = []
        for pattern in pattern_data.get("regex_patterns", []):
            if re.search(pattern, test_error, re.IGNORECASE):
                matched_patterns.append(pattern)
        
        return {
            "pattern_id": pattern_id,
            "confidence": confidence,
            "matched_patterns": matched_patterns,
            "would_suggest": confidence >= 60,
            "suggestion": pattern_data["suggested_fix"] if confidence >= 60 else None
        }
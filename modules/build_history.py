"""
Build History Manager Module - Feature 2: Build Time Prediction & ETA

Learns build patterns over time to provide accurate duration estimates and completion times.
Maintains rolling windows of historical data with intelligent pattern matching.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class BuildHistoryManager:
    """Manages build history for ETA prediction and pattern recognition."""
    
    def __init__(self, history_file: str = None):
        """Initialize build history manager.
        
        Args:
            history_file: Path to history storage file. If None, uses default location.
        """
        if history_file is None:
            history_file = Path.cwd() / "build_history.json"
        
        self.history_file = Path(history_file)
        self.history_data = self._load_history()
        
        # Self-documentation metadata for AI assistants
        self.help_data = {
            "name": "Build History Manager",
            "description": "Learns build patterns to provide accurate duration estimates and completion times",
            "version": "1.0.0",
            "features": [
                "Target-specific duration learning with pattern matching",
                "Intelligent ETA prediction with confidence scores",
                "Rolling window data management (last 50 builds per target)",
                "Handles both individual packages and full system builds",
                "Automatic outlier detection and cleanup"
            ],
            "configuration": {
                "max_history_per_target": {
                    "type": "int",
                    "default": 50,
                    "description": "Maximum build records kept per target"
                },
                "min_samples_for_prediction": {
                    "type": "int",
                    "default": 3,
                    "description": "Minimum builds needed before predictions"
                },
                "outlier_threshold": {
                    "type": "float",
                    "default": 2.5,
                    "description": "Standard deviations for outlier detection"
                }
            },
            "output_format": {
                "eta": "Duration + completion time (e.g., '45s@14:28')",
                "confidence": "Prediction confidence 0-100%",
                "sample_size": "Number of historical builds used"
            },
            "token_cost": "4-6 tokens per build response (when included)",
            "ai_metadata": {
                "purpose": "Provide accurate build time estimates for planning and optimization",
                "when_to_use": "After 3+ historical builds for the same target pattern",
                "interpretation": {
                    "short_eta": "<1 minute typically indicates incremental/package builds",
                    "long_eta": ">5 minutes suggests full system builds or complex changes",
                    "high_confidence": ">80% confidence indicates stable, predictable builds"
                },
                "recommendations": {
                    "variable_times": "Inconsistent durations may indicate caching issues",
                    "increasing_trend": "Gradually longer builds may indicate technical debt",
                    "outliers": "Occasional long builds may indicate system resource issues"
                }
            },
            "examples": [
                {
                    "scenario": "Package-specific build",
                    "input": ["package_websocket/fast"],
                    "output": {"eta": "45s@14:28", "confidence": 85},
                    "interpretation": "Consistent 45-second builds, high confidence"
                },
                {
                    "scenario": "Full system build",
                    "input": [],
                    "output": {"eta": "320s@14:35", "confidence": 72},
                    "interpretation": "~5 minute build, moderate confidence due to variability"
                },
                {
                    "scenario": "First build of target",
                    "input": ["new_package/fast"],
                    "output": None,
                    "interpretation": "No prediction available - insufficient historical data"
                }
            ],
            "troubleshooting": {
                "no_predictions": "Need 3+ historical builds for reliable predictions",
                "wildly_inaccurate": "Clear history or check for system changes",
                "file_permissions": "Ensure write access to build_history.json location"
            }
        }
    
    def _load_history(self) -> Dict[str, Any]:
        """Load build history from file."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    # Ensure required structure
                    if "builds" not in data:
                        data["builds"] = {}
                    if "metadata" not in data:
                        data["metadata"] = {"last_cleanup": time.time()}
                    return data
        except (json.JSONDecodeError, IOError):
            pass
        
        # Return default structure
        return {
            "builds": {},
            "metadata": {
                "last_cleanup": time.time(),
                "total_builds_recorded": 0,
                "version": "1.0.0"
            }
        }
    
    def _save_history(self):
        """Save build history to file."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.history_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save build history: {e}")
    
    def _get_target_key(self, targets: List[str]) -> str:
        """Generate a normalized key for target pattern matching."""
        if not targets:
            return "full_build"
        
        # Sort targets to ensure consistent keys
        sorted_targets = sorted(targets)
        
        # Group similar patterns
        if len(sorted_targets) == 1:
            target = sorted_targets[0]
            if target.endswith("/fast"):
                # Package builds
                package_name = target.replace("/fast", "").replace("package_", "")
                return f"package_{package_name}"
            elif target in ["all", "install"]:
                return "full_build"
            else:
                return f"target_{target}"
        else:
            # Multiple targets - create pattern
            if all(t.startswith("package_") for t in sorted_targets):
                return f"multi_package_{len(sorted_targets)}"
            else:
                return f"multi_target_{len(sorted_targets)}"
    
    def record_build_duration(self, targets: List[str], duration: float):
        """Record a successful build duration for learning."""
        target_key = self._get_target_key(targets)
        current_time = time.time()
        
        # Initialize target history if needed
        if target_key not in self.history_data["builds"]:
            self.history_data["builds"][target_key] = []
        
        # Add new build record
        build_record = {
            "duration": duration,
            "timestamp": current_time,
            "targets": targets.copy(),
            "success": True
        }
        
        self.history_data["builds"][target_key].append(build_record)
        
        # Maintain rolling window (keep last 50 builds per target)
        max_history = 50
        if len(self.history_data["builds"][target_key]) > max_history:
            self.history_data["builds"][target_key] = \
                self.history_data["builds"][target_key][-max_history:]
        
        # Update metadata
        self.history_data["metadata"]["total_builds_recorded"] = \
            self.history_data["metadata"].get("total_builds_recorded", 0) + 1
        self.history_data["metadata"]["last_update"] = current_time
        
        # Periodic cleanup
        if current_time - self.history_data["metadata"].get("last_cleanup", 0) > 86400:  # 24 hours
            self._cleanup_old_data()
            self.history_data["metadata"]["last_cleanup"] = current_time
        
        self._save_history()
    
    def get_predicted_duration(self, targets: List[str]) -> Optional[float]:
        """Get predicted build duration based on historical data."""
        target_key = self._get_target_key(targets)
        
        if target_key not in self.history_data["builds"]:
            return None
        
        build_history = self.history_data["builds"][target_key]
        
        # Need at least 3 builds for reliable prediction
        if len(build_history) < 3:
            return None
        
        # Get recent builds (last 10) for more accurate prediction
        recent_builds = build_history[-10:]
        durations = [build["duration"] for build in recent_builds]
        
        # Remove obvious outliers (>2.5 standard deviations)
        if len(durations) >= 5:
            durations = self._remove_outliers(durations)
        
        if len(durations) < 3:
            return None
        
        # Calculate weighted average (more recent builds have higher weight)
        weights = [(i + 1) * 0.1 + 0.5 for i in range(len(durations))]
        weighted_sum = sum(d * w for d, w in zip(durations, weights))
        weight_sum = sum(weights)
        
        predicted_duration = weighted_sum / weight_sum
        
        # Apply trend adjustment if we have enough data
        if len(durations) >= 5:
            trend_factor = self._calculate_trend_factor(durations)
            predicted_duration *= trend_factor
        
        return predicted_duration
    
    def _remove_outliers(self, durations: List[float], threshold: float = 2.5) -> List[float]:
        """Remove statistical outliers from duration list."""
        if len(durations) < 3:
            return durations
        
        mean_duration = sum(durations) / len(durations)
        variance = sum((d - mean_duration) ** 2 for d in durations) / len(durations)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return durations
        
        # Keep values within threshold standard deviations
        filtered = [d for d in durations 
                   if abs(d - mean_duration) <= threshold * std_dev]
        
        # Always keep at least 3 values
        if len(filtered) < 3:
            return durations
        
        return filtered
    
    def _calculate_trend_factor(self, durations: List[float]) -> float:
        """Calculate trend factor for duration prediction."""
        if len(durations) < 3:
            return 1.0
        
        # Simple linear trend calculation
        n = len(durations)
        x_values = list(range(n))
        y_values = durations
        
        # Calculate slope of linear trend
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 1.0
        
        slope = numerator / denominator
        
        # Convert slope to trend factor (clamp to reasonable range)
        trend_factor = 1.0 + (slope * 0.1)  # 10% adjustment per unit slope
        return max(0.5, min(2.0, trend_factor))  # Clamp between 0.5x and 2x
    
    def _cleanup_old_data(self):
        """Clean up old build data to prevent unbounded growth."""
        current_time = time.time()
        max_age_seconds = 30 * 24 * 3600  # 30 days
        
        for target_key in list(self.history_data["builds"].keys()):
            builds = self.history_data["builds"][target_key]
            
            # Remove builds older than max_age
            recent_builds = [
                build for build in builds
                if current_time - build.get("timestamp", 0) <= max_age_seconds
            ]
            
            # Keep at least 5 builds if available
            if len(recent_builds) < 5 and len(builds) >= 5:
                recent_builds = builds[-5:]
            
            if recent_builds:
                self.history_data["builds"][target_key] = recent_builds
            else:
                # Remove target with no recent builds
                del self.history_data["builds"][target_key]
    
    def get_build_statistics(self, targets: List[str] = None) -> Dict[str, Any]:
        """Get build statistics for analysis."""
        if targets is None:
            # Return overall statistics
            total_builds = sum(len(builds) for builds in self.history_data["builds"].values())
            total_targets = len(self.history_data["builds"])
            
            return {
                "total_builds_recorded": total_builds,
                "total_targets": total_targets,
                "targets": list(self.history_data["builds"].keys()),
                "last_cleanup": self.history_data["metadata"].get("last_cleanup"),
                "version": self.history_data["metadata"].get("version", "1.0.0")
            }
        else:
            # Return statistics for specific target
            target_key = self._get_target_key(targets)
            
            if target_key not in self.history_data["builds"]:
                return {"error": "No historical data for this target"}
            
            builds = self.history_data["builds"][target_key]
            durations = [build["duration"] for build in builds]
            
            if durations:
                avg_duration = sum(durations) / len(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                
                return {
                    "target_key": target_key,
                    "build_count": len(builds),
                    "average_duration": avg_duration,
                    "min_duration": min_duration,
                    "max_duration": max_duration,
                    "recent_builds": builds[-5:] if len(builds) >= 5 else builds,
                    "prediction_available": len(builds) >= 3
                }
            else:
                return {"error": "No duration data available"}
    
    def clear_history(self, targets: List[str] = None):
        """Clear build history for specific targets or all targets."""
        if targets is None:
            # Clear all history
            self.history_data["builds"] = {}
            self.history_data["metadata"]["total_builds_recorded"] = 0
        else:
            # Clear specific target
            target_key = self._get_target_key(targets)
            if target_key in self.history_data["builds"]:
                del self.history_data["builds"][target_key]
        
        self._save_history()
"""
Health Score Tracker Module - Feature 6: Build Health Scoring

Analyzes build patterns over time to calculate health scores (0-100) based on
success rate, performance trends, warning patterns, and resource efficiency.
"""

import json
import time
import statistics
from pathlib import Path
from typing import Dict, Any, List, Optional


class HealthScoreTracker:
    """Tracks build health metrics and calculates comprehensive health scores."""
    
    def __init__(self, tracker_file: str = None):
        """Initialize health score tracker.
        
        Args:
            tracker_file: Path to tracker storage file. If None, uses default location.
        """
        if tracker_file is None:
            tracker_file = Path.cwd() / "health_tracker.json"
            
        self.tracker_file = Path(tracker_file)
        self.tracker_data = self._load_tracker_data()
        
        # Self-documentation metadata for AI assistants
        self.help_data = {
            "name": "Health Score Tracker",
            "description": "Analyzes build patterns to calculate comprehensive health scores (0-100)",
            "version": "1.0.0", 
            "features": [
                "Multi-factor health scoring: success rate, performance, warnings, resources",
                "Target-specific health tracking with trend analysis",
                "Historical health data with rolling windows (last 20 builds)",
                "Performance regression detection and alerting",
                "Warning pattern analysis and impact assessment"
            ],
            "configuration": {
                "health_window_size": {
                    "type": "int",
                    "default": 20,
                    "description": "Number of recent builds to consider for health calculation"
                },
                "min_builds_for_score": {
                    "type": "int", 
                    "default": 5,
                    "description": "Minimum builds needed before calculating health score"
                },
                "performance_weight": {
                    "type": "float",
                    "default": 0.3,
                    "description": "Weight of performance factor in health score"
                },
                "success_weight": {
                    "type": "float",
                    "default": 0.4,
                    "description": "Weight of success rate factor in health score"
                },
                "warning_weight": {
                    "type": "float",
                    "default": 0.2,
                    "description": "Weight of warning factor in health score"
                },
                "resource_weight": {
                    "type": "float",
                    "default": 0.1,
                    "description": "Weight of resource efficiency factor in health score"
                }
            },
            "output_format": {
                "health_score": "Integer 0-100 (100 = perfect health)",
                "health_trend": "improving, stable, or declining",
                "primary_issues": "Array of main health concerns"
            },
            "token_cost": "3-5 tokens per build response (when included)",
            "ai_metadata": {
                "purpose": "Provide overall build system health assessment for optimization decisions",
                "when_to_use": "After 5+ builds to establish baseline health metrics",
                "interpretation": {
                    "excellent_health": "90-100: Consistently successful, fast, low warnings",
                    "good_health": "70-89: Generally reliable with minor issues",
                    "moderate_health": "50-69: Some problems, needs attention",
                    "poor_health": "<50: Significant issues requiring investigation"
                },
                "recommendations": {
                    "declining_health": "Investigate recent changes causing degradation",
                    "performance_issues": "Focus on build time optimization",
                    "warning_increases": "Address growing warning patterns",
                    "resource_inefficiency": "Optimize resource usage during builds"
                }
            },
            "examples": [
                {
                    "scenario": "Healthy project",
                    "output": {"health_score": 92, "health_trend": "stable"},
                    "interpretation": "Excellent health, builds consistently fast and successful"
                },
                {
                    "scenario": "Performance regression",
                    "output": {"health_score": 68, "health_trend": "declining", "primary_issues": ["performance_regression"]},
                    "interpretation": "Build times increasing, investigate recent changes"
                },
                {
                    "scenario": "Warning accumulation",
                    "output": {"health_score": 74, "health_trend": "declining", "primary_issues": ["warning_increase"]},
                    "interpretation": "Growing warning count, address before they become errors"
                }
            ],
            "troubleshooting": {
                "no_health_score": "Need 5+ builds to calculate reliable health score",
                "unstable_scores": "Increase health window size for more stable metrics",
                "always_low_score": "Review build configuration and dependency management"
            }
        }
    
    def _load_tracker_data(self) -> Dict[str, Any]:
        """Load health tracker data from file."""
        try:
            if self.tracker_file.exists():
                with open(self.tracker_file, 'r') as f:
                    data = json.load(f)
                    # Ensure required structure
                    if "build_metrics" not in data:
                        data["build_metrics"] = {}
                    if "health_history" not in data:
                        data["health_history"] = {}
                    if "metadata" not in data:
                        data["metadata"] = {}
                    return data
        except (json.JSONDecodeError, IOError):
            pass
        
        # Return default structure
        return {
            "build_metrics": {},
            "health_history": {},
            "metadata": {
                "version": "1.0.0",
                "total_builds_tracked": 0,
                "last_calculation": 0
            }
        }
    
    def _save_tracker_data(self):
        """Save tracker data to file."""
        try:
            self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tracker_file, 'w') as f:
                json.dump(self.tracker_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save health tracker data: {e}")
    
    def record_build_completion(self, targets: List[str], success: bool, 
                              duration: float, predicted_duration: Optional[float] = None,
                              warning_count: int = 0, resource_usage: Optional[Dict[str, Any]] = None):
        """Record build completion metrics for health tracking."""
        target_key = self._get_target_key(targets)
        current_time = time.time()
        
        # Initialize target tracking if needed
        if target_key not in self.tracker_data["build_metrics"]:
            self.tracker_data["build_metrics"][target_key] = []
        
        # Extract resource metrics if available
        cpu_usage = None
        memory_usage = None
        if resource_usage:
            res_str = resource_usage.get('res', '')
            if '%/' in res_str:
                try:
                    cpu_str, mem_str = res_str.split('%/')
                    cpu_usage = int(cpu_str.replace('%', ''))
                    if mem_str.endswith('g'):
                        memory_usage = float(mem_str.replace('g', '')) * 1024  # Convert to MB
                    else:
                        memory_usage = float(mem_str.replace('m', ''))
                except (ValueError, IndexError):
                    pass
        
        # Create build metric record
        metric_record = {
            "timestamp": current_time,
            "success": success,
            "duration": duration,
            "predicted_duration": predicted_duration,
            "prediction_accuracy": self._calculate_prediction_accuracy(duration, predicted_duration),
            "warning_count": warning_count,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "targets": targets.copy()
        }
        
        # Add to metrics
        self.tracker_data["build_metrics"][target_key].append(metric_record)
        
        # Maintain rolling window (keep last 20 builds per target)
        max_history = 20
        if len(self.tracker_data["build_metrics"][target_key]) > max_history:
            self.tracker_data["build_metrics"][target_key] = \
                self.tracker_data["build_metrics"][target_key][-max_history:]
        
        # Update metadata
        self.tracker_data["metadata"]["total_builds_tracked"] = \
            self.tracker_data["metadata"].get("total_builds_tracked", 0) + 1
        self.tracker_data["metadata"]["last_update"] = current_time
        
        self._save_tracker_data()
    
    def calculate_health_score(self, targets: List[str]) -> Optional[int]:
        """Calculate comprehensive health score (0-100) for targets."""
        target_key = self._get_target_key(targets)
        
        if target_key not in self.tracker_data["build_metrics"]:
            return None
        
        metrics = self.tracker_data["build_metrics"][target_key]
        
        # Need at least 5 builds for reliable health score
        if len(metrics) < 5:
            return None
        
        # Calculate component scores
        success_score = self._calculate_success_score(metrics)
        performance_score = self._calculate_performance_score(metrics) 
        warning_score = self._calculate_warning_score(metrics)
        resource_score = self._calculate_resource_score(metrics)
        
        # Weighted health score calculation
        weights = {
            'success': 0.4,
            'performance': 0.3,
            'warnings': 0.2,
            'resources': 0.1
        }
        
        health_score = (
            success_score * weights['success'] +
            performance_score * weights['performance'] + 
            warning_score * weights['warnings'] +
            resource_score * weights['resources']
        )
        
        # Record health score in history
        current_time = time.time()
        if target_key not in self.tracker_data["health_history"]:
            self.tracker_data["health_history"][target_key] = []
        
        self.tracker_data["health_history"][target_key].append({
            "timestamp": current_time,
            "health_score": int(health_score),
            "component_scores": {
                "success": success_score,
                "performance": performance_score,
                "warnings": warning_score,
                "resources": resource_score
            }
        })
        
        # Maintain rolling window for health history
        if len(self.tracker_data["health_history"][target_key]) > 10:
            self.tracker_data["health_history"][target_key] = \
                self.tracker_data["health_history"][target_key][-10:]
        
        self.tracker_data["metadata"]["last_calculation"] = current_time
        self._save_tracker_data()
        
        return int(health_score)
    
    def _calculate_success_score(self, metrics: List[Dict[str, Any]]) -> float:
        """Calculate success rate score (0-100)."""
        if not metrics:
            return 0.0
        
        successful_builds = sum(1 for m in metrics if m["success"])
        success_rate = successful_builds / len(metrics)
        
        # Convert to 0-100 scale with slight penalty for any failures
        if success_rate == 1.0:
            return 100.0
        elif success_rate >= 0.9:
            return 85.0 + (success_rate - 0.9) * 150  # 85-100 range
        elif success_rate >= 0.7:
            return 60.0 + (success_rate - 0.7) * 125  # 60-85 range
        else:
            return success_rate * 85.0  # 0-60 range
    
    def _calculate_performance_score(self, metrics: List[Dict[str, Any]]) -> float:
        """Calculate performance score based on duration trends."""
        if not metrics:
            return 0.0
        
        durations = [m["duration"] for m in metrics if m["duration"] > 0]
        if len(durations) < 2:
            return 80.0  # Neutral score for insufficient data
        
        # Calculate trend
        recent_durations = durations[-5:] if len(durations) >= 5 else durations
        older_durations = durations[:-5] if len(durations) >= 5 else []
        
        if older_durations:
            recent_avg = statistics.mean(recent_durations)
            older_avg = statistics.mean(older_durations)
            performance_ratio = older_avg / recent_avg if recent_avg > 0 else 1.0
            
            # Score based on performance trend
            if performance_ratio > 1.2:  # Getting faster
                return 95.0
            elif performance_ratio > 1.05:  # Slightly faster
                return 85.0
            elif performance_ratio > 0.95:  # Stable
                return 80.0
            elif performance_ratio > 0.8:  # Slightly slower
                return 65.0
            else:  # Getting slower
                return 40.0
        
        # Check prediction accuracy if available
        accurate_predictions = [m for m in metrics if m.get("prediction_accuracy", 0) > 0.8]
        if len(accurate_predictions) >= 3:
            avg_accuracy = statistics.mean([m["prediction_accuracy"] for m in accurate_predictions])
            return 70.0 + (avg_accuracy * 30)  # 70-100 based on accuracy
        
        return 75.0  # Default neutral performance score
    
    def _calculate_warning_score(self, metrics: List[Dict[str, Any]]) -> float:
        """Calculate warning score based on warning trends."""
        if not metrics:
            return 100.0
        
        warning_counts = [m.get("warning_count", 0) for m in metrics]
        
        if not any(warning_counts):
            return 100.0  # No warnings = perfect score
        
        # Calculate recent trend
        recent_warnings = warning_counts[-5:] if len(warning_counts) >= 5 else warning_counts
        avg_warnings = statistics.mean(recent_warnings)
        
        # Score based on average warning count
        if avg_warnings == 0:
            return 100.0
        elif avg_warnings <= 2:
            return 90.0
        elif avg_warnings <= 5:
            return 75.0
        elif avg_warnings <= 10:
            return 60.0
        elif avg_warnings <= 20:
            return 40.0
        else:
            return 20.0
    
    def _calculate_resource_score(self, metrics: List[Dict[str, Any]]) -> float:
        """Calculate resource efficiency score."""
        cpu_values = [m.get("cpu_usage") for m in metrics if m.get("cpu_usage") is not None]
        memory_values = [m.get("memory_usage") for m in metrics if m.get("memory_usage") is not None]
        
        if not cpu_values and not memory_values:
            return 80.0  # Neutral score when no resource data
        
        score = 100.0
        
        # CPU efficiency scoring
        if cpu_values:
            avg_cpu = statistics.mean(cpu_values)
            if avg_cpu > 95:  # Very high CPU usage
                score -= 20
            elif avg_cpu > 85:  # High CPU usage
                score -= 10
            elif avg_cpu < 30:  # Very low CPU usage (potentially inefficient)
                score -= 5
        
        # Memory efficiency scoring  
        if memory_values:
            avg_memory_gb = statistics.mean(memory_values) / 1024
            if avg_memory_gb > 8:  # Very high memory usage
                score -= 20
            elif avg_memory_gb > 4:  # High memory usage
                score -= 10
            elif avg_memory_gb > 2:  # Moderate memory usage
                score -= 5
        
        return max(0.0, score)
    
    def _calculate_prediction_accuracy(self, actual_duration: float, 
                                     predicted_duration: Optional[float]) -> float:
        """Calculate how accurate the duration prediction was."""
        if predicted_duration is None or predicted_duration <= 0:
            return 0.0
        
        if actual_duration <= 0:
            return 0.0
        
        # Calculate accuracy as 1 - (relative error)
        relative_error = abs(actual_duration - predicted_duration) / predicted_duration
        accuracy = max(0.0, 1.0 - relative_error)
        
        return accuracy
    
    def _get_target_key(self, targets: List[str]) -> str:
        """Generate consistent target key for tracking."""
        if not targets:
            return "default_build"
        
        # Sort targets for consistency
        sorted_targets = sorted(targets)
        return "_".join(sorted_targets).replace("/", "_").replace("package_", "pkg_")
    
    def get_health_trend(self, targets: List[str]) -> Optional[str]:
        """Get health trend analysis for targets."""
        target_key = self._get_target_key(targets)
        
        if target_key not in self.tracker_data["health_history"]:
            return None
        
        history = self.tracker_data["health_history"][target_key]
        if len(history) < 3:
            return "insufficient_data"
        
        # Analyze recent trend (last 5 scores)
        recent_scores = [h["health_score"] for h in history[-5:]]
        
        if len(recent_scores) < 3:
            return "stable"
        
        # Calculate trend using linear regression slope
        x_values = list(range(len(recent_scores)))
        y_values = recent_scores
        
        n = len(recent_scores)
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Classify trend based on slope
        if slope > 2.0:
            return "improving"
        elif slope < -2.0:
            return "declining" 
        else:
            return "stable"
    
    def get_health_analysis(self, targets: List[str]) -> Dict[str, Any]:
        """Get comprehensive health analysis for targets."""
        target_key = self._get_target_key(targets)
        
        if target_key not in self.tracker_data["build_metrics"]:
            return {"error": "No health data available for these targets"}
        
        metrics = self.tracker_data["build_metrics"][target_key]
        health_score = self.calculate_health_score(targets)
        health_trend = self.get_health_trend(targets)
        
        # Identify primary issues
        primary_issues = []
        if len(metrics) >= 5:
            recent_metrics = metrics[-5:]
            
            # Check success rate
            recent_failures = sum(1 for m in recent_metrics if not m["success"])
            if recent_failures >= 2:
                primary_issues.append("reliability_issues")
            
            # Check performance regression
            if len(metrics) >= 10:
                recent_durations = [m["duration"] for m in metrics[-5:]]
                older_durations = [m["duration"] for m in metrics[-10:-5]]
                if recent_durations and older_durations:
                    recent_avg = statistics.mean(recent_durations)
                    older_avg = statistics.mean(older_durations)
                    if recent_avg > older_avg * 1.2:
                        primary_issues.append("performance_regression")
            
            # Check warning trends
            recent_warnings = [m.get("warning_count", 0) for m in recent_metrics]
            if statistics.mean(recent_warnings) > 5:
                primary_issues.append("warning_increase")
        
        return {
            "health_score": health_score,
            "health_trend": health_trend,
            "primary_issues": primary_issues,
            "build_count": len(metrics),
            "success_rate": sum(1 for m in metrics if m["success"]) / len(metrics) if metrics else 0,
            "average_duration": statistics.mean([m["duration"] for m in metrics]) if metrics else 0,
            "recent_warnings": statistics.mean([m.get("warning_count", 0) for m in metrics[-5:]]) if len(metrics) >= 5 else 0
        }
    
    def clear_health_data(self, targets: List[str] = None):
        """Clear health tracking data for specific targets or all targets."""
        if targets is None:
            # Clear all health data
            self.tracker_data["build_metrics"] = {}
            self.tracker_data["health_history"] = {}
            self.tracker_data["metadata"]["total_builds_tracked"] = 0
        else:
            # Clear specific target
            target_key = self._get_target_key(targets)
            if target_key in self.tracker_data["build_metrics"]:
                del self.tracker_data["build_metrics"][target_key]
            if target_key in self.tracker_data["health_history"]:
                del self.tracker_data["health_history"][target_key]
        
        self._save_tracker_data()
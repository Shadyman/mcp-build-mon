"""
Build Session Module - Active build session tracking and management

Track active build sessions with ETA prediction, incremental build intelligence,
resource monitoring, and dependency change tracking.
"""

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from modules.resource_monitor import ResourceMonitor

@dataclass
class BuildSession:
    """Track active build sessions."""
    id: str
    process: Optional[subprocess.Popen]
    status: str  # "running", "completed", "failed", "background"
    start_time: float
    targets: List[str]
    cmake_result: Optional[Dict[str, Any]]
    make_result: Optional[Dict[str, Any]]
    status_file: Optional[str]
    output_lines: List[str]
    # ETA prediction fields
    predicted_duration: Optional[float] = None
    estimated_completion_time: Optional[str] = None
    # Incremental build fields
    change_data: Optional[Dict[str, Any]] = None
    build_recommendation: Optional[str] = None
    change_impact: Optional[str] = None
    # Resource monitoring fields (Feature 5)
    resource_monitor: Optional[ResourceMonitor] = None
    final_resource_usage: Optional[Dict[str, Any]] = None
    # Dependency tracking fields (Feature 7)
    dependency_changes: Optional[List[Dict[str, Any]]] = None
    
    def calculate_eta(self, current_time: float = None) -> Optional[str]:
        """Calculate estimated completion time based on prediction and current progress."""
        if self.predicted_duration is None:
            return None
        
        if current_time is None:
            current_time = time.time()
        
        # For background builds, try to get progress percentage if available
        progress_percentage = self._get_progress_percentage()
        
        if progress_percentage is not None and progress_percentage > 0:
            # Adjust ETA based on current progress
            remaining_percentage = (100 - progress_percentage) / 100
            remaining_time = self.predicted_duration * remaining_percentage
            completion_time = current_time + remaining_time
        else:
            # Use original prediction
            completion_time = self.start_time + self.predicted_duration
        
        # Return ISO format timestamp
        return datetime.fromtimestamp(completion_time).isoformat() + "Z"
    
    def _get_progress_percentage(self) -> Optional[float]:
        """Extract progress percentage from status file or output."""
        if self.status_file and os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    status_data = json.load(f)
                    progress_str = status_data.get("progress", "")
                    if progress_str and "[" in progress_str and "%" in progress_str:
                        # Extract percentage from "[XX%]" format
                        match = re.search(r'\[(\d+)%\]', progress_str)
                        if match:
                            return float(match.group(1))
            except:
                pass
        
        return None

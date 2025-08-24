"""
Resource Monitor Module - Feature 5: Resource Usage Monitoring

Ultra-compact CPU and memory usage monitoring during builds with minimal token overhead.
Provides background sampling with peak tracking and token-efficient JSON response format.
"""

import time
import threading
from typing import Dict, Any, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class ResourceMonitor:
    """Lightweight resource usage monitoring during builds."""
    
    def __init__(self, sample_interval: float = 3.0):
        """Initialize with sampling interval in seconds."""
        self.sample_interval = sample_interval
        self.sampling_active = False
        self.samples = []
        self.peak_cpu = 0.0
        self.peak_memory_mb = 0.0
        self.sampling_thread = None
        self.lock = threading.Lock()
        self.start_time = None
        
        # Self-documentation metadata for AI assistants and help system
        self.help_data = {
            "name": "Resource Monitor",
            "description": "Ultra-compact CPU and memory monitoring during builds with minimal token overhead",
            "version": "1.0.0",
            "features": [
                "Background resource sampling every 2-5 seconds",
                "Peak usage tracking with smart thresholds",
                "Ultra-compact JSON format: 'res': '85%/1.5g'",
                "Conditional inclusion based on meaningful usage",
                "Automatic thread management and cleanup"
            ],
            "configuration": {
                "sample_interval": {
                    "type": "float",
                    "default": 2.5,
                    "range": [0.5, 10.0],
                    "description": "Sampling frequency in seconds"
                },
                "min_cpu_threshold": {
                    "type": "float", 
                    "default": 50.0,
                    "description": "Minimum CPU% to include in response"
                },
                "min_memory_threshold": {
                    "type": "int",
                    "default": 500,
                    "description": "Minimum memory MB to include in response"
                }
            },
            "output_format": {
                "res": "CPU%/Memory format (e.g., '85%/1.5g' or '75%/512m')",
                "pk": "Peak values when significantly different (e.g., '95/2g')"
            },
            "token_cost": "4-8 tokens per build response (when included)",
            "ai_metadata": {
                "purpose": "Monitor resource usage during builds to identify bottlenecks",
                "when_to_use": "Automatically enabled for builds longer than 30 seconds",
                "interpretation": {
                    "high_cpu": ">80% indicates CPU-bound compilation",
                    "high_memory": ">1GB indicates memory-intensive build", 
                    "peaks": "Significant spikes suggest resource bottlenecks"
                },
                "recommendations": {
                    "high_resource_usage": "Consider reducing parallel jobs (-j flag)",
                    "memory_spikes": "Monitor for memory leaks or large object compilation",
                    "sustained_high_cpu": "Normal for intensive compilation"
                }
            },
            "examples": [
                {
                    "scenario": "Light compilation",
                    "output": {"res": "45%/512m"},
                    "interpretation": "Normal resource usage, no concerns"
                },
                {
                    "scenario": "Heavy parallel build",
                    "output": {"res": "85%/1.5g", "pk": "95/2g"},
                    "interpretation": "High resource usage with spikes, consider fewer parallel jobs"
                },
                {
                    "scenario": "Memory-intensive build",
                    "output": {"res": "60%/3g"},
                    "interpretation": "High memory usage, possible large object compilation"
                }
            ],
            "troubleshooting": {
                "psutil_not_available": "Resource monitoring disabled - install psutil",
                "no_data_collected": "Build too short (<30s) or no meaningful resource usage",
                "thread_errors": "Sampling thread failed - check system permissions"
            }
        }
    
    def start_sampling(self):
        """Start background resource sampling."""
        if not HAS_PSUTIL:
            return False
            
        with self.lock:
            if self.sampling_active:
                return True  # Already sampling
            
            self.sampling_active = True
            self.samples = []
            self.peak_cpu = 0.0
            self.peak_memory_mb = 0.0
            self.start_time = time.time()
            
            # Start sampling thread
            self.sampling_thread = threading.Thread(target=self._sampling_loop, daemon=True)
            self.sampling_thread.start()
            
        return True
    
    def stop_sampling(self):
        """Stop resource sampling and return final metrics."""
        if not HAS_PSUTIL:
            return None
            
        with self.lock:
            if not self.sampling_active:
                return None
                
            self.sampling_active = False
            
            # Wait for sampling thread to finish
            if self.sampling_thread and self.sampling_thread.is_alive():
                self.sampling_thread.join(timeout=1.0)
            
            return self._calculate_final_metrics()
    
    def _sampling_loop(self):
        """Background sampling loop."""
        try:
            while self.sampling_active:
                try:
                    # Get current resource usage
                    cpu_percent = psutil.cpu_percent(interval=None)
                    memory_info = psutil.virtual_memory()
                    memory_mb = memory_info.used / (1024 * 1024)  # Convert to MB
                    
                    with self.lock:
                        if self.sampling_active:  # Double-check while holding lock
                            # Store sample
                            self.samples.append({
                                'timestamp': time.time(),
                                'cpu_percent': cpu_percent,
                                'memory_mb': memory_mb
                            })
                            
                            # Update peaks
                            self.peak_cpu = max(self.peak_cpu, cpu_percent)
                            self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
                            
                            # Limit sample history to prevent memory growth (keep last 100 samples)
                            if len(self.samples) > 100:
                                self.samples = self.samples[-100:]
                    
                    # Sleep for sampling interval
                    time.sleep(self.sample_interval)
                    
                except (psutil.Error, OSError) as e:
                    # Silently handle psutil errors - continue sampling
                    time.sleep(self.sample_interval)
                    continue
                    
        except Exception:
            # Silent failure - don't disrupt build monitoring
            pass
    
    def _calculate_final_metrics(self) -> Dict[str, Any]:
        """Calculate final resource usage metrics - ultra-compact format for <10 tokens."""
        if not self.samples:
            return None
            
        # Calculate average CPU usage (weighted by time)
        total_cpu = 0.0
        total_memory = 0.0
        sample_count = len(self.samples)
        
        for sample in self.samples:
            total_cpu += sample['cpu_percent']
            total_memory += sample['memory_mb']
        
        avg_cpu = total_cpu / sample_count if sample_count > 0 else 0.0
        avg_memory = total_memory / sample_count if sample_count > 0 else 0.0
        
        # ULTRA-COMPACT FORMAT: Single string combining CPU and memory
        # Format: "cpu%/memGB" or "cpu%/memMB" 
        # Examples: "85%/1.5g" (7 chars), "75%/512m" (8 chars)
        
        # Memory formatting - ultra-compact
        if avg_memory >= 1024:
            # Use 'g' for GB, strip trailing zeros
            mem_val = avg_memory / 1024
            if mem_val == int(mem_val):
                mem_str = f"{int(mem_val)}g"
            else:
                mem_str = f"{mem_val:.1f}g".rstrip('0').rstrip('.')
        else:
            mem_str = f"{int(avg_memory)}m"
        
        # CPU formatting - integer percentage for compactness
        cpu_str = f"{int(round(avg_cpu))}%"
        
        # Single field format: "cpu%/mem"
        result = {"res": f"{cpu_str}/{mem_str}"}
        
        # Only include peaks if significantly different (>20% difference) and very high
        peak_diff_cpu = (self.peak_cpu - avg_cpu) / avg_cpu if avg_cpu > 0 else 0
        peak_diff_mem = (self.peak_memory_mb - avg_memory) / avg_memory if avg_memory > 0 else 0
        
        # Only add peak info if both: significant difference AND high absolute values
        if (peak_diff_cpu > 0.2 and self.peak_cpu > 80) or (peak_diff_mem > 0.2 and self.peak_memory_mb > 1024):
            # Ultra-compact peak format: "p95/2g" (peak cpu 95%, peak mem 2GB)
            peak_cpu_str = f"{int(round(self.peak_cpu))}"
            if self.peak_memory_mb >= 1024:
                peak_mem_val = self.peak_memory_mb / 1024
                if peak_mem_val == int(peak_mem_val):
                    peak_mem_str = f"{int(peak_mem_val)}g"
                else:
                    peak_mem_str = f"{peak_mem_val:.1f}g".rstrip('0').rstrip('.')
            else:
                peak_mem_str = f"{int(self.peak_memory_mb)}m"
            
            result["pk"] = f"{peak_cpu_str}/{peak_mem_str}"
        
        return result
    
    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current resource metrics without stopping sampling - ultra-compact format."""
        if not HAS_PSUTIL or not self.sampling_active:
            return None
            
        try:
            with self.lock:
                if not self.samples:
                    return None
                    
                # Get most recent sample - ultra-compact format matching _calculate_final_metrics
                latest = self.samples[-1]
                current_cpu = latest['cpu_percent']
                current_mem = latest['memory_mb']
                
                # Ultra-compact memory formatting
                if current_mem >= 1024:
                    mem_val = current_mem / 1024
                    if mem_val == int(mem_val):
                        mem_str = f"{int(mem_val)}g"
                    else:
                        mem_str = f"{mem_val:.1f}g".rstrip('0').rstrip('.')
                else:
                    mem_str = f"{int(current_mem)}m"
                
                # CPU formatting - integer percentage
                cpu_str = f"{int(round(current_cpu))}%"
                
                # Single field format: "cpu%/mem"
                result = {"res": f"{cpu_str}/{mem_str}"}
                
                # Only include peaks if significantly different from current AND very high
                peak_diff_cpu = (self.peak_cpu - current_cpu) / current_cpu if current_cpu > 0 else 0
                peak_diff_mem = (self.peak_memory_mb - current_mem) / current_mem if current_mem > 0 else 0
                
                if (peak_diff_cpu > 0.2 and self.peak_cpu > 80) or (peak_diff_mem > 0.2 and self.peak_memory_mb > 1024):
                    # Ultra-compact peak format
                    peak_cpu_str = f"{int(round(self.peak_cpu))}"
                    if self.peak_memory_mb >= 1024:
                        peak_mem_val = self.peak_memory_mb / 1024
                        if peak_mem_val == int(peak_mem_val):
                            peak_mem_str = f"{int(peak_mem_val)}g"
                        else:
                            peak_mem_str = f"{peak_mem_val:.1f}g".rstrip('0').rstrip('.')
                    else:
                        peak_mem_str = f"{int(self.peak_memory_mb)}m"
                    
                    result["pk"] = f"{peak_cpu_str}/{peak_mem_str}"
                
                return result
        except Exception:
            return None
    
    def should_include_in_response(self, build_duration: float = None) -> bool:
        """Determine if resource usage should be included in response."""
        if not HAS_PSUTIL or not self.samples:
            return False
            
        # Exclude for very short builds (< 30 seconds)
        if build_duration and build_duration < 30:
            return False
            
        # Include if meaningful resource usage detected
        with self.lock:
            return (self.peak_cpu > 50.0 or self.peak_memory_mb > 500.0)
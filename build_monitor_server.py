#!/usr/bin/env python3
"""
MCP Build Monitor Server
Universal build monitoring server for CMake/Make projects through MCP protocol.

This server provides build monitoring capabilities through MCP tools:
- build_monitor/start: Start cmake/make builds with full option support
- build_monitor/status: Check status of running builds  
- build_monitor/conflicts: Check for build process conflicts
- build_monitor/terminate: Stop running builds

Features comprehensive AI optimizations and intelligent error analysis.
Compatible with any CMake-based C/C++ project.
"""

import asyncio
import json
import subprocess
import sys
import re
import os
import time
import threading
import multiprocessing
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Import modularized components
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
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# MCP imports
try:
    from mcp.server import Server
    from mcp import stdio_server
    from mcp.types import TextContent, Tool
    from mcp import InitializeResult
except ImportError:
    print("Error: MCP package not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)


class BuildMonitorServer:
    """MCP Server for build monitoring with universal CMake/Make project support"""
    
    def __init__(self, project_root: str = None):
        """Initialize build monitor server.
        
        Args:
            project_root: Root directory of the CMake project. If None, uses current directory.
        """
        self.server = Server("build-monitor")
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.build_dir = self.project_root / "build"
        self.active_builds: Dict[str, BuildSession] = {}
        self.history_manager = BuildHistoryManager()
        self.incremental_tracker = IncrementalBuildTracker()
        self.health_tracker = HealthScoreTracker()
        self.dependency_tracker = DependencyTracker()
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools with their schemas."""
        
        @self.server.call_tool()
        async def build_monitor_start(arguments: dict) -> list[TextContent]:
            """Start a build with cmake/make options. Universal CMake project support."""
            try:
                # Parse arguments with defaults
                targets = arguments.get("targets", [])
                cmake = arguments.get("cmake", False)
                cmake_only = arguments.get("cmake_only", False)
                parallel_jobs = arguments.get("parallel_jobs", "auto")
                background = arguments.get("background", "auto")
                export_logs = arguments.get("export_logs", False)
                show_progress = arguments.get("show_progress", True)
                force = arguments.get("force", False)
                
                # Generate unique build ID
                build_id = str(uuid.uuid4())[:8]
                
                # Get ETA prediction
                predicted_duration = self.history_manager.get_predicted_duration(targets)
                estimated_completion = None
                if predicted_duration:
                    completion_timestamp = time.time() + predicted_duration
                    estimated_completion = datetime.fromtimestamp(completion_timestamp).isoformat() + "Z"
                
                # Detect incremental changes
                change_data = self.incremental_tracker.detect_changes_since_build(targets)
                build_recommendation = self.incremental_tracker.get_build_recommendation(change_data)
                change_impact = self.incremental_tracker.get_change_impact(change_data)
                
                # Detect dependency changes
                dependency_changes = self.dependency_tracker.detect_dependency_changes()
                
                # Create resource monitor for this build
                resource_monitor = ResourceMonitor(sample_interval=2.5)
                
                # Create build session
                session = BuildSession(
                    id=build_id,
                    process=None,
                    status="initializing",
                    start_time=time.time(),
                    targets=targets,
                    cmake_result=None,
                    make_result=None,
                    status_file=None,
                    output_lines=[],
                    predicted_duration=predicted_duration,
                    estimated_completion_time=estimated_completion,
                    change_data=change_data,
                    build_recommendation=build_recommendation,
                    change_impact=change_impact,
                    resource_monitor=resource_monitor,
                    final_resource_usage=None,
                    dependency_changes=dependency_changes
                )
                self.active_builds[build_id] = session
                
                # Check for build conflicts first (unless forced)
                if not force:
                    conflict_result = await self._check_build_conflicts()
                    if conflict_result["status"] == "conflict_detected":
                        session.status = "conflict"
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "build_id": build_id,
                                "status": "build_conflict",
                                "errors": [{"type": "conflict", "message": conflict_result["message"]}],
                                "warnings": [],
                                "error_count": 1,
                                "warning_count": 0,
                                "conflicts": conflict_result["conflicts"],
                                "return_code": 2,
                                "advice": "Wait for other build processes to complete, or use force=true to override."
                            })
                        )]
                
                # Prepare make arguments
                make_args = list(targets)
                
                # Handle parallel jobs
                if parallel_jobs == "auto":
                    try:
                        make_args.insert(0, f'-j{multiprocessing.cpu_count()}')
                    except:
                        make_args.insert(0, '-j4')
                elif isinstance(parallel_jobs, int) and parallel_jobs > 0:
                    make_args.insert(0, f'-j{parallel_jobs}')
                
                # Auto-enable background for long builds
                if background == "auto" and not cmake_only:
                    long_build_targets = ['all', 'install']
                    has_long_target = any(target in targets for target in long_build_targets)
                    has_multiple_packages = len([t for t in targets if 'package_' in t]) > 1
                    background = has_long_target or has_multiple_packages or len(targets) == 0
                
                # Run cmake if requested
                cmake_result = None
                if cmake:
                    if session.resource_monitor:
                        session.resource_monitor.start_sampling()
                    
                    cmake_result = await self._run_cmake(session, show_progress)
                    if cmake_result["status"] == "failed":
                        session.status = "failed"
                        session.cmake_result = cmake_result
                        
                        if session.resource_monitor:
                            session.final_resource_usage = session.resource_monitor.stop_sampling()
                        
                        response_data = {
                            "build_id": build_id,
                            "cmake": cmake_result,
                            "make": {"status": "skipped", "reason": "cmake failed"},
                            "status": "cmake_failed",
                            "errors": [{"type": "cmake_error", "message": cmake_result.get("error", "cmake failed")}],
                            "warnings": [],
                            "error_count": 1,
                            "warning_count": 0,
                            "return_code": cmake_result.get("return_code", 1)
                        }
                        
                        # Include resource usage if meaningful
                        if (session.final_resource_usage and 
                            session.resource_monitor and
                            session.resource_monitor.should_include_in_response(time.time() - session.start_time)):
                            response_data.update(session.final_resource_usage)
                        
                        return [TextContent(type="text", text=json.dumps(response_data))]
                
                # If cmake-only mode, return results without running make
                if cmake_only:
                    session.status = "completed"
                    session.cmake_result = cmake_result
                    
                    if session.resource_monitor:
                        session.final_resource_usage = session.resource_monitor.stop_sampling()
                    
                    cmake_output = {
                        "build_id": build_id,
                        "cmake": cmake_result,
                        "make": {"status": "skipped", "reason": "cmake_only option used"},
                        "status": "cmake_complete",
                        "return_code": cmake_result.get("return_code", 0)
                    }
                    
                    # Include resource usage if meaningful
                    if (session.final_resource_usage and 
                        session.resource_monitor and
                        session.resource_monitor.should_include_in_response(time.time() - session.start_time)):
                        cmake_output.update(session.final_resource_usage)
                    
                    # Include incremental build information when relevant
                    if (session.change_data and 
                        session.change_data.get("changed_files") and 
                        session.change_impact != "none"):
                        cmake_output["changed_files"] = session.change_data.get("changed_files", [])
                        cmake_output["build_recommendation"] = session.build_recommendation
                        cmake_output["change_impact"] = session.change_impact
                    
                    return [TextContent(type="text", text=json.dumps(cmake_output))]
                
                # Run make (background or foreground)
                if session.resource_monitor and not cmake:
                    session.resource_monitor.start_sampling()
                
                if background:
                    make_result = await self._run_make_background(session, make_args, show_progress, export_logs)
                else:
                    make_result = await self._run_make_foreground(session, make_args, show_progress, export_logs)
                
                # Stop resource monitoring and get final metrics
                if session.resource_monitor:
                    session.final_resource_usage = session.resource_monitor.stop_sampling()
                
                # Record build completion for learning systems
                build_duration = time.time() - session.start_time
                success = make_result.get("status") in ["success", "completed"]
                
                if success:
                    self.history_manager.record_build_duration(targets, build_duration)
                    self.incremental_tracker.record_successful_build(targets)
                
                # Record health data
                predicted_duration = session.predicted_duration
                warning_count = make_result.get("warning_count", 0)
                self.health_tracker.record_build_completion(
                    targets, success, build_duration, predicted_duration, 
                    warning_count, session.final_resource_usage
                )
                
                # Prepare final output
                final_output = {
                    "build_id": build_id,
                    "cmake": cmake_result if cmake_result else {"status": "skipped", "reason": "cmake option not used"},
                    "make": make_result,
                    "status": make_result.get("status", "unknown"),
                    "return_code": make_result.get("return_code", 0)
                }
                
                # Include health score if sufficient historical data
                health_score = self.health_tracker.calculate_health_score(targets)
                if health_score is not None:
                    final_output["health_score"] = health_score
                
                # Include ETA information if available
                if session.estimated_completion_time and session.predicted_duration:
                    try:
                        eta_dt = datetime.fromisoformat(session.estimated_completion_time.replace("Z", ""))
                        eta_time = eta_dt.strftime("%H:%M")
                        duration = int(session.predicted_duration)
                        final_output["eta"] = f"{duration}s@{eta_time}"
                    except:
                        eta_time = session.estimated_completion_time[11:16]
                        duration = int(session.predicted_duration)
                        final_output["eta"] = f"{duration}s@{eta_time}"
                
                # Include resource usage if meaningful
                if (session.final_resource_usage and 
                    session.resource_monitor and
                    session.resource_monitor.should_include_in_response(time.time() - session.start_time)):
                    final_output.update(session.final_resource_usage)
                
                # Include incremental build information when relevant
                if (session.change_data and 
                    session.change_data.get("changed_files") and 
                    session.change_impact != "none"):
                    final_output["changed_files"] = session.change_data.get("changed_files", [])
                    final_output["build_recommendation"] = session.build_recommendation
                    final_output["change_impact"] = session.change_impact
                
                # Include dependency changes if any
                if session.dependency_changes:
                    final_output["dependency_changes"] = session.dependency_changes
                
                # Include error/warning summaries
                if "errors" in make_result:
                    final_output["errors"] = make_result["errors"]
                    final_output["error_count"] = make_result.get("error_count", 0)
                if "warnings" in make_result:
                    final_output["warnings"] = make_result["warnings"]
                    final_output["warning_count"] = make_result.get("warning_count", 0)
                
                return [TextContent(type="text", text=json.dumps(final_output))]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "message": f"Build monitor error: {str(e)}",
                        "return_code": 1
                    })
                )]
        
        @self.server.call_tool()
        async def build_monitor_status(arguments: dict) -> list[TextContent]:
            """Get status of running builds."""
            try:
                build_id = arguments.get("build_id")
                
                if build_id:
                    # Get status of specific build
                    if build_id in self.active_builds:
                        session = self.active_builds[build_id]
                        current_time = time.time()
                        status_info = {
                            "build_id": build_id,
                            "status": session.status,
                            "start_time": session.start_time,
                            "targets": session.targets,
                            "duration": current_time - session.start_time
                        }
                        
                        # Add ETA information if available
                        if session.predicted_duration:
                            updated_eta = session.calculate_eta(current_time)
                            if updated_eta:
                                try:
                                    eta_dt = datetime.fromisoformat(updated_eta.replace("Z", ""))
                                    eta_time = eta_dt.strftime("%H:%M")
                                    duration = int(session.predicted_duration)
                                    status_info["eta"] = f"{duration}s@{eta_time}"
                                except:
                                    eta_time = updated_eta[11:16]
                                    duration = int(session.predicted_duration)
                                    status_info["eta"] = f"{duration}s@{eta_time}"
                        
                        # Add resource usage if available
                        if session.resource_monitor:
                            current_metrics = session.resource_monitor.get_current_metrics()
                            if current_metrics:
                                res_str = current_metrics.get('res', '')
                                meaningful_usage = False
                                
                                if '%/' in res_str:
                                    try:
                                        cpu_str, mem_str = res_str.split('%/')
                                        cpu_val = int(cpu_str)
                                        
                                        if mem_str.endswith('g'):
                                            mem_val = float(mem_str.replace('g', '')) * 1024
                                        else:
                                            mem_val = float(mem_str.replace('m', ''))
                                        
                                        meaningful_usage = cpu_val > 30 or mem_val > 300
                                    except (ValueError, IndexError):
                                        meaningful_usage = False
                                
                                if meaningful_usage:
                                    status_info.update(current_metrics)
                        
                        # Add process info if running
                        if session.process and session.process.poll() is None:
                            status_info["pid"] = session.process.pid
                        
                        # Add status file info if background
                        if session.status_file and os.path.exists(session.status_file):
                            try:
                                with open(session.status_file, 'r') as f:
                                    status_info["background_status"] = json.load(f)
                            except:
                                pass
                        
                        return [TextContent(type="text", text=json.dumps(status_info))]
                    else:
                        return [TextContent(
                            type="text", 
                            text=json.dumps({"error": f"Build ID {build_id} not found"})
                        )]
                else:
                    # Get status of all builds
                    all_builds = {}
                    for bid, session in self.active_builds.items():
                        all_builds[bid] = {
                            "status": session.status,
                            "start_time": session.start_time,
                            "targets": session.targets,
                            "duration": time.time() - session.start_time
                        }
                    
                    return [TextContent(
                        type="text",
                        text=json.dumps({"active_builds": all_builds})
                    )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Status check error: {str(e)}"})
                )]
        
        @self.server.call_tool()
        async def build_monitor_conflicts(arguments: dict) -> list[TextContent]:
            """Check for build process conflicts."""
            try:
                result = await self._check_build_conflicts()
                return [TextContent(type="text", text=json.dumps(result))]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Conflict check error: {str(e)}"})
                )]
        
        @self.server.call_tool()
        async def build_monitor_terminate(arguments: dict) -> list[TextContent]:
            """Terminate running builds."""
            try:
                build_id = arguments.get("build_id")
                
                if build_id and build_id in self.active_builds:
                    session = self.active_builds[build_id]
                    if session.process and session.process.poll() is None:
                        session.process.terminate()
                        session.status = "terminated"
                        return [TextContent(
                            type="text",
                            text=json.dumps({"build_id": build_id, "status": "terminated"})
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"build_id": build_id, "status": "not_running"})
                        )]
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": "Build ID required or not found"})
                    )]
                    
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Terminate error: {str(e)}"})
                )]

    async def _check_build_conflicts(self) -> Dict[str, Any]:
        """Check for build process conflicts."""
        if not HAS_PSUTIL:
            return {
                "status": "clear", 
                "conflicts": [],
                "message": "psutil not available - skipping build conflict detection"
            }
        
        # Build-related process names
        build_processes = [
            'make', 'gcc', 'g++', 'clang', 'clang++', 'ld', 'ar', 'ranlib',
            'cmake', 'ninja', 'cc', 'c++', 'collect2', 'as'
        ]
        
        # Script patterns
        script_patterns = [
            'build_monitor_server.py', 'build_monitor_server'
        ]
        
        running_builds = []
        current_pid = os.getpid()
        parent_pid = os.getppid()
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    proc_info = proc.info
                    if not proc_info['name']:
                        continue
                        
                    if proc_info['pid'] in [current_pid, parent_pid]:
                        continue
                        
                    cmdline = proc_info.get('cmdline', [])
                    cmdline_str = ' '.join(cmdline) if cmdline else ''
                    
                    is_build_process = proc_info['name'].lower() in build_processes
                    is_script_instance = any(
                        pattern in cmdline_str for pattern in script_patterns
                    ) or (proc_info['name'] == 'python3' and any(p in cmdline_str for p in script_patterns))
                    
                    if is_build_process or is_script_instance:
                        is_relevant = is_script_instance or any(keyword in cmdline_str.lower() for keyword in 
                                       ['cmake', 'build', 'make'])
                        
                        if is_relevant:
                            conflict_type = "script_instance" if is_script_instance else "build_process"
                            running_builds.append({
                                'pid': proc_info['pid'],
                                'name': proc_info['name'],
                                'cmdline': cmdline_str[:100] + '...' if len(cmdline_str) > 100 else cmdline_str,
                                'duration': f"{int(time.time() - proc_info['create_time'])}s",
                                'type': conflict_type
                            })
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            return {
                "conflict_check_error": f"Failed to check for build conflicts: {str(e)}",
                "conflicts": []
            }
        
        if running_builds:
            script_instances = [p for p in running_builds if p.get('type') == 'script_instance']
            build_processes = [p for p in running_builds if p.get('type') == 'build_process']
            
            message_parts = []
            if script_instances:
                message_parts.append(f"{len(script_instances)} build monitor script(s) already running")
            if build_processes:
                message_parts.append(f"{len(build_processes)} build process(es) already running")
                
            message = "WARNING: " + " and ".join(message_parts) + ". "
            
            if script_instances:
                message += "Multiple script instances could cause build queue conflicts. "
            if build_processes:
                message += "Concurrent builds could interfere with compilation. "
                
            message += "Consider waiting for completion or coordinate with other processes."
            
            return {
                "status": "conflict_detected", 
                "conflicts": running_builds,
                "script_instances": len(script_instances),
                "build_processes": len(build_processes),
                "message": message
            }
        
        return {"status": "clear", "conflicts": []}
    
    async def _run_cmake(self, session: BuildSession, show_progress: bool) -> Dict[str, Any]:
        """Run cmake configuration."""
        if show_progress:
            print("🏗️  Creating Build Environment...", flush=True)
        start_time = time.time()
        
        try:
            original_dir = os.getcwd()
            
            if not self.build_dir.exists():
                return {
                    "status": "failed",
                    "return_code": 1,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "error": f"Build directory {self.build_dir} does not exist",
                    "target": ".."
                }
                
            os.chdir(self.build_dir)
            
            # Run cmake
            process = subprocess.Popen(
                ['cmake', '..', '--log-level=STATUS', '--no-warn-unused-cli'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor cmake progress
            output_lines = []
            progress_count = 0
            current_phase = "Initializing"
            phases_shown = set()
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                    
                if line:
                    line_lower = line.lower()
                    
                    # Collect important lines
                    is_important = any(keyword in line_lower for keyword in [
                        'error', 'warning', 'failed', 'could not', 'not found',
                        'configuring done', 'generating done', 'build files have been written'
                    ])
                    
                    if is_important:
                        output_lines.append(line.strip())
                    
                    # Phase tracking
                    if any(keyword in line_lower for keyword in [
                        'looking for', 'checking', 'performing test', 'found', 'detecting',
                        'check size of', 'check for working'
                    ]):
                        progress_count += 1
                        
                        new_phase = current_phase
                        if progress_count < 100 and ('compiler' in line_lower or 'detecting' in line_lower):
                            new_phase = "Configuring build system"
                        elif progress_count >= 100 and progress_count < 400 and ('checking' in line_lower or 'performing test' in line_lower or 'size of' in line_lower):
                            new_phase = "Checking system capabilities"
                        elif progress_count >= 400 and ('looking for' in line_lower):
                            new_phase = "Finding libraries"
                        
                        should_show = (new_phase != current_phase and new_phase not in phases_shown)
                        
                        if should_show and show_progress:
                            print(f"🏗️  {new_phase}...", flush=True)
                            phases_shown.add(new_phase)
                            current_phase = new_phase
                    
                    # Major milestone messages
                    elif any(milestone in line_lower for milestone in [
                        'build files have been written', 'configuring done', 'generating done'
                    ]) and show_progress:
                        print(f"🏗️  {line.strip().replace('-- ', '')}", flush=True)
            
            os.chdir(original_dir)
            
            # Filter cmake output
            important_lines = []
            for line in output_lines:
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in [
                    'warning:', 'error:', 'failed', 'not found', 'missing',
                    'compiler identification', 'build type:',
                    'installing to', 'found openssl', 'found icu', 'deprecation warning',
                    'cmake deprecation warning', 'final compile flags'
                ]) or line.strip().startswith('-- ') and ('found' in line_lower or 'not found' in line_lower):
                    important_lines.append(line.strip())
            
            if not important_lines and process.returncode == 0:
                important_lines = ["CMake configuration completed successfully"]
            elif not important_lines and process.returncode != 0:
                important_lines = ["CMake configuration failed - check build environment"]
                
            return {
                "status": "success" if process.returncode == 0 else "failed",
                "return_code": process.returncode,
                "duration_ms": int((time.time() - start_time) * 1000),
                "target": "..",
                "output": '\n'.join(important_lines)
            }
            
        except Exception as e:
            if 'original_dir' in locals():
                os.chdir(original_dir)
            return {
                "status": "failed",
                "return_code": 1,
                "duration_ms": int((time.time() - start_time) * 1000),
                "target": "..",
                "error": f"Failed to run cmake: {str(e)}"
            }

    async def _run_make_background(self, session: BuildSession, make_args: List[str], show_progress: bool, export_logs: bool) -> Dict[str, Any]:
        """Run make in background with monitoring."""
        # Display build info
        cores = make_args[0][2:] if make_args and make_args[0].startswith('-j') else str(multiprocessing.cpu_count())
        target = make_args[-1] if make_args and not make_args[-1].startswith('-') else "all"
        if show_progress:
            print(f"🚀 Starting background build: {target} with {cores} cores...", flush=True)
        
        # Change to build directory
        original_dir = os.getcwd()
        os.chdir(self.build_dir)
        
        try:
            process = subprocess.Popen(
                ['make'] + make_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            session.process = process
            session.status = "background"
            
            # Create status file
            status_file = f"/tmp/make-progress-{process.pid}-{int(time.time())}.json"
            session.status_file = status_file
            
            # Background monitor thread
            def monitor_progress():
                output_lines = []
                last_progress = time.time()
                
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                        
                    if line:
                        line_lower = line.lower()
                        is_important = any(keyword in line_lower for keyword in [
                            'error', 'warning', 'failed', 'could not', 'not found',
                            'built target', 'building'
                        ])
                        
                        if is_important:
                            output_lines.append(line.strip())
                        
                        # Extract progress
                        progress_match = re.search(r'\[\s*(\d+)%\]', line)
                        if progress_match:
                            progress = progress_match.group(1)
                            status = {
                                "progress": f"[{progress}%]",
                                "status": "building",
                                "pid": process.pid,
                                "last_update": time.time()
                            }
                            try:
                                with open(status_file, 'w') as f:
                                    json.dump(status, f)
                            except:
                                pass
                                
                        # Send progress updates
                        if time.time() - last_progress >= 15:
                            if show_progress:
                                if progress_match:
                                    print(f"🔨 Building... [{progress_match.group(1)}%]", flush=True)
                                else:
                                    print("🔨 Building...", flush=True)
                            last_progress = time.time()
                
                # Final status
                final_status = {
                    "status": "completed" if process.returncode == 0 else "failed",
                    "return_code": process.returncode,
                    "pid": process.pid,
                    "output": output_lines,
                    "last_update": time.time()
                }
                try:
                    with open(status_file, 'w') as f:
                        json.dump(final_status, f)
                except:
                    pass
                
                session.status = "completed" if process.returncode == 0 else "failed"
                
                # Record completion
                build_duration = time.time() - session.start_time
                success = process.returncode == 0
                
                if success:
                    self.history_manager.record_build_duration(session.targets, build_duration)
                    self.incremental_tracker.record_successful_build(session.targets)
                
                if session.resource_monitor:
                    session.final_resource_usage = session.resource_monitor.stop_sampling()
                
                predicted_duration = session.predicted_duration
                warning_count = len([line for line in output_lines if 'warning' in line.lower()])
                self.health_tracker.record_build_completion(
                    session.targets, success, build_duration, predicted_duration, 
                    warning_count, session.final_resource_usage
                )
            
            # Start monitoring thread
            monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
            monitor_thread.start()
            
            return {
                "status": "background",
                "pid": process.pid,
                "status_file": status_file,
                "bash_command": f"tail -f /proc/{process.pid}/fd/1 2>/dev/null || echo 'Process completed'",
                "monitor_command": f"cat {status_file} 2>/dev/null || echo '{{}}'",
                "message": f"Build started in background (PID: {process.pid}). Use build_monitor/status to check progress."
            }
        
        finally:
            os.chdir(original_dir)

    async def _run_make_foreground(self, session: BuildSession, make_args: List[str], show_progress: bool, export_logs: bool) -> Dict[str, Any]:
        """Run make in foreground with progress updates."""
        try:
            # Display build info
            cores = make_args[0][2:] if make_args and make_args[0].startswith('-j') else str(multiprocessing.cpu_count())
            target = make_args[-1] if make_args and not make_args[-1].startswith('-') else "all"
            if show_progress:
                print(f"🔨 Building {target} with {cores} cores...", flush=True)
            
            # Change to build directory
            original_dir = os.getcwd()
            os.chdir(self.build_dir)
            
            process = subprocess.Popen(
                ['make'] + make_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            session.process = process
            session.status = "running"
            
            output_lines = []
            last_progress_update = time.time()
            current_percentage = None
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                    
                if line:
                    line_lower = line.lower()
                    is_important = any(keyword in line_lower for keyword in [
                        'error', 'warning', 'failed', 'could not', 'not found',
                        'built target', 'building', '[100%]'
                    ])
                    
                    if is_important:
                        output_lines.append(line.rstrip())
                    
                    # Extract percentage
                    percent_match = re.search(r'\[\s*(\d+)%\]', line)
                    if percent_match:
                        current_percentage = int(percent_match.group(1))
                        
                    # Show progress updates
                    if show_progress and (time.time() - last_progress_update >= 10 or percent_match):
                        if current_percentage is not None:
                            print(f"🔨 Building... [{current_percentage}%]", flush=True)
                        else:
                            if 'Building' in line and ('package_' in line or 'target' in line):
                                package_match = re.search(r'(package_\w+|[\w_]+\.dir)', line)
                                if package_match:
                                    package = package_match.group(1).replace('.dir', '').replace('package_', '')
                                    print(f"🔨 Building {package}...", flush=True)
                            elif current_percentage is None:
                                print("🔨 Building...", flush=True)
                        last_progress_update = time.time()
            
            os.chdir(original_dir)
            
            # Wait for completion
            return_code = process.wait()
            session.status = "completed" if return_code == 0 else "failed"
            
            full_output = '\n'.join(output_lines)
            
            # Parse output
            parsed = self._parse_make_output(full_output)
            parsed["return_code"] = return_code
            
            # Handle export functionality
            if export_logs:
                try:
                    import datetime
                    import glob
                    
                    # Clean up old files
                    current_time = datetime.datetime.now()
                    for old_file in glob.glob("/tmp/make_output_*.log"):
                        try:
                            file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(old_file))
                            age_hours = (current_time - file_mtime).total_seconds() / 3600
                            if age_hours > 1:
                                os.remove(old_file)
                        except (OSError, ValueError):
                            continue
                    
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    build_target = "_".join(make_args) if make_args else "default"
                    build_target = "".join(c for c in build_target if c.isalnum() or c in "._-")
                    filename = f"/tmp/make_output_{build_target}_{timestamp}.log"
                    
                    with open(filename, 'w') as f:
                        f.write(f"# Make command: make {' '.join(make_args)}\n")
                        f.write(f"# Timestamp: {datetime.datetime.now().isoformat()}\n")
                        f.write(f"# Return code: {return_code}\n")
                        f.write(f"# Working directory: {os.getcwd()}\n")
                        f.write("# " + "="*70 + "\n\n")
                        f.write(full_output)
                    
                    parsed["exported_to"] = filename
                    
                except Exception as export_error:
                    parsed["export_error"] = f"Failed to export logs: {str(export_error)}"
            
            return parsed
            
        except Exception as e:
            session.status = "failed"
            return {
                "status": "failed",
                "errors": [{"type": "error", "message": f"Failed to run make: {str(e)}"}],
                "warnings": [],
                "error_count": 1,
                "warning_count": 0,
                "return_code": 1
            }
        finally:
            if 'original_dir' in locals():
                os.chdir(original_dir)

    def _parse_make_output(self, output: str) -> Dict[str, Any]:
        """Parse make output with enhanced error categorization."""
        lines = output.split('\n')
        errors = []
        warnings = []
        build_status = "success"
        
        # Enhanced error patterns for C/C++ projects
        error_patterns = [
            r'^(.+?):(\d+):(\d+):\s*error:\s*(.+)$',
            r'^(.+?):(\d+):\s*error:\s*(.+)$',
            r'^(.+?):(\d+):(\d+):\s*fatal error:\s*(.+)$',
            r'^(.+?):(\d+):\s*fatal error:\s*(.+)$',
            r'^(.+?):\s*error:\s*(.+)$',
            r'make\[\d+\]:\s*\*\*\*\s*(.+)$',
            r'collect2:\s*error:\s*(.+)$',
            r'/usr/bin/ld:\s*(.+)$',
            r'CMake Error:\s*(.+)$',
        ]
        
        warning_patterns = [
            r'^(.+?):(\d+):(\d+):\s*warning:\s*(.+)$',
            r'^(.+?):(\d+):\s*warning:\s*(.+)$',
            r'^(.+?):\s*warning:\s*(.+)$',
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for errors
            for pattern in error_patterns:
                match = re.match(pattern, line)
                if match:
                    if len(match.groups()) >= 4:
                        file_path = match.group(1)
                        message = match.group(4)
                        category = self._categorize_error(message, file_path)
                        severity = self._determine_severity("error", category, message)
                        
                        error_dict = {
                            "type": "error",
                            "file": file_path,
                            "line": int(match.group(2)),
                            "column": int(match.group(3)),
                            "message": message,
                            "category": category,
                            "severity": severity
                        }
                        
                        errors.append(error_dict)
                    elif len(match.groups()) >= 3:
                        file_path = match.group(1)
                        message = match.group(3)
                        category = self._categorize_error(message, file_path)
                        severity = self._determine_severity("error", category, message)
                        
                        error_dict = {
                            "type": "error", 
                            "file": file_path,
                            "line": int(match.group(2)),
                            "message": message,
                            "category": category,
                            "severity": severity
                        }
                        
                        errors.append(error_dict)
                    else:
                        message = match.group(1)
                        category = self._categorize_error(message)
                        severity = self._determine_severity("error", category, message)
                        
                        error_dict = {
                            "type": "error",
                            "message": message,
                            "category": category,
                            "severity": severity
                        }
                        
                        errors.append(error_dict)
                    build_status = "failed"
                    break
                    
            # Check for warnings
            for pattern in warning_patterns:
                match = re.match(pattern, line)
                if match:
                    if len(match.groups()) >= 4:
                        file_path = match.group(1)
                        message = match.group(4)
                        category = self._categorize_error(message, file_path)
                        severity = self._determine_severity("warning", category, message)
                        
                        warning_dict = {
                            "type": "warning",
                            "file": file_path,
                            "line": int(match.group(2)),
                            "column": int(match.group(3)),
                            "message": message,
                            "category": category,
                            "severity": severity
                        }
                        
                        warnings.append(warning_dict)
                    elif len(match.groups()) >= 3:
                        file_path = match.group(1)
                        message = match.group(3)
                        category = self._categorize_error(message, file_path)
                        severity = self._determine_severity("warning", category, message)
                        
                        warning_dict = {
                            "type": "warning",
                            "file": file_path,
                            "line": int(match.group(2)),
                            "message": message,
                            "category": category,
                            "severity": severity
                        }
                        
                        warnings.append(warning_dict)
                    break
        
        # Extract build progress
        progress_info = {}
        if build_status == "success":
            for line in lines:
                if '%]' in line and 'Built target' in line:
                    parts = line.split(']')
                    if parts and '%' in parts[0]:
                        try:
                            pct = parts[0].split('%')[0].strip().split()[-1]
                            progress_info["completion"] = f"{pct}%"
                            progress_info["last_target"] = parts[1].strip()
                        except:
                            pass
        
        return {
            "status": build_status,
            "errors": errors,
            "warnings": warnings[:10],  # Limit warnings
            "error_count": len(errors),
            "warning_count": len(warnings),
            "progress": progress_info
        }

    def _categorize_error(self, message: str, file_path: str = "") -> str:
        """Categorize error by type."""
        message_lower = message.lower()
        file_lower = file_path.lower()
        
        # Linker errors
        if any(keyword in message_lower for keyword in [
            "collect2:", "/usr/bin/ld:", "ld:", "cannot find -l",
            "library not found", "shared object", "relocation"
        ]) or "undefined reference" in message_lower:
            return "link"
        
        # Missing headers
        if any(keyword in message_lower for keyword in [
            "no such file or directory", "file not found", "#include",
            "fatal error:", "cannot find", "missing header"
        ]):
            return "header"
        
        # Undefined symbols
        if any(keyword in message_lower for keyword in [
            "undefined symbol", "undeclared identifier",
            "was not declared", "has not been declared", "unknown type name"
        ]):
            return "symbol"
        
        # Syntax errors
        if any(keyword in message_lower for keyword in [
            "syntax error", "expected", "unexpected", "parse error",
            "invalid syntax", "missing semicolon", "missing ')", "missing '}'"
        ]):
            return "syntax"
        
        # CMake errors
        if any(keyword in message_lower for keyword in [
            "cmake", "could not find", "configuration", "package not found",
            "no cmake", "missing dependency"
        ]):
            return "cmake"
        
        # Type errors
        if any(keyword in message_lower for keyword in [
            "type error", "incompatible types", "cannot convert", "invalid conversion",
            "type mismatch", "conflicting types"
        ]):
            return "type"
        
        # Build system errors
        if any(keyword in message_lower for keyword in [
            "make:", "target", "recipe", "no rule", "file is up to date"
        ]):
            return "build"
        
        # Permission errors
        if any(keyword in message_lower for keyword in [
            "permission denied", "cannot open", "access denied", "read-only"
        ]):
            return "access"
        
        # Third-party warnings (often noise)
        if any(lib in file_lower for lib in [
            "libevent", "libwebsockets", "openssl", "icu", "zlib"
        ]) or any(lib in message_lower for lib in [
            "deprecated", "warning directive"
        ]):
            return "lib"
        
        return "other"
    
    def _determine_severity(self, error_type: str, category: str, message: str) -> str:
        """Determine error severity for prioritization."""
        message_lower = message.lower()
        
        # Critical errors that stop builds
        if error_type == "error" and category in ["header", "symbol", "link"]:
            return "C"  # Critical
        
        # CMake errors are critical if they prevent configuration
        if category == "cmake" and any(keyword in message_lower for keyword in [
            "could not find", "missing", "required"
        ]):
            return "C"  # Critical
        
        # Fixable errors
        if category in ["syntax", "type"] or (
            category == "header" and any(keyword in message_lower for keyword in [
                "#include", "file not found"
            ])
        ):
            return "F"  # Fixable
        
        # Third-party issues are usually noise
        if category == "lib":
            return "N"  # Noise
        
        # Warnings are generally warnings unless deprecated
        if error_type == "warning":
            if any(keyword in message_lower for keyword in [
                "deprecated", "will be removed", "obsolete"
            ]):
                return "W"  # Warning
            else:
                return "N"  # Noise
        
        # Build system errors can often be resolved
        if category in ["build", "access"]:
            return "F"  # Fixable
        
        # General errors default to fixable
        if error_type == "error":
            return "F"  # Fixable
        
        return "W"  # Warning

    def get_tool_schemas(self) -> List[Tool]:
        """Define MCP tool schemas."""
        return [
            Tool(
                name="build_monitor/start",
                description="Start a build with cmake/make options for CMake projects",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "targets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Build targets (e.g., ['all'], ['package_name/fast'])",
                            "default": []
                        },
                        "cmake": {
                            "type": "boolean", 
                            "description": "Run cmake before make",
                            "default": False
                        },
                        "cmake_only": {
                            "type": "boolean",
                            "description": "Run cmake only, skip make",
                            "default": False
                        },
                        "parallel_jobs": {
                            "oneOf": [
                                {"type": "integer", "minimum": 1},
                                {"type": "string", "enum": ["auto"]}
                            ],
                            "description": "Number of parallel jobs or 'auto' for CPU count",
                            "default": "auto"
                        },
                        "background": {
                            "oneOf": [
                                {"type": "boolean"},
                                {"type": "string", "enum": ["auto"]}
                            ],
                            "description": "Run in background, or 'auto' for long builds",
                            "default": "auto"
                        },
                        "export_logs": {
                            "type": "boolean",
                            "description": "Export full build logs to /tmp/",
                            "default": False
                        },
                        "show_progress": {
                            "type": "boolean",
                            "description": "Show progress indicators",
                            "default": True
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force run despite build conflicts",
                            "default": False
                        }
                    }
                }
            ),
            Tool(
                name="build_monitor/status",
                description="Get status of running builds",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "build_id": {
                            "type": "string",
                            "description": "Specific build ID to check, or omit for all builds"
                        }
                    }
                }
            ),
            Tool(
                name="build_monitor/conflicts",
                description="Check for build process conflicts",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="build_monitor/terminate",
                description="Terminate a running build",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "build_id": {
                            "type": "string",
                            "description": "Build ID to terminate",
                            "required": True
                        }
                    },
                    "required": ["build_id"]
                }
            )
        ]

async def main():
    """Main entry point for the MCP server.""" 
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MCP Build Monitor Server for CMake projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_monitor_server.py                    # Start MCP server
  python build_monitor_server.py --help
  python build_monitor_server.py --help resource_monitor
  python build_monitor_server.py --list-tools
  python build_monitor_server.py --ai-metadata
        """
    )
    
    # Help and information commands
    parser.add_argument("--help-module", metavar="MODULE", 
                       help="Get help for specific buildmon module")
    parser.add_argument("--list-tools", action="store_true", 
                       help="List all buildmon modules and their status")
    parser.add_argument("--ai-metadata", action="store_true", 
                       help="Get AI assistant integration metadata")
    parser.add_argument("--enable-tool", metavar="MODULE", 
                       help="Enable a buildmon module")
    parser.add_argument("--disable-tool", metavar="MODULE", 
                       help="Disable a buildmon module")
    parser.add_argument("--config-get", metavar="KEY", 
                       help="Get configuration value")
    parser.add_argument("--config-set", nargs=2, metavar=("KEY", "VALUE"), 
                       help="Set configuration value")
    parser.add_argument("--status", action="store_true", 
                       help="Get buildmon system status")
    parser.add_argument("--project-root", metavar="PATH",
                       help="Root directory of CMake project")
    
    args = parser.parse_args()
    
    # Handle CLI commands (delegate to buildmon.py)
    if any([args.help_module, args.list_tools, args.ai_metadata, args.enable_tool, 
            args.disable_tool, args.config_get, args.config_set, args.status]):
        
        try:
            from buildmon import BuildMonManager
            manager = BuildMonManager()
            
            if args.list_tools:
                modules = manager.list_modules()
                print("📦 MCP Build Monitor Modules:")
                print("="*50)
                for name, info in modules.items():
                    status = "✅ Enabled" if info["enabled"] else "❌ Disabled"
                    print(f"{name:20} {status:12} {info.get('description', '')}")
                return
            
            elif args.help_module:
                help_data = manager.get_module_help(args.help_module)
                print(f"📚 Help for {args.help_module}:")
                print("="*50)
                print(json.dumps(help_data, indent=2))
                return
            
            elif args.ai_metadata:
                metadata = manager.get_ai_metadata()
                print(json.dumps(metadata, indent=2))
                return
            
            elif args.enable_tool:
                success, message = manager.enable_module(args.enable_tool)
                print("✅" if success else "❌", message)
                return
            
            elif args.disable_tool:
                success, message = manager.disable_module(args.disable_tool)
                print("✅" if success else "❌", message)
                return
            
            elif args.config_get:
                value = manager.get_config_value(args.config_get)
                print(f"{args.config_get}: {value}")
                return
            
            elif args.config_set:
                key, value = args.config_set
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    parsed_value = value
                
                success, message = manager.set_config_value(key, parsed_value)
                print("✅" if success else "❌", message)
                return
            
            elif args.status:
                status = manager.get_system_status()
                print("🖥️  MCP Build Monitor Status:")
                print("="*50)
                print(json.dumps(status, indent=2))
                return
                
        except ImportError as e:
            print(f"❌ Error: Could not import buildmon manager: {e}")
            print("   Make sure the buildmon module structure is correct")
            return
        except Exception as e:
            print(f"❌ Error: {e}")
            return
    
    # Start the MCP server
    print("🚀 Starting MCP Build Monitor Server...")
    print("   Use --help for CLI options or --list-tools to see available modules")
    if args.project_root:
        print(f"   Project root: {args.project_root}")
    
    server_instance = BuildMonitorServer(project_root=args.project_root)
    
    # Run the server with stdio transport
    async with stdio_server() as streams:
        await server_instance.server.run(
            *streams,
            {
                "server_name": "build-monitor",
                "server_version": "1.0.0"
            }
        )

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
MCP Build Monitor Server
Universal build monitoring server for CMake/Make projects through MCP protocol.

This server provides build monitoring capabilities through MCP tools:
- build_start: Start cmake/make builds with full option support
- build_status: Check status of running builds with line count monitoring
- build_output: Get last n lines of build output for progress examination
- build_conflicts: Check for build process conflicts
- build_terminate: Stop running builds

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
from typing import List, Dict, Any, Optional, Annotated
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import Field

# Set up logging to stderr (required for MCP stdio servers)
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

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
    from mcp.server.fastmcp import FastMCP
    from mcp.types import TextContent
except ImportError:
    logger.error("MCP package not found. Install with: pip install mcp")
    sys.exit(1)

class BuildMonitorServer:
    """MCP Server for build monitoring with universal CMake/Make project support"""

    def __init__(self, project_root: str = None):
        """Initialize build monitor server."""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.build_dir = self.project_root / "build"
        self.sessions_file = self.project_root / ".build_sessions.json"

        # Initialize modular components with proper working-memory paths
        working_memory_dir = Path(__file__).parent / "working-memory"
        working_memory_dir.mkdir(exist_ok=True)

        self.resource_monitor = ResourceMonitor()
        self.build_tracker = IncrementalBuildTracker(
            tracker_file=str(working_memory_dir / "build_tracker.json"),
            project_root=str(self.project_root)
        )
        self.build_history = BuildHistoryManager(
            history_file=str(working_memory_dir / "build_history.json")
        )
        self.dependency_tracker = DependencyTracker(
            tracker_file=str(working_memory_dir / "dependency_tracker.json"),
            project_root=str(self.project_root)
        )
        self.health_tracker = HealthScoreTracker(
            tracker_file=str(working_memory_dir / "health_tracker.json")
        )
        self.fix_suggestions = FixSuggestionsDatabase(
            suggestions_file=str(working_memory_dir / "fix_suggestions.json")
        )

        # Load configuration
        self.config = self._load_config()

        # Load or initialize active builds with persistence
        self.active_builds: Dict[str, BuildSession] = {}
        self._load_sessions()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from settings.json"""
        settings_file = Path(__file__).parent / "settings.json"
        try:
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

        # Default configuration
        return {
            "version": "1.0.0",
            "modules": {
                "resource_monitor": {"enabled": True},
                "build_tracker": {"enabled": True},
                "build_history": {"enabled": True},
                "dependency_tracker": {"enabled": True},
                "health_tracker": {"enabled": True},
                "fix_suggestions": {"enabled": True},
                "build_context": {"enabled": True}
            }
        }

    def _load_sessions(self):
        """Load persisted active build sessions."""
        if not self.sessions_file.exists():
            return

        try:
            with open(self.sessions_file, 'r') as f:
                session_data = json.load(f)

            # Restore sessions, checking if processes are still active
            for session_id, data in session_data.items():
                if self._is_process_still_active(data.get('pid')):
                    # Recreate BuildSession object from persisted data
                    session = BuildSession(
                        id=session_id,
                        process=None,  # Will be reconnected if needed
                        status=data.get('status', 'running'),
                        start_time=data.get('start_time', time.time()),
                        targets=data.get('targets', []),
                        cmake_result=data.get('cmake_result'),
                        make_result=data.get('make_result'),
                        status_file=data.get('status_file'),
                        output_lines=data.get('output_lines', [])
                    )
                    self.active_builds[session_id] = session
                    logger.info(f"Restored active session: {session_id}")
                else:
                    logger.info(f"Session {session_id} process no longer active")

        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")

    def _save_sessions(self):
        """Save active build sessions to disk."""
        try:
            session_data = {}
            for session_id, session in self.active_builds.items():
                session_data[session_id] = {
                    'status': session.status,
                    'start_time': session.start_time,
                    'targets': session.targets,
                    'cmake_result': session.cmake_result,
                    'make_result': session.make_result,
                    'status_file': session.status_file,
                    'output_lines': session.output_lines[-100:] if session.output_lines else [],  # Keep last 100 lines
                    'pid': session.process.pid if session.process else None
                }

            with open(self.sessions_file, 'w') as f:
                json.dump(session_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def _is_process_still_active(self, pid: Optional[int]) -> bool:
        """Check if a process is still running."""
        if not pid:
            return False

        try:
            if HAS_PSUTIL:
                return psutil.pid_exists(pid)
            else:
                # Fallback: check if PID exists using kill signal 0
                os.kill(pid, 0)
                return True
        except (OSError, ProcessLookupError):
            return False

# Initialize FastMCP server
mcp = FastMCP("Build Monitor")

# Global build server instance - will be initialized properly in main

@mcp.tool()
def build_start(
    target: Annotated[str, Field(
        description="Build target name (empty for all targets)",
        examples=["", "lpcc", "driver"]
    )] = "",
    cmake_first: Annotated[bool, Field(
        description="Run cmake configuration before build",
        examples=[False, True]
    )] = False,
    clean: Annotated[bool, Field(
        description="Clean build directory first",
        examples=[False, True]
    )] = False,
    parallel_jobs: Annotated[int, Field(
        description="Number of parallel build jobs (0=auto)",
        ge=0,
        le=32,
        examples=[0, 4, 8]
    )] = 0,
    verbose: Annotated[bool, Field(
        description="Enable verbose build output",
        examples=[False, True]
    )] = False,
    cmake_args: List[str] = None,
    make_args: List[str] = None
) -> str:
    """Start a cmake/make build with comprehensive monitoring and return build session information."""
    try:
        if build_server is None:
            return json.dumps({
                "status": "error",
                "error": "Build server not initialized"
            })

        session_id = str(uuid.uuid4())
        logger.info(f"Creating BuildSession with id: {session_id}")
        session = BuildSession(
            id=session_id,
            process=None,
            status="initializing",
            start_time=time.time(),
            targets=[target] if target else ["default"],
            cmake_result=None,
            make_result=None,
            status_file=None,
            output_lines=[]
        )
        logger.info("BuildSession created successfully")

        build_server.active_builds[session_id] = session
        build_server._save_sessions()  # Persist new session

        # Prepare build directory
        build_dir = build_server.build_dir
        if not build_dir.exists():
            build_dir.mkdir(parents=True)

        # Handle cmake_first option - run cmake asynchronously
        if cmake_first:
            logger.info("Starting asynchronous cmake configuration...")
            session.status = "cmake_running"
            build_server._save_sessions()

            # Start cmake in background thread to avoid blocking MCP request
            def run_cmake_then_make():
                """Background thread to run cmake then start make process."""
                try:
                    # Run cmake as separate non-blocking process
                    cmake_cmd = ["cmake", "-S", str(build_server.project_root), "-B", str(build_dir)] + (cmake_args or [])
                    cmake_process = subprocess.Popen(
                        cmake_cmd,
                        cwd=build_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )

                    # Wait for cmake to complete with reasonable timeout
                    try:
                        cmake_output, _ = cmake_process.communicate(timeout=300)  # 5 minute timeout for cmake

                        # Add cmake output to session output_lines for visibility
                        if cmake_output:
                            cmake_lines = cmake_output.strip().split('\n')
                            session.output_lines.extend([f"[CMAKE] {line}" for line in cmake_lines])

                        if cmake_process.returncode != 0:
                            session.status = "failed"
                            session.cmake_result = {"returncode": cmake_process.returncode, "output": cmake_output, "error": "cmake failed"}
                            session.output_lines.append(f"[CMAKE] FAILED with return code {cmake_process.returncode}")
                            build_server._save_sessions()
                            return

                        # Store cmake result for reporting
                        session.cmake_result = {"returncode": 0, "output": cmake_output}
                        session.output_lines.append("[CMAKE] Configuration completed successfully")
                        logger.info(f"CMake completed successfully for session {session_id}")

                    except subprocess.TimeoutExpired:
                        cmake_process.kill()
                        session.status = "failed"
                        session.cmake_result = {"returncode": -1, "output": "", "error": "cmake timed out after 5 minutes"}
                        session.output_lines.append("[CMAKE] ERROR: Process timed out after 5 minutes")
                        build_server._save_sessions()
                        return

                    # Now start the make process after successful cmake
                    start_make_process(session, build_dir, target, cmake_args, make_args,
                                     parallel_jobs, verbose, clean)

                except Exception as e:
                    logger.error(f"Error in cmake background thread: {e}")
                    session.status = "failed"
                    session.cmake_result = {"returncode": -1, "output": "", "error": f"cmake thread error: {str(e)}"}
                    session.output_lines.append(f"[CMAKE] ERROR: {str(e)}")
                    build_server._save_sessions()

            # Start cmake in background thread
            import threading
            cmake_thread = threading.Thread(target=run_cmake_then_make, daemon=True)
            cmake_thread.start()

            # Return immediately while cmake runs in background
            return json.dumps({
                "session_id": session_id,
                "status": "cmake_running",
                "message": "CMake configuration started in background. Use build_status to monitor progress.",
                "target": target or "default"
            })

        # Continue with regular make process (no cmake_first)
        start_make_process(session, build_dir, target, cmake_args, make_args, parallel_jobs, verbose, clean)

        return json.dumps({
            "session_id": session_id,
            "status": "starting",
            "target": target or "default",
            "message": "Make process started in background. Use build_status to monitor progress.",
            "command": f"make {target or ''}"
        })

    except Exception as e:
        logger.error(f"Build start failed: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e)
        })

def start_make_process(session, build_dir, target, cmake_args, make_args, parallel_jobs, verbose, clean):
    """Start the make process in a separate thread to avoid blocking MCP requests."""
    import subprocess
    import threading
    import time

    def run_make_in_thread():
        """Background thread function to run make without blocking MCP requests."""
        try:
            logger.info(f"Starting make process for session {session.id}")
            session.status = "running"
            build_server._save_sessions()

            # Build the make command
            cmd = ['make']
            if target:
                cmd.append(target)
            if parallel_jobs and parallel_jobs > 1:
                cmd.extend(['-j', str(parallel_jobs)])
            if verbose:
                cmd.append('VERBOSE=1')
            if clean:
                cmd.append('clean')

            # Add any additional make arguments
            if make_args:
                cmd.extend(make_args)

            logger.info(f"Running make command: {' '.join(cmd)} in {build_dir}")

            # Start make process
            process = subprocess.Popen(
                cmd,
                cwd=build_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            session.process = process
            build_server._save_sessions()

            # Monitor the process output with timeout handling
            output_lines = []

            # Use poll() instead of blocking wait() to avoid MCP timeout
            while process.poll() is None:
                try:
                    # Read available output with timeout
                    line = process.stdout.readline()
                    if line:
                        output_lines.append(line.rstrip())
                        session.output_lines.append(f"[MAKE] {line.rstrip()}")
                    else:
                        # Brief sleep to avoid busy waiting
                        time.sleep(0.1)

                    # Save progress periodically to maintain session state
                    if len(output_lines) % 100 == 0:  # Every 100 lines
                        build_server._save_sessions()

                except Exception as read_error:
                    logger.error(f"Error reading make output: {read_error}")
                    break

            # Read any remaining output
            try:
                remaining_output, _ = process.communicate(timeout=5)
                if remaining_output:
                    for line in remaining_output.split('\n'):
                        if line.strip():
                            session.output_lines.append(f"[MAKE] {line.rstrip()}")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout reading remaining make output")

            # Get final return code
            return_code = process.returncode

            if return_code == 0:
                session.status = "completed"
                session.return_code = 0
                logger.info(f"Make completed successfully for session {session.id}")
            else:
                session.status = "failed"
                session.return_code = return_code
                logger.error(f"Make failed with return code {return_code} for session {session.id}")

            build_server._save_sessions()

        except Exception as e:
            logger.error(f"Make process failed for session {session.id}: {e}")
            session.status = "failed"
            session.return_code = -1
            session.output_lines.append(f"[MAKE] ERROR: {str(e)}")
            build_server._save_sessions()

    # Start make in a daemon thread to avoid blocking MCP requests
    make_thread = threading.Thread(target=run_make_in_thread, daemon=True)
    make_thread.start()

    # Return immediately - status can be checked via build_status
    logger.info(f"Make process started in background thread for session {session.id}")

@mcp.tool()
def build_status(
    session_id: Annotated[str, Field(
        description="Build session ID (empty for all active builds)",
        examples=["", "123e4567-e89b-12d3-a456-426614174000"]
    )] = ""
) -> str:
    """Check status of running builds. Provide session_id for specific build or leave empty for all active builds."""
    try:
        if build_server is None:
            return json.dumps({
                "error": "Build server not initialized"
            })

        if session_id:
            # Check specific session
            if session_id not in build_server.active_builds:
                return json.dumps({
                    "error": f"Session {session_id} not found"
                })

            session = build_server.active_builds[session_id]
            status = {
                "session_id": session_id,
                "status": session.status,
                "target": session.targets[0] if session.targets else "default",
                "start_time": session.start_time,
                "duration": time.time() - session.start_time if session.start_time else 0,
                "output_lines": len(session.output_lines),
                "last_output": session.output_lines[-1] if session.output_lines else None
            }

            if session.process:
                poll = session.process.poll()
                # Update session status if process completed but status not yet updated
                if poll is not None and session.status == "running":
                    session.status = "completed" if poll == 0 else "failed"
                    session.return_code = poll
                    build_server._save_sessions()  # Persist status update

                status["running"] = poll is None
                status["return_code"] = poll

            return json.dumps(status)
        else:
            # Check all active builds
            active_sessions = {}
            for sid, session in build_server.active_builds.items():
                active_sessions[sid] = {
                    "status": session.status,
                    "target": session.targets[0] if session.targets else "default",
                    "duration": time.time() - session.start_time if session.start_time else 0,
                    "output_lines": len(session.output_lines),
                    "last_output": session.output_lines[-1] if session.output_lines else None
                }

            return json.dumps({
                "active_builds": len(active_sessions),
                "sessions": active_sessions
            })

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return json.dumps({
            "error": str(e)
        })

@mcp.tool()
def build_terminate(
    session_id: Annotated[str, Field(
        description="Build session ID to terminate",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )]
) -> str:
    """Terminate a running build by session ID. Attempts graceful termination before forcing kill."""
    try:
        if session_id not in build_server.active_builds:
            return json.dumps({
                "error": f"Session {session_id} not found"
            })

        session = build_server.active_builds[session_id]
        if session.process and session.process.poll() is None:
            session.process.terminate()
            time.sleep(1)
            if session.process.poll() is None:
                session.process.kill()
            session.status = "terminated"
            build_server._save_sessions()  # Persist termination status

        return json.dumps({
            "session_id": session_id,
            "status": "terminated"
        })

    except Exception as e:
        logger.error(f"Termination failed: {e}")
        return json.dumps({
            "error": str(e)
        })

@mcp.tool()
def build_conflicts() -> str:
    """Check for conflicting build processes (make/cmake/ninja) that may interfere with new builds."""
    try:
        conflicts = []

        if HAS_PSUTIL:
            # Check for existing make/cmake processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] in ['make', 'cmake', 'ninja']:
                        conflicts.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cmdline": ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ""
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        return json.dumps({
            "conflicts": conflicts,
            "count": len(conflicts)
        })

    except Exception as e:
        logger.error(f"Conflict check failed: {e}")
        return json.dumps({
            "error": str(e)
        })

@mcp.tool()
def get_modules() -> str:
    """Get list of available build monitor modules and their enabled/disabled status."""
    try:
        modules = {}
        config = build_server.config.get("modules", {})

        for module_name in ["resource_monitor", "build_tracker", "build_history",
                          "dependency_tracker", "health_tracker", "fix_suggestions"]:
            modules[module_name] = {
                "enabled": config.get(module_name, {}).get("enabled", True),
                "available": hasattr(build_server, module_name)
            }

        return json.dumps({
            "modules": modules,
            "version": build_server.config.get("version", "1.0.0")
        })

    except Exception as e:
        logger.error(f"Module listing failed: {e}")
        return json.dumps({
            "error": str(e)
        })

@mcp.tool()
def build_output(
    session_id: Annotated[str, Field(
        description="Build session ID",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )],
    lines: Annotated[int, Field(
        description="Number of output lines to retrieve (max 100)",
        ge=1,
        le=100,
        examples=[10, 20, 50]
    )] = 10
) -> str:
    """Get the last n lines of build output from a session for progress monitoring (max 100 lines)."""
    try:
        if session_id not in build_server.active_builds:
            return json.dumps({
                "error": f"Session {session_id} not found"
            })

        session = build_server.active_builds[session_id]

        # Limit lines to reasonable maximum
        lines = min(lines, 100)

        # Get the last n lines
        output_lines = session.output_lines[-lines:] if session.output_lines else []

        return json.dumps({
            "session_id": session_id,
            "status": session.status,
            "total_lines": len(session.output_lines),
            "requested_lines": lines,
            "returned_lines": len(output_lines),
            "output": output_lines,
            "target": session.targets[0] if session.targets else "default",
            "duration": time.time() - session.start_time if session.start_time else 0
        })

    except Exception as e:
        logger.error(f"Output retrieval failed for {session_id}: {e}")
        return json.dumps({
            "error": str(e)
        })

if __name__ == "__main__":
    # Initialize project root from command line
    import argparse
    global build_server

    parser = argparse.ArgumentParser(description="MCP Build Monitor Server")
    parser.add_argument("--project-root", help="Root directory of CMake project")

    args, unknown = parser.parse_known_args()

    # Initialize build_server with proper project root
    if args.project_root:
        build_server = BuildMonitorServer(project_root=args.project_root)
    else:
        build_server = BuildMonitorServer()

    # Run MCP server with stdio transport
    logger.info("Starting MCP Build Monitor Server...")
    mcp.run(transport="stdio")
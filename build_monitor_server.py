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
from typing import List, Dict, Any, Optional
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path

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
        self.active_builds: Dict[str, BuildSession] = {}
        
        # Initialize modular components
        self.resource_monitor = ResourceMonitor()
        self.build_tracker = IncrementalBuildTracker()
        self.build_history = BuildHistoryManager()
        self.dependency_tracker = DependencyTracker()
        self.health_tracker = HealthScoreTracker()
        self.fix_suggestions = FixSuggestionsDatabase()
        
        # Load configuration
        self.config = self._load_config()
        
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

# Initialize FastMCP server
mcp = FastMCP("Build Monitor")
build_server = BuildMonitorServer()

@mcp.tool()
def build_start(target: str = "", cmake_first: bool = False, clean: bool = False, 
                parallel_jobs: int = 0, verbose: bool = False, 
                cmake_args: List[str] = None, make_args: List[str] = None) -> str:
    """
    Start a cmake/make build with comprehensive monitoring.
    
    Args:
        target: Make target to build (e.g. "package_websocket/fast", leave empty for default)
        cmake_first: Run cmake before make
        clean: Clean before building
        parallel_jobs: Number of parallel jobs (0 = auto-detect)
        verbose: Enable verbose output
        cmake_args: Additional cmake arguments
        make_args: Additional make arguments
        
    Returns:
        JSON string with build session info and initial status
    """
    try:
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
        
        # Prepare build directory
        build_dir = build_server.build_dir
        if not build_dir.exists():
            build_dir.mkdir(parents=True)
            
        # Handle cmake_first option
        if cmake_first:
            logger.info("Running cmake configuration...")
            cmake_result = subprocess.run(
                ["cmake", "-S", str(project_root), "-B", str(build_dir)] + (cmake_args or []),
                capture_output=True,
                text=True
            )
            if cmake_result.returncode != 0:
                session.status = "failed"
                return json.dumps({
                    "session_id": session_id,
                    "status": "failed",
                    "error": "cmake failed",
                    "cmake_output": cmake_result.stderr
                })
        
        # Prepare make command
        make_cmd = ["make"]
        if parallel_jobs > 0:
            make_cmd.extend(["-j", str(parallel_jobs)])
        elif parallel_jobs == 0:
            make_cmd.extend(["-j", str(multiprocessing.cpu_count())])
        
        if verbose:
            make_cmd.append("VERBOSE=1")
            
        if clean:
            make_cmd.append("clean")
            
        if target:
            make_cmd.append(target)
            
        if make_args:
            make_cmd.extend(make_args)
        
        # Start build process
        process = subprocess.Popen(
            make_cmd,
            cwd=build_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        session.process = process
        session.status = "running"
        
        # Start monitoring
        if build_server.config["modules"]["resource_monitor"]["enabled"]:
            build_server.resource_monitor.start_sampling()
            
        # Start background completion and output monitoring
        import threading
        def monitor_completion_and_output():
            """Background thread to capture output and detect build completion."""
            try:
                # Read output line by line to track progress
                while True:
                    line = process.stdout.readline()
                    if line:
                        session.output_lines.append(line.strip())
                        # Keep only last 1000 lines to prevent memory issues
                        if len(session.output_lines) > 1000:
                            session.output_lines = session.output_lines[-1000:]
                    
                    # Check if process completed
                    if process.poll() is not None:
                        break
                
                # Read any remaining output
                remaining_output = process.stdout.read()
                if remaining_output:
                    remaining_lines = remaining_output.strip().split('\n')
                    session.output_lines.extend(remaining_lines)
                    if len(session.output_lines) > 1000:
                        session.output_lines = session.output_lines[-1000:]
                
                # Update session status when complete
                session.status = "completed" if process.returncode == 0 else "failed"
                session.return_code = process.returncode
                logger.info(f"Build {session_id} completed with return code {process.returncode}, total output lines: {len(session.output_lines)}")
                
            except Exception as e:
                logger.error(f"Output monitoring failed for {session_id}: {e}")
                session.status = "failed"
        
        completion_thread = threading.Thread(target=monitor_completion_and_output, daemon=True)
        completion_thread.start()
            
        return json.dumps({
            "session_id": session_id,
            "status": "started",
            "target": target,
            "pid": process.pid,
            "command": " ".join(make_cmd)
        })
        
    except Exception as e:
        logger.error(f"Build start failed: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e)
        })

@mcp.tool()
def build_status(session_id: str = "") -> str:
    """
    Check status of running builds.
    
    Args:
        session_id: Specific session ID to check (empty for all active builds)
        
    Returns:
        JSON string with build status information
    """
    try:
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
def build_terminate(session_id: str) -> str:
    """
    Terminate a running build.
    
    Args:
        session_id: Session ID to terminate
        
    Returns:
        JSON string with termination result
    """
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
    """
    Check for build process conflicts.
    
    Returns:
        JSON string with conflict detection results
    """
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
    """
    Get list of available build monitor modules and their status.
    
    Returns:
        JSON string with module information
    """
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
def build_output(session_id: str, lines: int = 10) -> str:
    """
    Get the last n lines of build output from a session.
    
    Args:
        session_id: Session ID to get output from
        lines: Number of lines to retrieve (default: 10, max: 100)
        
    Returns:
        JSON string with output lines and session info
    """
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
    parser = argparse.ArgumentParser(description="MCP Build Monitor Server")
    parser.add_argument("--project-root", help="Root directory of CMake project")
    
    args, unknown = parser.parse_known_args()
    
    if args.project_root:
        build_server = BuildMonitorServer(project_root=args.project_root)
    
    # Run MCP server with stdio transport
    logger.info("Starting MCP Build Monitor Server...")
    mcp.run(transport="stdio")
---
title: Build Monitor API Documentation
description: API documentation for build monitor in DS3.9 automation MCP.
category: automation_tools
subcategory: build_monitor
status: active
created: '2025-08-30'
updated: '2025-08-30'
author: GitHub Copilot
tags:
- build monitor
- API
- automation
- MCP
date: '2025-08-30'
ds3.9_frontmatter_version: '1.0'
---

# MCP Build Monitor API Reference

Complete API documentation for AI assistant integration with the universal MCP Build Monitor system for CMake/Make projects.

## 🔌 MCP Tools

### `build_monitor/start`
Execute builds with comprehensive intelligent monitoring for any CMake-based project.

**Description**: Primary build execution tool with enhanced AI features and universal C/C++ project support.

#### Parameters
```json
{
  "targets": ["string"],           // Build targets (e.g., ["package_websocket/fast"])
  "cmake": false,                  // Run cmake before make
  "cmake_only": false,             // Run cmake only, skip make
  "parallel_jobs": "auto",         // Number of parallel jobs or "auto"
  "background": "auto",            // Run in background, or "auto" for long builds
  "export_logs": false,            // Export full build logs to /tmp/
  "show_progress": true,           // Show progress indicators
  "force": false                   // Force run despite build conflicts
}
```

#### Response Format
```json
{
  "build_id": "abc123de",          // Unique build identifier
  "status": "success",             // Overall build status
  "return_code": 0,                // Process return code
  
  // Core build results
  "cmake": {
    "status": "success",
    "return_code": 0,
    "duration_ms": 1234,
    "output": "cmake output..."
  },
  "make": {
    "status": "success",
    "errors": [...],               // Enhanced error objects
    "warnings": [...],             // Enhanced warning objects
    "error_count": 0,
    "warning_count": 0
  },
  
  // Enhanced features (conditional inclusion)
  "health_score": 85,              // Feature 6: 0-100 build quality score
  "eta": "45s@14:28",              // Feature 2: Duration + completion time
  "res": "85%/1.5g",               // Feature 5: CPU%/Memory
  "pk": "95/2g",                   // Feature 5: Peak usage (conditional)
  "changed_files": ["file1.c"],   // Feature 4: Modified files
  "build_recommendation": "incremental_rebuild",  // Feature 4
  "change_impact": "medium",       // Feature 4: Impact assessment
  "dependency_changes": [          // Feature 7: Dependency modifications
    {
      "file": "CMakeLists.txt",
      "type": "build_config", 
      "impact": "full_rebuild",
      "recommendation": "Run cmake .. && make clean && make"
    }
  ]
}
```

#### Enhanced Error Objects (Feature 1 + 8)
```json
{
  "type": "error",
  "file": "src/websocket.cc",
  "line": 45,
  "column": 12,
  "message": "fatal error: openssl/ssl.h: No such file or directory",
  "category": "header",            // Feature 1: Error categorization
  "severity": "C",                 // Feature 1: C=Critical, F=Fixable, W=Warning, N=Noise
  "pattern": "missing_openssl_headers",    // Feature 8: Pattern identifier
  "suggested_fix": "Install OpenSSL development packages",  // Feature 8
  "fix_commands": [                // Feature 8: Step-by-step commands
    "sudo apt update",
    "sudo apt install -y libssl-dev openssl",
    "pkg-config --modversion openssl"
  ],
  "fix_type": "quick",             // Feature 8: quick/medium/complex
  "confidence": 95                 // Feature 8: Confidence score (0-100)
}
```

#### Usage Patterns
```javascript
// Quick package build
{
  "targets": ["specific_target"],
  "background": false
}

// Full system build with dependency updates
{
  "cmake": true,
  "targets": [],
  "background": "auto"
}

// Development iteration cycle
{
  "targets": ["package_crypto"],
  "show_progress": true,
  "background": false
}

// Force build despite conflicts
{
  "targets": ["all"],
  "force": true,
  "background": true
}
```

---

### `build_monitor/status`
Get status of running or completed builds.

#### Parameters
```json
{
  "build_id": "abc123de"          // Optional: specific build ID
}
```

#### Response Format
```json
{
  "build_id": "abc123de",
  "status": "running",            // running, completed, failed, background
  "start_time": 1692847234.56,
  "duration": 45.2,
  "targets": ["specific_target"],
  "pid": 12345,                   // If process is running
  
  // Real-time enhanced data
  "eta": "30s@14:30",             // Updated ETA based on progress
  "res": "75%/1.2g",              // Current resource usage
  "background_status": {          // For background builds
    "progress": "[45%]",
    "last_update": 1692847245.12
  }
}
```

---

### `build_monitor/conflicts`  
Check for build process conflicts.

#### Parameters
```json
{}
```

#### Response Format
```json
{
  "status": "conflict_detected",  // clear, conflict_detected
  "conflicts": [
    {
      "pid": 12345,
      "name": "make",
      "cmdline": "make specific_target",
      "duration": "45s",
      "type": "build_process"      // build_process, script_instance
    }
  ],
  "script_instances": 1,          // Count of other build monitors
  "build_processes": 1,           // Count of active builds
  "message": "WARNING: 1 build process already running..."
}
```

---

### `build_monitor/terminate`
Terminate running builds.

#### Parameters
```json
{
  "build_id": "abc123de"          // Required: build ID to terminate
}
```

#### Response Format
```json
{
  "build_id": "abc123de",
  "status": "terminated"          // terminated, not_running
}
```

---

## 🤖 AI Assistant Integration

### Metadata API
Get comprehensive system information for AI decision-making:

```bash
python buildmon.py --ai-metadata
```

#### Response Structure
```json
{
  "system_info": {
    "name": "MCP Build Monitor",
    "version": "1.0.0",
    "enabled_modules": ["resource_monitor", "build_tracker", ...],
    "total_modules": 7,
    "configuration_file": "/path/to/settings.json"
  },
  "modules": {
    "resource_monitor": {
      "name": "Resource Monitor",
      "description": "Ultra-compact CPU and memory monitoring...",
      "features": [...],
      "configuration": {...},
      "output_format": {...},
      "token_cost": "4-8 tokens per build response",
      "ai_metadata": {
        "purpose": "Monitor resource usage during builds...",
        "when_to_use": "Automatically enabled for builds >30 seconds",
        "interpretation": {...},
        "recommendations": {...}
      },
      "examples": [...],
      "troubleshooting": {...}
    }
    // ... all enabled modules
  },
  "workflows": [
    {
      "name": "Quick Package Build",
      "description": "Build specific CMake package quickly",
      "mcp_tool": "build_monitor/start",
      "parameters": {...},
      "relevant_modules": [...],
      "interpretation_tips": [...]
    }
    // ... common workflows
  ],
  "troubleshooting": {
    "common_issues": [...],
    "module_specific": {...}
  },
  "token_efficiency": {
    "estimated_token_range": "15-45 tokens per build response",
    "efficiency_features": [...],
    "module_estimates": {...}
  }
}
```

### Module-Specific Help
Get detailed help for individual modules:

```bash
python buildmon.py --help-module resource_monitor
```

Returns complete module metadata including configuration options, examples, and AI integration guidance.

---

## 📊 Feature Integration Guide

### Feature 1: Smart Error Categorization
**When to use**: Always enabled for error analysis
**Response fields**: `category`, `severity` in error objects
**AI interpretation**: 
- `C` (Critical): Blocks compilation, requires immediate attention
- `F` (Fixable): Can be resolved with specific actions  
- `W` (Warning): Important but not blocking
- `N` (Noise): Third-party warnings, usually ignorable

### Feature 2: Build Time Prediction & ETA
**When to use**: When historical data available (≥3 previous builds)
**Response fields**: `eta` (format: "45s@14:28")  
**AI interpretation**: Duration estimate + expected completion time
**Accuracy**: Improves over time with more build history

### Feature 5: Resource Usage Monitoring  
**When to use**: Builds longer than 30 seconds with meaningful resource usage
**Response fields**: `res` (CPU%/Memory), `pk` (peaks, conditional)
**AI interpretation**:
- `res: "85%/1.5g"` = 85% CPU, 1.5GB memory
- `pk: "95/2g"` = Peaks of 95% CPU, 2GB memory (significant spikes)
**Thresholds**: Only included when CPU >50% OR Memory >500MB

### Feature 6: Build Health Scoring
**When to use**: When sufficient historical data (≥5 builds)
**Response fields**: `health_score` (0-100 integer)
**AI interpretation**:
- 90-100: Excellent build quality, high success rate, good performance
- 70-89: Good quality with some issues to monitor  
- 50-69: Moderate quality, investigate recurring problems
- <50: Poor quality, requires attention to patterns and fixes

### Feature 7: Dependency Change Detection
**When to use**: When dependency files modified since last build
**Response fields**: `dependency_changes` array
**AI interpretation**: Each entry includes file, type, impact, and recommendation
**Common impacts**: `full_rebuild`, `package_specific`, `dependency_update`

### Feature 8: Fix Suggestions Database
**When to use**: When errors match known patterns (automatic)
**Response fields**: Enhanced error objects with `pattern`, `suggested_fix`, `fix_commands`, `fix_type`, `confidence`
**AI interpretation**:
- `confidence: 90+`: Highly reliable, execute immediately
- `confidence: 70-89`: Good match, verify applicability
- `fix_type: "quick"`: 1-2 commands, usually safe
- `fix_type: "medium"`: 3-5 commands, review before execution
- `fix_type: "complex"`: 6+ commands, requires careful consideration

---

## 🎯 Common Workflows

### Quick Package Development
```json
{
  "tool": "build_monitor/start",
  "parameters": {
    "targets": ["specific_package"],
    "background": false
  },
  "expected_features": ["error_categorization", "fix_suggestions", "resource_monitor"],
  "typical_duration": "30-60 seconds",
  "ai_focus": "Error analysis and fix suggestions"
}
```

### Full System Build
```json
{
  "tool": "build_monitor/start", 
  "parameters": {
    "cmake": true,
    "targets": [],
    "background": "auto"
  },
  "expected_features": ["health_score", "resource_monitor", "dependency_tracker", "eta"],
  "typical_duration": "3-8 minutes",
  "ai_focus": "Overall system health and performance trends"
}
```

### Dependency Update Build
```json
{
  "tool": "build_monitor/start",
  "parameters": {
    "cmake": true,
    "targets": [],
    "force": false
  },
  "expected_features": ["dependency_changes", "build_recommendation", "change_impact"],
  "ai_focus": "Understanding impact of changes and rebuild requirements"
}
```

---

## ⚙️ Configuration Management

### Runtime Configuration
```bash
# List current settings
python buildmon.py --config-get modules.resource_monitor

# Modify settings  
python buildmon.py --config-set modules.resource_monitor.sample_interval 3.0

# Reset to defaults
python buildmon.py --config-set modules.fix_suggestions.enabled true
```

### Module Management
```bash
# Enable/disable features
python buildmon.py --enable-tool health_tracker
python buildmon.py --disable-tool dependency_tracker

# Check module status
python buildmon.py --list-tools
```

---

## 🚨 Error Handling

### Build Conflicts
```json
{
  "status": "build_conflict",
  "conflicts": [...],
  "advice": "Wait for other build processes to complete, or use force=true to override"
}
```

### Module Failures
```json
{
  "status": "partial_failure",
  "failed_modules": ["dependency_tracker"],
  "main_result": {...},
  "warnings": ["Dependency tracking unavailable"]
}
```

### Invalid Parameters
```json
{
  "status": "error",
  "message": "Invalid target specification",
  "return_code": 1
}
```

---

## 🔧 Universal CMake Project Support

### Supported Project Types
- **Standard CMake Projects**: Any project using CMakeLists.txt
- **Multi-Package Projects**: Projects with package-based builds
- **Cross-Platform**: Linux, macOS, Windows (with appropriate tools)
- **Build Systems**: CMake + Make, CMake + Ninja, CMake + Visual Studio

### Project Structure Requirements
```
your-project/
├── CMakeLists.txt           # Main CMake configuration
├── src/                     # Source files (.c, .cpp, .h, .hpp)
├── build/                   # Build directory (auto-created)
├── package_*/               # Optional: package-based organization
└── dependencies/            # Optional: external dependencies
```

### Environment Setup
```bash
# Required tools
cmake --version    # CMake 3.10+
make --version     # GNU Make or equivalent
gcc --version      # GCC, Clang, or MSVC

# Optional but recommended
python3 --version  # Python 3.6+ for build monitor
psutil             # pip install psutil (for resource monitoring)
```

---

## 📈 Performance Characteristics

### Token Efficiency
- **Conditional inclusion**: Features only add tokens when providing actionable value
- **Ultra-compact formats**: Maximum information density
- **Smart thresholds**: Avoid noise with meaningful data detection
- **Estimated total**: 15-45 tokens per build response

### System Impact
- **CPU overhead**: <1% during builds
- **Memory usage**: <10MB persistent data
- **Storage**: <5MB with automatic cleanup
- **Network**: None (local operation)

### Scalability
- **Build history**: Rolling windows prevent unbounded growth
- **Concurrent builds**: Conflict detection and management
- **Module architecture**: Easy to enable/disable features for performance tuning

---

## 🏗️ Integration Examples

### Basic Integration
```python
# Initialize build monitor server
from build_monitor_server import BuildMonitorServer
server = BuildMonitorServer(project_root="/path/to/your/cmake/project")

# Start a build
result = await server.build_monitor_start({
    "targets": ["your_target"],
    "cmake": True,
    "show_progress": True
})
```

---

## 🔌 Current MCP Tools (Updated 2025-08-26)

### `build_start`
Start a cmake/make build with comprehensive monitoring.

**Parameters:**
- `target` (str): Build target (e.g., "package_grpc/fast")
- `cmake_first` (bool): Run cmake before make (default: false)
- `clean` (bool): Run clean before build (default: false)  
- `parallel_jobs` (int): Parallel jobs (0 = auto-detect, default: 0)
- `verbose` (bool): Enable verbose output (default: false)
- `cmake_args` (List[str]): Additional cmake arguments
- `make_args` (List[str]): Additional make arguments

**Returns:**
```json
{
  "session_id": "uuid-string",
  "status": "started",
  "target": "package_grpc/fast",
  "pid": 12345,
  "command": "make -j 4 package_grpc/fast"
}
```

### `build_status`
Check status of running builds with line count monitoring.

**Parameters:**
- `session_id` (str): Specific session ID (empty for all active builds)

**Returns:**
```json
{
  "session_id": "uuid-string",
  "status": "running|completed|failed|terminated",
  "target": "package_grpc/fast", 
  "start_time": 1756191747.34,
  "duration": 120.5,
  "output_lines": 45,
  "last_output": "Building CXX object src/packages/grpc/grpc.o",
  "running": true,
  "return_code": null
}
```

**New Fields (Added 2025-08-26):**
- `output_lines`: Total number of captured output lines
- `last_output`: Most recent output line (null if no output yet)

### `build_output` 
Get the last n lines of build output for progress examination.

**Parameters:**
- `session_id` (str): Build session to examine
- `lines` (int): Number of lines to retrieve (default: 10, max: 100)

**Returns:**
```json
{
  "session_id": "uuid-string",
  "status": "running",
  "total_lines": 1247,
  "requested_lines": 20,
  "returned_lines": 20,
  "output": [
    "Building CXX object CMakeFiles/package_grpc.dir/src/packages/grpc/grpc.cc.o",
    "Building CXX object CMakeFiles/package_grpc.dir/src/packages/grpc/grpc_server.cc.o",
    "..."
  ],
  "target": "package_grpc/fast",
  "duration": 180.2
}
```

### `build_terminate`
Terminate a running build.

**Parameters:**
- `session_id` (str): Session ID to terminate

**Returns:**
```json
{
  "session_id": "uuid-string", 
  "status": "terminated"
}
```

### `build_conflicts`
Check for existing build process conflicts.

**Returns:**
```json
{
  "conflicts": [
    {
      "pid": 12345,
      "name": "make", 
      "cmdline": "make -j 4 package_grpc/fast",
      "duration": "120s",
      "type": "build_process"
    }
  ],
  "conflict_count": 1,
  "recommendation": "wait_or_coordinate"
}
```

### `get_modules`
Get list of available build monitor modules and their status.

**Returns:**
```json
{
  "modules": {
    "resource_monitor": {"enabled": true, "available": true},
    "build_tracker": {"enabled": true, "available": true},
    "health_tracker": {"enabled": false, "available": true}
  }
}
```

## 🔄 AI Assistant Usage Patterns

### Progress Monitoring
```python
# Monitor build progress via line count changes
status = mcp__build-monitor__build_status(session_id="...")
if status['output_lines'] > previous_count:
    print(f"Build active: {status['last_output']}")
```

### Output Examination  
```python
# Examine recent output for troubleshooting
output = mcp__build-monitor__build_output(session_id="...", lines=20)
for line in output['output']:
    if 'error' in line.lower():
        print(f"Error found: {line}")
```

### Smart Build Management
```python
# Check for conflicts before starting
conflicts = mcp__build-monitor__build_conflicts()
if conflicts['conflict_count'] == 0:
    # Start build
    result = mcp__build-monitor__build_start(target="package_grpc/fast")
```

### Advanced Configuration
```python
# Custom project configuration
server = BuildMonitorServer(
    project_root="/path/to/project"
)

# Full system build with all features
result = await server.build_monitor_start({
    "cmake": True,
    "targets": [],
    "background": True,
    "export_logs": True,
    "parallel_jobs": 8
})
```

### Error Handling Pattern
```python
try:
    result = await server.build_monitor_start(params)
    
    if result["status"] == "success":
        # Build completed successfully
        if "health_score" in result:
            print(f"Build health: {result['health_score']}/100")
        
        if "errors" in result and result["errors"]:
            # Handle build errors with fix suggestions
            for error in result["errors"]:
                if "suggested_fix" in error:
                    print(f"Fix suggestion: {error['suggested_fix']}")
                    if error["confidence"] > 90:
                        # High confidence fix, safe to apply
                        pass
    
    elif result["status"] == "build_conflict":
        # Handle build conflicts
        print("Build conflict detected, waiting...")
        
except Exception as e:
    print(f"Build monitor error: {e}")
```

---

*This API is optimized for AI assistant integration with the MCP protocol, providing maximum functionality with minimal token overhead for any CMake-based C/C++ project.*
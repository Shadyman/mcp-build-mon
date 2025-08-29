# MCP Build Monitor - TODO List

## High Priority Features

### ⚡ URGENT: Deliver Research Brief to Claude Opus 4.1
**Status**: Ready for Delivery  
**Priority**: URGENT - High Impact Research  
**Description**: Comprehensive research brief prepared for Claude Opus 4.1 analysis of Python package integration opportunities

**Deliverable Ready**: `/automation/mcp/build-monitor/RESEARCH_BRIEF.md`
- **33+ pages** of comprehensive technical analysis and context
- **Live FluffOS build evidence** with real multi-core compilation data
- **Strategic integration questions** for optimal package selection
- **Implementation roadmap requirements** with risk/reward analysis
- **Quantitative benchmarks** and success validation framework

**Research Focus**: 
1. **Strategic Package Selection**: Which 3-5 packages provide maximum enhancement with minimal integration risk?
2. **Implementation Roadmap**: Phased integration approach with dependency management  
3. **Architecture Preservation**: Maintain MCP compatibility and AI optimization while gaining advanced features
4. **Performance Impact**: Expected resource overhead and optimization opportunities
5. **Validation Strategy**: Test and benchmark each integration against current baseline

**Expected Research Outcomes**:
- **Package integration matrix** with complexity/benefit analysis
- **Architecture migration plan** with phased implementation approach
- **Proof-of-concept implementations** for top 3 recommended packages
- **Risk assessment** with mitigation strategies for each integration

**High-Value Research Targets**:
- **`compiledb`/`bear`**: Enhanced compilation process tracking
- **`networkx`**: Dependency graph analysis and critical path detection  
- **`scikit-build`**: Advanced CMake integration capabilities
- **`ccache`/`sccache`**: Performance insights and caching metrics
- **`watchdog`**: Intelligent file change detection for incremental builds

**Business Impact**:
- **Solve parallel job blindness**: Accurate ETAs for different `-j` counts
- **Enable package-level learning**: Individual package compilation time tracking
- **Multi-threaded progress displays**: Rich UI capabilities for build dashboards
- **Build optimization insights**: Data-driven recommendations for faster builds

**Token Investment**: High-value research that could save weeks of development time by leveraging existing, optimized packages vs custom implementation.

**Action Required**: Schedule dedicated research session with Claude Opus 4.1 when tokens and time are available.

---

### Parallel Job Count Awareness in Build Learning
**Status**: Not implemented  
**Priority**: High  
**Description**: Build monitor currently ignores parallel job count (`-j` flag) when learning build patterns and predicting ETAs

**Current Problem**:
- Build history uses only target names as keys, ignoring parallel job count
- `-j1` and `-j4` builds are stored under same history key
- ETA predictions mix data from different parallel job counts
- Resource usage patterns don't correlate with job parallelism
- Health scoring doesn't account for parallelism impact

**Expected Impact**:
- **Wildly inaccurate ETAs**: A `-j1` build (20 minutes) vs `-j4` build (5 minutes) would average to 12.5 minutes
- **Poor resource predictions**: Memory/CPU usage varies dramatically with job count
- **Misleading health scores**: Parallel job failures treated same as single-threaded failures

**Requested Implementation**:
1. **Enhanced Target Keys**: Include parallel job count in build history keys
   - `"package_sockets_j1"` vs `"package_sockets_j4"` 
   - `"full_build_j8"` vs `"full_build_j2"`

2. **Resource Correlation**: Track resource usage patterns per job count
   - Memory scaling with parallel jobs (2GB @ j1 vs 8GB @ j4)  
   - CPU utilization efficiency per job count
   - Optimal job count recommendations per project

3. **Smart ETA Prediction**: Factor parallelism into time estimates
   - Learn scaling patterns (linear, sublinear, or diminishing returns)
   - Predict optimal job count for current system resources
   - Account for memory constraints limiting effective parallelism

4. **Health Score Adjustments**: 
   - Different failure patterns for parallel vs sequential builds
   - Timeout thresholds adjusted for job count
   - Build success rates correlated with parallelism level

**Example Enhanced Response**:
```json
{
  "build_history_key": "package_sockets_j4",
  "eta": "2m 15s@14:30",
  "parallel_efficiency": 85,
  "optimal_job_count": 4,
  "resource_prediction": {
    "peak_memory": "6.2GB", 
    "avg_cpu": "78%",
    "based_on_j4_history": true
  },
  "recommendations": [
    "Current -j4 is optimal for this system and target",
    "Memory usage scales linearly up to -j6 on this system"
  ]
}
```

**Benefits**:
- **Accurate ETAs**: Separate predictions for different parallel job counts
- **Resource optimization**: Learn optimal job counts per project/system
- **Performance insights**: Understand parallelism efficiency and bottlenecks  
- **System-aware recommendations**: Suggest job counts based on available resources

**Estimated Effort**: High (3-4 weeks implementation + testing)

### Package-Level Compilation Time Learning
**Status**: Not implemented  
**Priority**: High  
**Description**: Learn and predict compilation times for individual packages to enable granular progress tracking and multi-threaded build displays

**Current Limitation**:
- Build monitor only tracks overall build duration
- No visibility into individual package compilation times
- Multi-threaded builds show generic "building..." status
- Cannot predict completion order or bottleneck packages

**Requested Implementation**:

1. **Package Detection**: Parse CMake makefiles to identify all buildable packages
   ```json
   {
     "detected_packages": [
       "package_core", "package_sockets", "package_http", 
       "package_websocket", "package_zmqtt", "package_external"
     ]
   }
   ```

2. **Real-Time Package Tracking**: Monitor active package builds during compilation
   ```json
   {
     "active_packages": {
       "package_core": {"status": "linking", "progress": "libpackage_core.a", "elapsed": "45s"},
       "package_sockets": {"status": "compiling", "progress": "socket_efuns.cc.o", "elapsed": "38s"},
       "package_http": {"status": "queued", "progress": "waiting", "elapsed": "0s"}
     }
   }
   ```

3. **Package-Specific Learning**: Build history per package with parallel job awareness
   ```json
   {
     "package_history": {
       "package_sockets_j4": {
         "avg_duration": "2m 15s",
         "confidence": 0.85,
         "sample_count": 12,
         "typical_files": ["socket_efuns.cc", "socket_option_manager.cc"],
         "bottleneck_files": ["socket_option_validator.cc"]
       }
     }
   }
   ```

4. **Multi-Threaded Progress Display**: Enable rich UI progress tracking
   ```json
   {
     "build_progress": {
       "overall_eta": "4m 30s@14:45",
       "packages": [
         {
           "name": "package_core",
           "status": "completed", 
           "duration": "1m 22s",
           "health": "good"
         },
         {
           "name": "package_sockets",
           "status": "compiling",
           "eta": "1m 45s", 
           "current_file": "socket_option_validator.cc",
           "progress_pct": 65
         },
         {
           "name": "package_http", 
           "status": "queued",
           "eta": "2m 10s",
           "depends_on": ["package_sockets"]
         }
       ]
     }
   }
   ```

5. **Dependency-Aware Scheduling**: Understand package build order and dependencies
   - Track which packages can build in parallel
   - Identify critical path packages that block others
   - Predict overall completion based on dependency chains

**Use Cases**:
- **Multi-threaded UI**: Show individual package progress bars with ETAs
- **Build optimization**: Identify consistently slow packages for optimization
- **Resource planning**: Predict memory/CPU usage patterns per package
- **Bottleneck identification**: Find packages that consistently take longer than expected
- **Parallel efficiency**: Understand which packages benefit most from parallelization

**Implementation Approach**:
1. **Process Tree Parsing**: Monitor make process hierarchy to identify package builds
2. **Makefile Analysis**: Parse CMake-generated makefiles for package dependencies
3. **File Pattern Recognition**: Track compilation of specific source files per package
4. **Duration Learning**: Maintain rolling history of package compilation times
5. **Progress Estimation**: Calculate package completion percentage based on file counts

**API Enhancement Example**:
```json
{
  "tool": "build_monitor/get_package_status",
  "response": {
    "session_id": "abc123",
    "packages": {
      "package_sockets": {
        "status": "compiling",
        "files_completed": 12,
        "files_total": 18,
        "progress_pct": 67,
        "current_files": ["socket_option_validator.cc", "socket_efuns.cc"],
        "eta_remaining": "1m 23s",
        "avg_duration": "2m 15s"
      }
    }
  }
}
```

**Benefits**:
- **Granular Progress Tracking**: Real-time visibility into multi-package builds
- **UI/Dashboard Integration**: Rich progress displays for developers
- **Build Optimization**: Data-driven package optimization decisions  
- **Predictive Planning**: Accurate ETAs for complex multi-package builds
- **Resource Management**: Package-specific resource usage patterns

**Current Evidence from FluffOS Build**:
Our current build shows packages building in parallel:
- `package_core` (building dumpstat.cc.o)
- `package_sockets` (compiling socket_option_validator.cc) 
- `package_math` (linking libpackage_math.a)
- `package_matrix` (building matrix.cc.o)

**Estimated Effort**: High (4-5 weeks implementation + comprehensive testing)

### Research Python Compilation Management Packages
**Status**: Research Required  
**Priority**: Medium  
**Description**: Investigate existing Python packages for compilation management that could be leveraged to enhance the build monitor

**Research Areas**:

1. **Build System Integration Libraries**:
   - `cmake` - Python bindings for CMake
   - `scikit-build` - Better integration between setuptools and CMake
   - `ninja` - Python wrapper for Ninja build system
   - `conan` - C/C++ package manager with build integration
   - `vcpkg` - Microsoft's C++ package manager with Python tools

2. **Compilation Database Tools**:
   - `compiledb` - Generate JSON compilation database for bear/clang tooling
   - `bear` - Tool for generating compilation database by intercepting build commands
   - `scan-build` - Static analysis tool that understands compilation processes
   - `compile_commands` - Tools for working with compile_commands.json

3. **Build Monitoring and Analysis**:
   - `buildbot` - Continuous integration framework with build monitoring
   - `ccache` - Compiler cache with statistics and monitoring
   - `distcc` - Distributed compilation with monitoring capabilities
   - `sccache` - Shared compilation cache with metrics
   - `incredibuild` - Build acceleration with detailed analytics

4. **Process and Performance Monitoring**:
   - `psutil` - Already in use, but explore advanced features
   - `py-spy` - Sampling profiler that could track compilation processes
   - `memory_profiler` - Memory usage tracking during builds
   - `time` / `timeit` - Enhanced timing and benchmarking utilities

5. **Dependency Graph Analysis**:
   - `networkx` - Graph analysis for build dependency chains
   - `graphviz` - Visualization of build dependencies and critical paths
   - `pydot` - Python interface to Graphviz for dependency visualization

6. **Makefile and Build File Parsing**:
   - `pyparsing` - For parsing complex makefile syntax
   - `ply` - Python Lex-Yacc for parsing build configuration files
   - `parsimonious` - PEG parser for structured build file analysis

7. **Real-time Monitoring and Events**:
   - `watchdog` - File system monitoring for source file changes
   - `asyncio` - Enhanced async capabilities for real-time monitoring
   - `websockets` - Real-time build status streaming to UIs
   - `fastapi` - Modern API framework for build monitoring endpoints

**Integration Opportunities**:
- **Replace custom parsing**: Use established libraries for makefile/cmake parsing
- **Enhanced dependency tracking**: Leverage graph analysis libraries
- **Better process monitoring**: Use advanced psutil features or specialized tools
- **Compilation database**: Integrate compile_commands.json generation and analysis
- **Build acceleration**: Explore ccache/sccache integration for performance insights
- **Real-time streaming**: WebSocket integration for live build dashboards

**Research Questions**:
1. Can `compiledb` or `bear` provide better compilation process tracking?
2. Does `scikit-build` offer CMake integration advantages?
3. Can `networkx` improve dependency graph analysis and critical path detection?
4. Would `ccache` integration provide valuable caching and performance metrics?
5. Can `watchdog` enable smarter file change detection for incremental builds?
6. Does `buildbot` have reusable components for build monitoring?

**Expected Outcomes**:
- **Reduced development time**: Leverage existing, well-tested libraries
- **Enhanced capabilities**: Access to features beyond custom implementation
- **Better integration**: Standard interfaces with other build tools
- **Community support**: Established packages with ongoing maintenance
- **Performance improvements**: Optimized libraries vs custom implementations

**Deliverable**:
Comprehensive research document with:
- Library comparison matrix (features, performance, integration complexity)
- Proof-of-concept integrations for top candidates
- Migration recommendations for current custom implementations
- Performance benchmarks comparing custom vs library-based approaches

**Estimated Effort**: Medium (2-3 weeks research + prototyping)

### CMake Configuration Management
**Status**: Not implemented  
**Priority**: High  
**Description**: Add CMakeLists.txt option() management functionality to the build monitor

**Requested Features**:
- **Read CMake options**: Parse CMakeLists.txt to extract `option()` definitions and current values
- **Set CMake options**: Modify option values before running `cmake ..`
- **CMake cache management**: Read/write CMake cache variables
- **Option validation**: Validate option values against defined constraints

**Implementation Approach**:
1. **New MCP Tools**:
   - `cmake_get_options` - Extract all option() definitions from CMakeLists.txt
   - `cmake_set_option` - Set specific option value before cmake execution
   - `cmake_get_cache` - Read current cmake cache values
   - `cmake_set_cache` - Modify cmake cache variables

2. **Integration with Existing Tools**:
   - Extend `build_monitor/start` with `cmake_options` parameter
   - Add pre-cmake option configuration step
   - Integrate with dependency tracking for option changes

3. **Response Format Example**:
   ```json
   {
     "cmake_options": {
       "PACKAGE_WEBSOCKET": {"value": "ON", "type": "BOOL", "description": "websocket package"},
       "PACKAGE_ZMQTT": {"value": "OFF", "type": "BOOL", "description": "zmqtt package"}
     },
     "cmake_cache": {
       "CMAKE_BUILD_TYPE": "Debug",
       "CMAKE_INSTALL_PREFIX": "/usr/local"
     }
   }
   ```

**Benefits**:
- Automated CMake configuration management
- Integration with build monitoring workflow
- Eliminates manual CMakeLists.txt editing
- Supports dynamic build configuration based on project needs

**Estimated Effort**: Medium (2-3 weeks implementation)

---

## Medium Priority Features

### Enhanced Dependency Tracking
- Track CMakeLists.txt changes and recommend full rebuilds
- Detect package interdependencies for targeted builds

### Build Configuration Profiles
- Save/restore common build configurations
- Profile-based option sets (debug, release, testing)

### Advanced Error Pattern Recognition
- Machine learning for error pattern detection
- Community-sourced fix suggestions database

### Multi-Core Build Process Tracking
**Status**: Feature Request  
**Priority**: Medium  
**Description**: Add MCP tools to expose real-time multi-core build process information

**Current Evidence of Multi-Core Activity** (2025-08-25):
During active FluffOS build with `make -j 4`, the following parallel processes were observed:

1. **Main make process**: PID 899531 (`make -j 4`) - the build monitor's main process
2. **CMake coordination**: PID 899536 (`make -s -f CMakeFiles/Makefile2 all`) 
3. **Parallel package builds**:
   - **package_core**: PID 900749 - building `dumpstat.cc.o`
   - **package_sockets**: PID 900879 - compiling `socket_option_validator.cc` 
   - **package_math**: PID 901232 - linking `libpackage_math.a`
   - **package_matrix**: PID 901311 - building `matrix.cc.o`
4. **Active GCC compilation**: PID 901197 - the actual C++ compiler (`cc1plus`) working on socket_option_validator.cc with full optimization flags (`-O3`, `-flto=auto`, `-march=native`)

**Requested MCP Tools**:
- `build_monitor/get_active_processes` - Return real-time process tree for current build
- `build_monitor/get_parallel_status` - Show which packages/files are building in parallel
- `build_monitor/get_compilation_details` - Expose compiler flags, optimization levels, target files

**Response Format Example**:
```json
{
  "build_session_id": "abc123",
  "parallel_jobs": 4,
  "active_processes": [
    {
      "pid": 899531,
      "command": "make -j 4",
      "role": "build_coordinator",
      "duration": "5m 23s"
    },
    {
      "pid": 900879,
      "command": "make -s -f src/packages/sockets/CMakeFiles/package_sockets.dir/build.make",
      "role": "package_builder",
      "package": "sockets",
      "current_file": "socket_option_validator.cc"
    }
  ],
  "compiler_activity": [
    {
      "pid": 901197,
      "compiler": "cc1plus",
      "source_file": "socket_option_validator.cc",
      "optimization": "-O3",
      "target_arch": "skylake",
      "progress": "compilation"
    }
  ],
  "package_status": {
    "package_core": {"status": "building", "current_file": "dumpstat.cc.o"},
    "package_sockets": {"status": "building", "current_file": "socket_option_validator.cc.o"},
    "package_math": {"status": "linking", "current_target": "libpackage_math.a"},
    "package_matrix": {"status": "building", "current_file": "matrix.cc.o"}
  }
}
```

**Benefits**:
- **Real-time visibility**: See exactly what's building across all cores
- **Performance insights**: Identify bottlenecks in parallel compilation
- **Progress tracking**: More granular build progress than duration alone
- **Debug assistance**: Understand build failures in multi-process context
- **Resource optimization**: Optimize parallel job counts based on actual utilization

**Implementation Considerations**:
- Parse `ps -ef` output to build process tree
- Track CMake makefile targets and dependencies
- Monitor compiler process command lines for file/optimization details
- Handle process lifecycle (spawn/complete) during build progression
- Filter noise (focus on build-related processes only)

**Use Cases**:
- AI assistants understanding build complexity and progress
- Developers debugging slow or failed parallel builds
- Build system optimization and performance tuning
- Educational insight into modern multi-core compilation processes

**Estimated Effort**: Medium (2-3 weeks implementation)

---

## Low Priority Features

### Build Artifact Management
- Track generated files and build outputs
- Cleanup utilities for build directories

### Integration Testing Support
- Test execution integration with build monitoring
- Test result correlation with build health

---

## Bug Reports and Anomalies

### 🚨 URGENT: .build_sessions.json Naming Inconsistency
**Date Reported**: 2025-08-28  
**Status**: Investigation Required  
**Priority**: URGENT - Git Repository Issue  
**Reporter**: User

**Issue Description**:
The build monitor creates a hidden file `.build_sessions.json` (with dot prefix) but this file is not gitignored and appears in git status, causing confusion about whether it should be committed or ignored.

**Problem**:
- File is named with dot prefix (`.build_sessions.json`) suggesting it's a hidden config/cache file
- File is NOT in `.gitignore` so it appears in `git status` 
- Unclear if this should be tracked in version control or ignored as local state
- Naming inconsistency suggests this was an oversight in implementation

**Expected Resolution Options**:
1. **Rename to `build_sessions.json`** (remove dot) if it should be version controlled
2. **Add to `.gitignore`** if it's meant to be local-only session state
3. **Move to proper cache directory** like `~/.cache/build-monitor/` or `/tmp/`

**Current Impact**:
- Developers unsure whether to commit or ignore the file
- Git repository cleanliness affected
- Inconsistent with standard conventions (dotfiles are usually hidden configs)

**Investigation Needed**:
1. Check if build monitor actually needs persistent session state across runs
2. Determine if session data should be project-specific or system-wide
3. Review if other MCP servers follow similar patterns
4. Assess impact of changing filename on existing deployments

**Recommended Priority**: URGENT - This affects git workflow and repository cleanliness

---

### Build Process Execution Anomaly
**Date Reported**: 2025-08-25  
**Status**: Investigation Required  
**Priority**: High  
**Reporter**: Claude Code Assistant

**Issue Description**:
Anomalous behavior observed when using `build_monitor/start` with combined parameters:
- `cmake_first: true`
- `clean: true` 
- `target: ""` (default)

**Expected Behavior**:
Build monitor should execute the following sequence:
1. `make clean` (clean existing build artifacts)
2. `cmake ..` (regenerate build configuration)  
3. `make -j 4` (execute full build)

**Actual Behavior**:
Build monitor only executed:
1. `make -j 4 clean` (clean step only)
2. Process completed with `return_code: 0` and `running: false`
3. No cmake configuration or make build steps were executed

**Build Monitor Response**:
```json
{
  "session_id": "73658a8a-4cee-4968-a48f-b9b317625a9b",
  "status": "started", 
  "command": "make -j 4 clean",
  "return_code": 0,
  "running": false,
  "duration": ~39-78 seconds
}
```

**Verification**:
- No FluffOS driver binary was generated
- Only test libraries found: `/build/src/CMakeFiles/_CMakeLTOTest-*/bin/libfoo.a`
- Build directory contained cmake cache but no compiled artifacts
- Subsequent `build_monitor/start` with `cmake_first: false` successfully executed full build

**Potential Root Causes**:
1. **Parameter Conflict**: `cmake_first: true` + `clean: true` combination may not be handled correctly
2. **Process Management**: Build monitor may terminate after clean step instead of continuing
3. **Command Sequencing**: Multi-step build process may not be properly orchestrated
4. **Status Reporting**: Build monitor may report completion prematurely

**Impact**:
- **High**: Users may believe builds completed successfully when only cleaning occurred
- **Verification Gap**: Return code success doesn't guarantee full build completion
- **Workflow Disruption**: Forces manual verification of build artifacts

**Workaround**:
Execute build process in separate steps:
1. `build_monitor/start` with `clean: true` only
2. `build_monitor/start` with `cmake_first: true` only  
3. `build_monitor/start` with `target: ""` for actual build

**Recommended Investigation**:
1. **Code Review**: Examine build process orchestration logic
2. **Parameter Validation**: Test all parameter combinations systematically
3. **Process Monitoring**: Add intermediate status reporting for multi-step builds
4. **Artifact Verification**: Consider adding build output validation to status responses

**Additional Context**:
- Project: FluffOS socket development build
- Build Environment: CMake + Make (4 parallel jobs)
- Build Duration Expected: 5-10 minutes for full build
- Build Duration Observed: ~39 seconds (clean only)

---

## Completed Features
- ✅ Build execution and monitoring
- ✅ Error categorization and fix suggestions
- ✅ Resource usage tracking
- ✅ Build health scoring
- ✅ Dependency change detection
- ✅ Comprehensive API documentation
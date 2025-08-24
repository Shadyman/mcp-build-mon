# MCP Build Monitor

A comprehensive, AI-optimized build monitoring system for CMake/Make projects with intelligent error analysis, resource monitoring, and automated fix suggestions.

## ✨ Overview

The MCP Build Monitor transforms basic build execution into an intelligent, AI-assistant-friendly system that provides:
- **Smart Error Analysis** with categorization and fix suggestions
- **Resource Usage Monitoring** with ultra-compact token formats  
- **Build Time Prediction** using historical data
- **Health Scoring** based on success rates and performance trends
- **Dependency Change Detection** with impact analysis
- **Incremental Build Intelligence** for efficient rebuilds

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/Shadyman/mcp-build-mon.git
cd mcp-build-mon

# Install dependencies
pip install mcp psutil

# Test the system
python buildmon.py --list-tools
```

### Basic Usage
```bash
# Start the MCP server for AI assistant integration
python build_monitor_server.py

# Check system status
python buildmon.py --status

# Get help for specific module
python buildmon.py --help-module resource_monitor

# View AI integration metadata
python buildmon.py --ai-metadata
```

## 🎯 Key Features

### 🔍 Smart Error Analysis (Feature 1)
- Categorizes errors by type (header, linker, syntax, cmake, etc.)
- Assigns severity levels (Critical, Fixable, Noise)
- Token-efficient error prioritization for AI assistants

### ⏱️ Build Time Prediction (Feature 2)  
- Maintains rolling history of build durations per target
- Provides ETA estimates in ultra-compact format: `"eta": "45s@14:28"`
- Learns from actual vs predicted performance

### 🎯 Failure Pattern Recognition (Feature 3)
- Identifies 29+ common CMake and compilation error patterns
- Provides targeted fix suggestions with confidence scores
- Context-aware solutions for different environments

### 📊 Incremental Build Intelligence (Feature 4)
- Tracks file modifications to recommend optimal rebuild strategies
- Categorizes changes (source, headers, config) for impact analysis
- Smart recommendations: `no_build_needed`, `cmake_recommended`, `package_specific`

### 💾 Resource Usage Monitoring (Feature 5)
- Ultra-compact format: `"res": "85%/1.5g"` (CPU%/Memory)
- Peak tracking: `"pk": "95/2g"` (only for significant spikes)
- **Token efficient**: 4-8 tokens per build response

### 🏥 Build Health Scoring (Feature 6)
- Composite 0-100 score: success_rate(40%) + speed(25%) + warnings(20%) + resources(15%)
- Historical tracking with rolling windows
- Trend analysis for build quality assessment

### 🔗 Dependency Change Detection (Feature 7)
- Monitors CMakeLists.txt, config files, external dependencies
- Smart impact analysis with actionable recommendations
- Detects when cmake regeneration or clean rebuilds are needed

### 🛠️ Fix Suggestions Database (Feature 8)
- **29 comprehensive fix patterns** across 7 categories
- **Environment-aware commands** (Debian, RedHat, Arch)
- **Multi-level fixes**: Quick (1-2 commands), Medium (3-5), Complex (6+)
- **Confidence scoring** (0-100) for reliability assessment

## 📊 AI Assistant Integration

### Single Source of Truth
The buildmon system provides a unified interface for AI assistants:

```python
from buildmon import BuildMonManager
manager = BuildMonManager()

# Get complete system metadata
metadata = manager.get_ai_metadata()
# Returns: system_info, modules, workflows, troubleshooting, token_efficiency

# Get module-specific help
help_data = manager.get_module_help("resource_monitor")
# Returns: features, configuration, examples, ai_metadata, troubleshooting
```

### MCP Tools Integration
```bash
# Primary build tool - intelligent build execution
build_monitor/start: Execute builds with intelligent monitoring
build_monitor/status: Check running build status with ETA updates  
build_monitor/conflicts: Detect conflicting build processes
build_monitor/terminate: Stop running builds gracefully
```

### Token Efficiency
- **Conditional inclusion**: Features only add tokens when providing value
- **Ultra-compact formats**: `"res": "85%/1.5g"` vs traditional `{"cpu_percent": 85.2, "memory_mb": 1536}`
- **Smart thresholds**: Avoid noise with meaningful usage detection
- **Estimated overhead**: 15-45 tokens per build response (vs 100+ for verbose alternatives)

## 🛠️ Configuration

### Module Management
```bash
# List all modules and status
python buildmon.py --list-tools

# Enable/disable modules
python buildmon.py --enable-tool health_tracker
python buildmon.py --disable-tool dependency_tracker

# Configure module settings  
python buildmon.py --config-set resource_monitor.sample_interval 3.0
python buildmon.py --config-get health_tracker.weights
```

### Settings File
Configuration is stored in `settings.json`:
```json
{
  "version": "1.0.0",
  "modules": {
    "resource_monitor": {
      "enabled": true,
      "sample_interval": 2.5,
      "min_cpu_threshold": 50.0
    }
  }
}
```

## 📚 Module Architecture

### Self-Documenting Modules
Each module contains comprehensive `help_data`:
- **Features and capabilities**
- **Configuration options with types and ranges**
- **Output formats and field descriptions**
- **AI integration metadata and usage patterns**
- **Examples and troubleshooting guides**

### Core Modules
- **`resource_monitor.py`**: CPU/memory monitoring with ultra-compact formats
- **`build_tracker.py`**: Incremental build intelligence and file change tracking  
- **`build_history.py`**: ETA prediction using historical build data
- **`dependency_tracker.py`**: Smart dependency change detection and impact analysis
- **`health_tracker.py`**: Multi-factor build quality scoring system
- **`fix_suggestions.py`**: Comprehensive database of context-aware fix solutions
- **`build_context.py`**: Build session context preservation and analysis
- **`build_session.py`**: Build session data structures and management

### Data Organization
Configuration and runtime data are cleanly separated:

**Configuration** (`settings.json`):
- Module enable/disable states
- Thresholds, weights, and preferences
- Global system settings

**Runtime Data** (`working-memory/` directory):
- `build_history.json` - Historical build durations and ETA data
- `build_tracker.json` - File modification tracking for incremental builds
- `dependency_tracker.json` - Dependency change snapshots and analysis
- `health_tracker.json` - Build health metrics and scoring history
- `fix_suggestions.json` - Adaptive fix pattern database and usage statistics
- `build_context.json` - Session context and build pattern analysis

This separation ensures configuration portability while maintaining persistent runtime intelligence across sessions.

## 🎯 Use Cases

### CMake/Make Development
- **Package builds**: `package_name/fast`, `target_name`
- **Full system builds**: cmake regeneration + complete compilation
- **Library compilation**: Multi-target project builds

### AI Assistant Workflows
1. **Quick package build** → Focus on error categorization and fix suggestions
2. **Full system build** → Emphasize health scoring and resource monitoring  
3. **Dependency updates** → Highlight dependency changes and rebuild recommendations
4. **Performance analysis** → Leverage resource usage and build time trends

### Error Resolution
- **Pattern recognition**: Automatic identification of 29+ common issues
- **Environment-specific fixes**: Commands tailored to detected OS/package manager
- **Multi-step solutions**: Detailed command sequences with confidence scores
- **Preventive recommendations**: Suggestions based on build context and history

## 🔧 Development

### Adding New Modules
1. **Copy template**: `cp modules/TEMPLATE.py modules/new_feature.py`
2. **Implement class**: Follow the template pattern with `help_data` metadata
3. **Update imports**: Add to `modules/__init__.py`
4. **Configure**: Add module settings to `settings.json`
5. **Add tests**: Create `tests/test_new_feature.py`
6. **Test**: Run `python buildmon.py --list-tools`

### Integration Pattern
```python
# In BuildMonitorServer class
self.new_feature = NewFeature()

# In build processing
feature_result = self.new_feature.process_build_data({
    "targets": session.targets,
    "start_time": session.start_time,
    "errors": parsed_errors
})

if feature_result:
    final_output.update(feature_result)
```

## 📈 Performance

### Token Efficiency Metrics
- **Resource Monitor**: 4-8 tokens (vs 25+ for verbose JSON)
- **Build Health**: 4-5 tokens (single integer score)
- **Fix Suggestions**: 15-25 tokens (only when applicable)
- **ETA Prediction**: 8-10 tokens (ultra-compact time format)
- **Overall System**: 15-45 tokens per build response

### Build Performance Impact
- **CPU overhead**: <1% (background sampling with smart intervals)
- **Memory usage**: <10MB (efficient data structures and rolling windows)
- **Storage footprint**: <5MB (persistent data with automatic cleanup)
- **Network traffic**: None (local operation only)

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone https://github.com/Shadyman/mcp-build-mon.git
cd mcp-build-mon

# Install dependencies
pip install mcp psutil pytest

# Run tests
python -m pytest tests/ -v

# Check configuration
python buildmon.py --status
```

### Code Standards
- **Self-documenting**: All modules must include comprehensive `help_data`
- **Token efficient**: Conditional inclusion and compact formats
- **Error handling**: Graceful degradation when components fail
- **Backward compatible**: New features must not break existing functionality

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

### Common Issues
- **Import errors**: Ensure MCP dependencies are installed
- **Module not found**: Check `modules/__init__.py` imports
- **Configuration issues**: Validate `settings.json` syntax
- **Permission errors**: Verify write access to working directory

### Getting Help  
- **Module help**: `python buildmon.py --help-module <module_name>`
- **System status**: `python buildmon.py --status`
- **AI metadata**: `python buildmon.py --ai-metadata`
- **Configuration**: `python buildmon.py --config-get <key>`

### Troubleshooting
See individual module help data for specific troubleshooting guides:
```bash
python buildmon.py --help-module resource_monitor
# Returns comprehensive troubleshooting information
```

---

**Built for AI assistants, by AI assistants** 🤖  
*Optimized for Claude Code and MCP protocol integration*
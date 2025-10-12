# Directory Configuration Guide

This guide provides comprehensive information about configuring directory paths in the JSON QA webapp.

## Overview

The JSON QA webapp supports configurable directory paths through a `config.yaml` file. This allows you to:

- Customize directory locations for different environments
- Use absolute or relative paths as needed
- Maintain backward compatibility with existing deployments
- Implement organizational directory structures

## Quick Start

1. **Copy the example configuration:**
   ```bash
   cp example-config.yaml config.yaml
   ```

2. **Edit the directory paths:**
   ```yaml
   directories:
     json_docs: "your_input_directory"
     corrected: "your_output_directory"
     # ... customize other paths as needed
   ```

3. **Start the application:**
   ```bash
   python -m streamlit run streamlit_app.py
   ```

The application will validate your configuration and create missing directories automatically.

## Configuration File Structure

### Complete Configuration Example

```yaml
# Application settings
app:
  name: "JSON QA Webapp"
  version: "1.1.0"
  debug: false

# Schema configuration
schema:
  primary_schema: "invoice_schema.yaml"
  fallback_schema: "default_schema.yaml"

# Directory configuration (main focus)
directories:
  json_docs: "json_docs"    # Input JSON files
  corrected: "corrected"        # Processed JSON files
  audits: "audits"             # Audit logs
  pdf_docs: "pdf_docs"         # PDF documents
  locks: "locks"               # File locks

# UI customization
ui:
  page_title: "JSON Quality Assurance"
  sidebar_title: "Navigation"

# Processing settings
processing:
  lock_timeout: 60             # Minutes
  max_file_size: 10            # MB
```

### Directory Configuration Options

| Directory | Purpose | Default | Required |
|-----------|---------|---------|----------|
| `json_docs` | Input JSON files awaiting validation | `json_docs` | Yes |
| `corrected` | Validated and corrected JSON files | `corrected` | Yes |
| `audits` | Audit logs and processing history | `audits` | Yes |
| `pdf_docs` | Original PDF documents | `pdf_docs` | Yes |
| `locks` | File locking for concurrency control | `locks` | Yes |

## Path Types

### Relative Paths
Relative to the application root directory:
```yaml
directories:
  json_docs: "./input"           # Same directory
  corrected: "../output"           # Parent directory
  audits: "logs/processing"        # Subdirectory
```

### Absolute Paths
Full system paths:
```yaml
directories:
  json_docs: "/app/data/input"
  corrected: "/app/data/output"
  audits: "/var/log/qa/audits"
```

### Mixed Paths
Combine relative and absolute as needed:
```yaml
directories:
  json_docs: "./input"           # Relative
  corrected: "/shared/output"      # Absolute
  audits: "./logs"                 # Relative
```

## Environment-Specific Configurations

### Development Environment
```yaml
app:
  name: "JSON QA - Development"
  debug: true

directories:
  json_docs: "./dev_input"
  corrected: "./dev_output"
  audits: "./dev_logs"
  pdf_docs: "./dev_docs"
  locks: "./dev_locks"

processing:
  lock_timeout: 120  # Longer for debugging
```

### Production Environment
```yaml
app:
  name: "JSON QA - Production"
  debug: false

directories:
  json_docs: "/app/data/input"
  corrected: "/app/data/output"
  audits: "/app/logs/audits"
  pdf_docs: "/app/data/documents"
  locks: "/tmp/qa_locks"

processing:
  lock_timeout: 30   # Shorter for efficiency
  max_file_size: 50  # Larger for production
```

### Docker Container
```yaml
directories:
  json_docs: "/data/input"      # Volume mount
  corrected: "/data/output"       # Volume mount
  audits: "/logs/audits"          # Volume mount
  pdf_docs: "/data/documents"     # Volume mount
  locks: "/tmp/locks"             # Container temp
```

## Configuration Templates

The `config-templates/` directory contains ready-to-use configurations:

- `production-config.yaml` - Production deployment
- `development-config.yaml` - Development environment
- `docker-config.yaml` - Container deployment
- `testing-config.yaml` - Automated testing
- `minimal-config.yaml` - Minimal customization

### Using Templates

1. **Copy a template:**
   ```bash
   cp config-templates/production-config.yaml config.yaml
   ```

2. **Customize paths:**
   Edit the copied file to match your environment

3. **Test configuration:**
   Start the application and check startup messages

## Validation and Error Handling

### Startup Validation
The application validates configuration at startup:

- **Path Format**: Checks if paths are valid
- **Directory Existence**: Creates missing directories
- **Permissions**: Verifies read/write access
- **Fallback**: Uses defaults if validation fails

### Error Recovery
If configuration fails, the application:

1. **Logs the error** with detailed information
2. **Shows user-friendly messages** with recovery suggestions
3. **Falls back to defaults** to ensure functionality
4. **Continues operation** with working directories

### Common Validation Messages

**Success:**
```
✅ Custom Directory Configuration Active
📁 Using custom paths from config.yaml
```

**Warnings:**
```
⚠️ Configuration Issues Detected
Some configuration settings are invalid, using defaults where necessary.
```

**Errors:**
```
❌ Directory Configuration Error
Failed to create directory: Permission denied
```

## Migration Guide

### From Hardcoded Paths

1. **Identify current directories** used by your deployment
2. **Create config.yaml** with current paths:
   ```yaml
   directories:
     json_docs: "json_docs"    # Your current input dir
     corrected: "corrected"        # Your current output dir
     # ... etc
   ```
3. **Test the configuration** by starting the application
4. **Gradually customize** paths as needed

### Backward Compatibility
- Existing deployments work without changes
- No config.yaml file uses hardcoded defaults
- Partial configuration fills missing values with defaults
- Invalid configuration falls back to defaults

## Best Practices

### Directory Organization
```yaml
# Organized by function
directories:
  json_docs: "data/input/json"
  corrected: "data/output/json"
  audits: "logs/processing"
  pdf_docs: "data/input/pdf"
  locks: "temp/locks"
```

### Security Considerations
- Use dedicated directories with appropriate permissions
- Avoid world-writable directories
- Consider using separate user accounts for production
- Regularly backup audit logs and processed files

### Performance Optimization
- Use fast storage for frequently accessed directories
- Consider separate volumes for different directory types
- Monitor disk space usage
- Implement log rotation for audit directories

### Monitoring and Maintenance
- Check startup messages for configuration issues
- Monitor directory permissions and accessibility
- Backup configuration files with your deployment
- Document custom configurations for your team

## Troubleshooting

### Configuration Not Loading
1. Check `config.yaml` syntax with a YAML validator
2. Verify file is in the application root directory
3. Check file permissions (must be readable)
4. Review startup logs for specific errors

### Directory Creation Failures
1. Verify parent directories exist
2. Check file system permissions
3. Ensure sufficient disk space
4. Try creating directories manually

### Permission Issues
1. Check directory ownership and permissions
2. Verify application user has write access
3. Consider using absolute paths
4. Test with a simple directory structure first

### Path Resolution Problems
1. Use absolute paths to avoid ambiguity
2. Check for typos in directory names
3. Verify paths exist and are accessible
4. Test configuration with minimal setup

## Advanced Configuration

### Environment Variables
Override configuration with environment variables:
```bash
export QA_INPUT_DIR="/custom/input"
export QA_OUTPUT_DIR="/custom/output"
```

### Dynamic Configuration
Load configuration from external sources:
```python
# Custom configuration loader
config = load_config_from_database()
initialize_directories(config)
```

### Multiple Environments
Use different config files:
```bash
# Development
cp config-templates/development-config.yaml config.yaml

# Production
cp config-templates/production-config.yaml config.yaml
```

## Support

For configuration issues:

1. **Check this guide** for common scenarios
2. **Review startup messages** for specific errors
3. **Test with minimal configuration** to isolate issues
4. **Check file permissions** and directory accessibility
5. **Use templates** as starting points for custom configurations

## Examples Repository

See the `config-templates/` directory for complete examples:
- Production deployment configurations
- Development environment setups
- Container and Docker configurations
- Testing and CI/CD configurations
- Minimal customization examples
# JSON QA Web Application

A Streamlit-based web application for quality assurance and correction of extracted JSON data from PDF documents. The application provides a user-friendly interface for reviewing, editing, and validating JSON data with real-time diff visualization and audit logging.

## Features

### Core Functionality
- **File Queue Management**: View and claim unverified JSON files for processing
- **Side-by-Side Editing**: PDF preview alongside dynamic form-based JSON editing
- **Real-Time Diff Visualization**: Live comparison showing changes as you edit
- **Schema-Based Validation**: Automatic form generation based on YAML/JSON schemas
- **Audit Trail**: Complete logging of all changes with timestamps and user tracking
- **Multi-User Support**: File locking system prevents concurrent editing conflicts

### User Interface
- **Queue View**: Browse available files, see lock status, and claim files for editing
- **Edit View**: Split-screen interface with PDF on left, editable form on right
- **Audit View**: Review processing history with detailed change logs
- **Schema Editor View**: Interactive editor for creating, modifying, and validating YAML schemas with real-time preview and export options
- **Error Handling**: User-friendly error messages with recovery suggestions

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup
1. Clone or download the project files
2. Navigate to the project directory
3. Install dependencies:
```powershell
pip install -r requirements.txt
```

### Dependencies
- `streamlit>=1.31.0` - Web application framework
- `pydantic>=2.0.0` - Data validation and form generation
- `deepdiff>=6.0.0` - Change detection and diff visualization
- `streamlit-pdf-viewer>=0.0.5` - PDF display component
- `PyYAML>=6.0.0` - YAML schema loading
- `python-dateutil>=2.8.0` - Date/time handling
- `pandas>=1.5.0` - Data manipulation and analysis (used in data processing / tests)
- `PyPDF2>=3.0.0` - PDF reading and manipulation
- `pytest>=7.0.0` - Testing framework
- `pytest-mock>=3.10.0` - pytest plugin for easier mocking in tests

## Usage

### Starting the Application
```powershell
python -m streamlit run streamlit_app.py
```

The application will be available at `http://localhost:8501`

### Directory Structure
The application uses configurable directory paths. By default, it expects:
```
project_root/
├── config.yaml          # Configuration file (optional)
├── json_docs/          # Unverified JSON files to process
├── corrected/           # Processed and corrected JSON files
├── pdf_docs/            # PDF source documents
├── schemas/             # YAML/JSON schema definitions
├── audits/              # Processing audit trail (auto-created)
├── locks/               # File lock management (auto-created)
└── utils/               # Application utilities
```

**Note**: All directory paths can be customized through the `config.yaml` file (see Configuration section below).

### Workflow

1. **Queue View**: 
   - Browse available JSON files in the `json_docs/` directory
   - See file status (available, locked, or processed)
   - Click "Claim" to lock a file for editing

2. **Edit View**:
   - View the corresponding PDF document on the left
   - Edit JSON data using the dynamic form on the right
   - See real-time diff highlighting your changes
   - Submit corrections when complete

3. **Audit View**:
   - Review processing history
   - View detailed change logs for each file
   - Export audit data for reporting

## Schema Configuration

### Quick Start
Place schema files in the `schemas/` directory with `.yaml` extensions. The application uses these schemas to generate forms and validate data.

### Basic Schema Example
```yaml
title: "Simple Invoice Schema"
description: "Basic invoice validation"

fields:
  supplier_name:
    type: "string"
    label: "Supplier Name"
    required: true
    min_length: 2
    max_length: 100
    help: "Name of the supplier or vendor"
  
  invoice_amount:
    type: "number"
    label: "Invoice Amount"
    required: true
    min_value: 0.01
    max_value: 1000000
    help: "Total invoice amount"
  
  currency:
    type: "enum"
    label: "Currency"
    required: false
    choices: ["USD", "EUR", "GBP", "CAD", "AUD", "SGD"]
    default: "USD"
    help: "Invoice currency"
```

### Comprehensive Schema Guide
For detailed information on creating schemas, including all field types, validation rules, and best practices, see the **[Schema Definition Guide](SCHEMA_GUIDE.md)**.

The Schema Editor View provides an interactive interface to create and modify schemas directly within the application, with features like field management, type-specific editors, validation, and export to YAML.

The guide covers:
- All supported field types (string, number, enum, array, object, etc.)
- Validation constraints and rules
- Common patterns and examples
- Troubleshooting schema errors
- Best practices for schema design

### Schema Matching
The application automatically selects schemas based on configuration in `config.yaml`:
```yaml
schema:
  primary_schema: "invoice_schema.yaml"    # Main schema to use
  fallback_schema: "default_schema.yaml"   # Backup if primary fails
```

### Supported Field Types Summary
- `string` - Text input with length/pattern validation
- `number` - Decimal number input with min/max constraints  
- `integer` - Whole number input with min/max constraints
- `boolean` - Checkbox input
- `date` - Date picker
- `datetime` - Date and time picker
- `enum` - Dropdown selection from predefined choices
- `array` - Specialized array editors:
  - scalar arrays use individual item inputs with add/remove controls
  - object arrays use a table-style editor with add/remove row controls
- `object` - Nested form sections for complex data

**📖 See [SCHEMA_GUIDE.md](SCHEMA_GUIDE.md) for complete documentation with examples and troubleshooting.**

## File Management

### Input Files
- Place unverified JSON files in `json_docs/`
- Corresponding PDF files should be in `pdf_docs/` with matching names
- Example: `invoice_001.json` → `invoice_001.pdf`

### Output Files
- Corrected files are saved to `corrected/` directory
- Original files remain unchanged in `json_docs/`
- Audit logs are written to `audit_logs/` in JSONL format

### File Locking
- Files are automatically locked when claimed by a user
- Locks prevent concurrent editing conflicts
- Stale locks (older than 30 minutes) are automatically cleaned up
- Lock status is shown in real-time in the queue view

### Queue Date Filtering
- Date presets (`Today`, `Last 7 days`, `Last 30 days`, `Last 90 days`) evaluate both `created_at` and `modified_at`
- Filtering uses whichever timestamp is more recent for each file
- Custom date range filters are inclusive of both start and end dates

## Configuration

### Directory Configuration
The application supports configurable directory paths through a `config.yaml` file in the project root. If no configuration file is provided, the application uses default directory names.

#### Creating config.yaml
Create a `config.yaml` file in your project root:

```yaml
# JSON QA Webapp Configuration

# Application settings
app:
  name: "JSON QA Webapp"
  version: "1.0.0"
  debug: false

# Schema configuration
schema:
  primary_schema: "invoice_schema.yaml"
  fallback_schema: "default_schema.yaml"

# Directory configuration
directories:
  # Input JSON files awaiting validation
  json_docs: "json_docs"
  
  # Validated and corrected JSON files
  corrected: "corrected"
  
  # Audit logs and history
  audits: "audits"
  
  # Original PDF documents
  pdf_docs: "pdf_docs"
  
  # File locking for concurrency control
  locks: "locks"

# UI configuration
ui:
  page_title: "JSON Quality Assurance"
  sidebar_title: "Navigation"
  
# File processing settings
processing:
  # Lock timeout in minutes
  lock_timeout: 60
  
  # Maximum file size in MB
  max_file_size: 10
```

#### Directory Configuration Examples

**Production Setup with Absolute Paths:**
```yaml
directories:
  json_docs: "/app/data/input"
  corrected: "/app/data/output"
  audits: "/app/logs/audits"
  pdf_docs: "/app/data/documents"
  locks: "/tmp/qa_locks"
```

**Development Setup with Relative Paths:**
```yaml
directories:
  json_docs: "./dev_input"
  corrected: "./dev_output"
  audits: "./dev_logs"
  pdf_docs: "./dev_docs"
  locks: "./dev_locks"
```

**Custom Organizational Structure:**
```yaml
directories:
  json_docs: "data/incoming/json"
  corrected: "data/processed/json"
  audits: "logs/processing"
  pdf_docs: "documents/source"
  locks: "temp/file_locks"
```

#### Configuration Features
- **Automatic Fallback**: Missing config.yaml uses default directory names
- **Partial Configuration**: Specify only directories you want to customize
- **Path Validation**: Application validates paths at startup
- **Directory Creation**: Missing directories are created automatically
- **Error Recovery**: Graceful fallback to defaults if configuration fails
- **Startup Feedback**: Clear messages about configuration status

#### Migration from Hardcoded Paths
Existing deployments continue to work without changes. To migrate:

1. **Create config.yaml** with your current directory structure
2. **Test the configuration** by starting the application
3. **Customize paths** as needed for your environment
4. **Verify functionality** with your existing files

### Application Settings
The application can be configured through Streamlit's configuration system:

```toml
# .streamlit/config.toml
[server]
port = 8501
headless = true

[browser]
gatherUsageStats = false
```

### Environment Variables
- `STREAMLIT_SERVER_PORT` - Server port (default: 8501)
- `STREAMLIT_SERVER_HEADLESS` - Run without browser (default: false)

## Development

### Project Structure
```
├── streamlit_app.py          # Main application entry point
├── utils/
│   ├── audit_view.py         # Audit log interface
│   ├── config_loader.py      # Configuration file loading and validation
│   ├── diff_utils.py         # Change detection and visualization
│   ├── directory_config.py   # Directory path configuration management
│   ├── directory_creator.py  # Automatic directory creation utilities
│   ├── directory_exceptions.py # Custom exceptions for directory operations
│   ├── directory_validator.py # Directory path validation
│   ├── edit_view.py          # PDF and form editing interface
│   ├── error_handler.py      # Error handling utilities
│   ├── file_utils.py         # File operations and locking
│   ├── form_generator.py     # Dynamic form generation
│   ├── graceful_degradation.py # Fallback mechanisms for missing components
│   ├── model_builder.py      # Dynamic Pydantic model creation
│   ├── pdf_viewer.py         # PDF display utilities
│   ├── queue_view.py         # File queue interface
│   ├── schema_editor_view.py # Interactive schema editing interface
│   ├── schema_loader.py      # Schema loading and validation
│   ├── session_manager.py    # Session state management
│   ├── submission_handler.py # Form submission processing
│   └── ui_feedback.py        # User interface feedback
├── schemas/                  # Schema definitions
├── json_docs/                # Input JSON files
├── pdf_docs/                 # PDF source documents
├── tests/                    # Unit and integration tests
└── config.yaml               # Application configuration (optional)
```

### Running Tests
```powershell
# Run all tests
python -m pytest

# Run specific test modules
python -m pytest test_file_utils.py test_diff_utils.py test_model_builder.py

# Run with coverage
python -m pytest --cov=utils --cov-report=html

# CI-style coverage run (term + XML)
python -m pytest --cov=utils --cov-report=term-missing --cov-report=xml

# Enforce coverage policy (core threshold + UI non-regression)
python tools/coverage_policy.py --coverage-xml coverage.xml --policy-file coverage_policy.json
```

### Coverage Policy
- Policy file: `coverage_policy.json`
- Enforcement script: `tools/coverage_policy.py`
- Core logic modules must meet `>= 85%` coverage.
- UI-heavy modules use a non-decreasing baseline check.
- To refresh UI baselines intentionally after accepted improvements:

```powershell
python tools/coverage_policy.py --coverage-xml coverage.xml --policy-file coverage_policy.json --update-ui-baseline
```

### Coverage Snapshot (2026-02-15)
- Before: `537` passing tests, `41%` total `utils` coverage
- After: `633` passing tests, `47%` total `utils` coverage

Key module deltas:
- `utils/pdf_viewer.py`: `39.6% -> 80.2%`
- `utils/file_utils.py`: `70.7% -> 94.2%`
- `utils/schema_loader.py`: `73.2% -> 98.2%`
- `utils/form_data_collector.py`: `90.9% -> 100.0%`
- `utils/queue_filter_state.py`: `53.4% -> 81.7%`

### Adding New Features
1. Create utility modules in `utils/` directory
2. Add corresponding unit tests
3. Update schema format if needed
4. Update this documentation

## Troubleshooting

### Common Issues

**Application won't start**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (3.8+ required)
- Verify Streamlit installation: `python -m streamlit --version`

**Directory configuration errors**
- Check `config.yaml` syntax and format
- Verify directory paths are valid and accessible
- Ensure parent directories exist for custom paths
- Check file permissions for directory creation
- Review startup messages for specific configuration issues

**PDF files not displaying**
- Ensure PDF files are in `pdf_docs/` directory
- Check file naming matches JSON files (e.g., `invoice_001.json` → `invoice_001.pdf`)
- Verify PDF files are not corrupted

**Schema validation errors**
- Check YAML syntax in schema files
- Ensure required fields are properly defined
- Verify field types are supported (see Schema Configuration)

**File locking issues**
- Restart the application to clear stale locks
- Check `locks/` directory permissions
- Ensure multiple users aren't using the same session

### Error Messages
The application provides detailed error messages with suggested actions:
- **File not found**: Check file paths and directory structure
- **Schema validation failed**: Review schema syntax and field definitions
- **Lock conflict**: Wait for other user to finish or contact administrator
- **PDF loading error**: Verify PDF file exists and is readable

## Security Considerations

- The application is designed for internal use within trusted networks
- File uploads are not supported - files must be placed directly in directories
- No user authentication is implemented - consider adding if needed for production
- Audit logs contain all changes - ensure appropriate access controls

## Performance

### Optimization Tips
- Keep JSON files under 10MB for optimal performance
- Use specific schemas rather than generic ones for better validation
- Regularly clean up processed files from `json_docs/` directory
- Monitor `audit_logs/` directory size and archive old logs

### Resource Usage
- Memory usage scales with file size and complexity
- CPU usage is minimal during normal operation
- Disk space requirements depend on audit log retention

## License

This project is provided as-is for internal use. Modify and distribute according to your organization's policies.

## Support

For issues and questions:
1. Check this documentation
2. Review error messages and suggested actions
3. Check the troubleshooting section
4. Examine application logs for detailed error information

## Version History

### v1.2.0 (Current)
- **Schema Editor**: Interactive YAML schema editor with field management, type-specific editors, real-time validation, import/export, and compatibility checks
- **Enhanced Configuration**: Improved config_loader with validation and graceful degradation for missing configs
- **Directory Management**: Dedicated utilities for configurable paths, creation, validation, and error handling
- **Integration Tests**: Comprehensive testing for schema editor and configuration features

### v1.1.0
- **Configurable Directory Paths**: Customize all directory locations via config.yaml
- **Graceful Configuration Handling**: Automatic fallback to defaults if configuration fails
- **Enhanced Error Handling**: Comprehensive error recovery and user guidance
- **Backward Compatibility**: Existing deployments work without changes
- **Startup Validation**: Directory accessibility checks with clear feedback

### v1.0.0
- Initial release with core functionality
- PDF preview and form editing
- Real-time diff visualization
- Multi-user file locking
- Comprehensive audit logging
- Schema-based validation
- Error handling and recovery

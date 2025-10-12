# Array Field Support Sandbox

This standalone Streamlit application provides a testing environment for array field functionality before integration into the main JSON QA webapp codebase.

## Purpose

The sandbox allows developers and testers to:
- Test array editing functionality in isolation
- Verify user experience and interface design
- Validate array field configurations
- Collect feedback before main codebase integration

## Structure

```
sandbox/
├── array_sandbox_app.py          # Main Streamlit application
├── test_schemas/                  # Test schema definitions
│   ├── insurance_document_schema.yaml
│   └── purchase_order_schema.yaml
├── test_data/                     # Sample test data
│   ├── insurance_document_sample.json
│   └── purchase_order_sample.json
└── README.md                      # This file
```

## Running the Sandbox

1. Navigate to the sandbox directory:
   ```bash
   cd sandbox
   ```

2. Run the Streamlit application:
   ```bash
   streamlit run array_sandbox_app.py
   ```

3. Open your browser to the displayed URL (typically http://localhost:8501)

## Test Areas

### 1. Scalar Array Editor
- Test editing arrays of simple values (strings, numbers, booleans, dates)
- Add/remove individual items
- Validate constraints (min_length, max_length, patterns, etc.)

### 2. Object Array Editor  
- Test editing arrays of complex objects
- Table-style interface with add/remove rows
- Column-specific validation and data types

### 3. Schema Editor
- Test creating array field configurations
- Configure scalar and object array properties
- Generate and validate YAML output

### 4. Validation Testing
- Test validation rules and error handling
- Real-time validation feedback
- Error message clarity and context

### 5. Test Scenarios
- Predefined test cases for manual verification
- Feedback collection forms
- Test verification checklists

## Test Schemas

### Insurance Document
- **Scalar Arrays**: `serial_numbers`, `tags`
- **Validation**: Pattern matching, length constraints
- **Use Case**: Equipment tracking with categorization

### Purchase Order
- **Object Arrays**: `line_items` with multiple properties
- **Validation**: Required fields, numeric constraints
- **Use Case**: Complex business documents with line items

## Development Notes

This sandbox is independent of the main codebase to allow:
- Rapid prototyping without affecting production code
- Safe testing of experimental features
- Easy rollback of changes
- Isolated dependency management

Once functionality is verified in the sandbox, it will be ported to the main application following the implementation plan.

## Requirements Addressed

- **8.1**: Separate Streamlit application independent of main codebase
- **8.7**: Clear instructions and test scenarios for manual verification
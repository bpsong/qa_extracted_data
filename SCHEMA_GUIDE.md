# Schema Definition Guide

## Overview

This guide provides documentation for creating schema files that define how JSON data should be validated and displayed in the JSON QA webapp. Schemas control form generation, validation rules, and user interface behavior.

**Current Implementation Status**: This system currently supports scalar fields (string, number, integer, boolean, date, datetime, enum) and has been enhanced to support:
- Arrays of scalar values (e.g., `["SerialNo1", "SerialNo2"]`)
- Arrays of objects with one level of nesting (e.g., line items with Description and Quantity fields)

**Note**: Some advanced features described in this guide are planned for future implementation and are clearly marked as such.

## Schema File Format

Schemas are defined in YAML format and placed in the `schemas/` directory. Each schema file defines the structure and validation rules for JSON documents.

### Basic Schema Structure

```yaml
title: "Document Type Name"
description: "Brief description of what this schema validates"

fields:
  field_name:
    type: "field_type"
    label: "Display Label"
    required: true/false
    # Additional constraints based on field type
```

## Currently Supported Field Types

### 1. String Fields ✅ IMPLEMENTED

**Type**: `string`
**Widget**: Text input or text area

```yaml
supplier_name:
  type: "string"
  label: "Supplier Name"
  required: true
  min_length: 2          # Minimum character count
  max_length: 100        # Maximum character count (>100 = text area)
  pattern: "^[A-Za-z\\s]+$"  # Regex validation pattern
  help: "Enter the supplier company name"
  default: ""            # Default value (optional)
```

**Constraints**:
- `min_length`: Minimum number of characters (integer)
- `max_length`: Maximum number of characters (integer)
- `pattern`: Regular expression for validation (string)
- `default`: Default value (string)

### 2. Number Fields ✅ IMPLEMENTED

**Type**: `number`
**Widget**: Number input with decimal support

```yaml
invoice_amount:
  type: "number"
  label: "Invoice Amount"
  required: true
  min_value: 0.01        # Minimum value
  max_value: 1000000     # Maximum value
  step: 0.01             # Input step size
  help: "Enter the total invoice amount"
  default: 0.00
```

**Constraints**:
- `min_value`: Minimum allowed value (number)
- `max_value`: Maximum allowed value (number)
- `step`: Step size for input controls (number, default: 0.01)
- `default`: Default value (number)

### 3. Integer Fields ✅ IMPLEMENTED

**Type**: `integer`
**Widget**: Number input (whole numbers only)

```yaml
quantity:
  type: "integer"
  label: "Quantity"
  required: true
  min_value: 1
  max_value: 9999
  step: 1
  help: "Enter the quantity ordered"
  default: 1
```

**Constraints**:
- `min_value`: Minimum allowed value (integer)
- `max_value`: Maximum allowed value (integer)
- `step`: Step size (integer, default: 1)
- `default`: Default value (integer)

### 4. Enum Fields (Dropdowns) ✅ IMPLEMENTED

**Type**: `enum`
**Widget**: Selectbox dropdown

```yaml
currency:
  type: "enum"
  label: "Currency"
  required: false
  choices: ["USD", "EUR", "GBP", "CAD", "AUD", "SGD"]
  default: "USD"
  help: "Select the invoice currency"
```

**Constraints**:
- `choices`: List of allowed values (required for enum)
- `default`: Default selection (must be in choices list)

### 5. Boolean Fields ✅ IMPLEMENTED

**Type**: `boolean`
**Widget**: Checkbox

```yaml
is_approved:
  type: "boolean"
  label: "Approved"
  required: false
  default: false
  help: "Check if this invoice is approved"
```

**Constraints**:
- `default`: Default state (true/false)

### 6. Date Fields ✅ IMPLEMENTED

**Type**: `date`
**Widget**: Date picker

```yaml
invoice_date:
  type: "date"
  label: "Invoice Date"
  required: true
  help: "Select the invoice date"
```

**Constraints**:
- No specific constraints (uses browser date picker)
- Values are stored as ISO date strings (YYYY-MM-DD)

### 7. DateTime Fields ⚠️ PLANNED

**Type**: `datetime`
**Widget**: Date and time picker

**Note**: This field type is planned for future implementation.

```yaml
created_timestamp:
  type: "datetime"
  label: "Created At"
  required: false
  help: "When this record was created"
```

**Constraints**:
- No specific constraints
- Values are stored as ISO datetime strings

### 8. Array Fields ✅ FULLY IMPLEMENTED

**Type**: `array`
**Widget**: Specialized array editors (scalar array editor or table-style object array editor)

**Implementation Status:**
- ✅ **Core System**: Full support for arrays in JSON processing, validation, and form generation
- ✅ **Edit Queue**: User-friendly array editors with add/remove/edit capabilities
- ✅ **Schema Editor**: Visual array field creation and configuration via ArrayFieldManager
- ✅ **Validation**: Comprehensive validation with detailed error reporting

The system supports two types of arrays:

#### 8a. Array of Scalar Values ✅ FULLY IMPLEMENTED

For arrays containing simple values like strings, numbers, integers, booleans, dates, or enums.

**Supported Scalar Types:**
- `string` - Text values with optional length and pattern constraints
- `number` - Decimal numbers with min/max and step constraints
- `integer` - Whole numbers with min/max constraints
- `boolean` - True/false values
- `date` - Date values (ISO format: YYYY-MM-DD)
- `enum` - Predefined choices with dropdown selection

**Schema Definition:**
```yaml
serial_numbers:
  type: "array"
  label: "Serial Numbers"
  required: false
  help: "List of equipment serial numbers"
  items:
    type: "string"
    min_length: 5
    max_length: 20
    pattern: "^SN[0-9]{4}$"  # Example: SN1234
```

**Example with Enum Items:**
```yaml
status_history:
  type: "array"
  label: "Status History"
  help: "List of status values"
  items:
    type: "enum"
    choices: ["pending", "approved", "rejected", "completed"]
    default: "pending"
```

**Example with Number Items:**
```yaml
measurements:
  type: "array"
  label: "Measurements"
  help: "List of measurement values"
  items:
    type: "number"
    min_value: 0.0
    max_value: 1000.0
    step: 0.01
```

**Example JSON data**: `["SN1234", "SN5678", "SN9012"]`

**UI Rendering**: Scalar arrays are rendered with a user-friendly editor that provides:
- **✅ Individual Item Editing**: Each item gets its own input widget (text, number, date picker, dropdown, etc.)
- **✅ Add Items**: "Add Item" button to append new items to the array
- **✅ Remove Items**: "Remove Item" button next to each item for deletion
- **✅ Type-Specific Widgets**: 
  - String: Text input with validation
  - Number/Integer: Number input with min/max/step controls
  - Boolean: Checkbox
  - Date: Date picker
  - Enum: Dropdown with predefined choices
- **✅ Real-time Validation**: Constraints enforced as you type
- **✅ Reset Functionality**: Reset button to restore original values

#### 8b. Array of Objects ✅ FULLY IMPLEMENTED

For arrays containing objects with multiple properties (like line items, addresses, or contact information).

**Supported Property Types:**
- `string` - Text fields with optional constraints
- `number` - Decimal number fields
- `integer` - Whole number fields
- `boolean` - Checkbox fields
- `date` - Date picker fields
- `enum` - Dropdown fields with predefined choices

**Schema Definition:**
```yaml
line_items:
  type: "array"
  label: "Line Items"
  required: false
  help: "Invoice line items"
  items:
    type: "object"
    properties:
      description:
        type: "string"
        label: "Item Description"
        required: true
        max_length: 200
      quantity:
        type: "integer"
        label: "Quantity"
        required: true
        min_value: 1
      unit_price:
        type: "number"
        label: "Unit Price"
        required: true
        min_value: 0.01
        step: 0.01
      taxable:
        type: "boolean"
        label: "Taxable"
        required: false
        default: true
```

**Example with Enum Properties:**
```yaml
addresses:
  type: "array"
  label: "Addresses"
  help: "Customer addresses"
  items:
    type: "object"
    properties:
      address_type:
        type: "enum"
        label: "Type"
        required: true
        choices: ["billing", "shipping", "both"]
        default: "billing"
      street:
        type: "string"
        label: "Street Address"
        required: true
      city:
        type: "string"
        label: "City"
        required: true
      postal_code:
        type: "string"
        label: "Postal Code"
        required: true
        pattern: "^[0-9]{5}$"
```

**Example JSON data**:
```json
[
  {
    "description": "Widget A",
    "quantity": 10,
    "unit_price": 25.50,
    "taxable": true
  },
  {
    "description": "Widget B",
    "quantity": 5,
    "unit_price": 42.00,
    "taxable": false
  }
]
```

**UI Rendering**: Object arrays are rendered using a table-style editor that provides:
- **✅ Table Interface**: Spreadsheet-like editing with columns for each property
- **✅ Add Rows**: "Add Row" button to create new objects
- **✅ Delete Rows**: Manual row deletion controls
- **✅ Edit Cells**: Click any cell to edit its value
- **✅ Type-Specific Columns**: 
  - String: Text input columns
  - Number: Number input with formatting (%.2f for decimals, %d for integers)
  - Boolean: Checkbox columns
  - Date: Date picker columns
  - Enum: Dropdown columns (when supported)
- **✅ Column Configuration**: Automatic column setup based on property types
- **✅ Data Validation**: Real-time validation of required fields and constraints
- **✅ NaN Cleanup**: Automatic conversion of pandas NaN values to None for JSON compatibility
- **✅ Type Normalization**: Automatic conversion of numpy types to native Python types
- **✅ Reset Functionality**: Reset button to restore original array

**Technical Implementation:**
- Uses Streamlit's `st.data_editor` with `num_rows="dynamic"`
- Requires pandas library for DataFrame operations
- Automatic type conversion for JSON serialization
- Column configuration based on property schema definitions

**Current Limitations**:
- Object arrays are limited to one level of nesting (no nested objects within objects)
- Arrays of arrays are not supported
- Object properties must be scalar types (string, number, integer, boolean, date, enum)

**Constraints**:
- `items`: Definition of array item structure (required)
- For scalar arrays: `items.type` must be a scalar type
- For object arrays: `items.type: "object"` with `properties` containing only scalar field definitions

### 9. Object Fields ⚠️ LIMITED IMPLEMENTATION / ❌ SCHEMA EDITOR

**Type**: `object`
**Widget**: Nested form section

**Implementation Status:**
- ⚠️ **Core System**: Limited support, primarily within arrays
- ❌ **Schema Editor**: Visual schema editor does not support creating/editing object fields yet

**Current Status**: Object fields are primarily supported within arrays (see Array of Objects above). Standalone object fields may have limited support.

```yaml
# Currently supported mainly within arrays
billing_address:
  type: "object"
  label: "Billing Address"
  help: "Customer billing address"
  properties:
    street:
      type: "string"
      label: "Street Address"
      required: true
    city:
      type: "string"
      label: "City"
      required: true
```

**Constraints**:
- `properties`: Object field definitions (same format as top-level fields)
- Currently works best within array contexts
- Nested objects (objects within objects) are not supported

## Common Field Properties

All field types support these common properties:

```yaml
field_name:
  type: "field_type"
  label: "Display Label"      # Required: User-friendly field name
  required: true              # Optional: Whether field is mandatory (default: false)
  help: "Help text"          # Optional: Tooltip/help text for users
  readonly: false            # Optional: Make field read-only (default: false)
  default: value             # Optional: Default value (type must match field type)
```

## Schema Examples

### Simple Invoice Schema (Currently Supported)

```yaml
title: "Simple Invoice Schema"
description: "Basic invoice validation with essential fields"

fields:
  supplier_name:
    type: "string"
    label: "Supplier Name"
    required: true
    help: "Name of the supplier or vendor"

  purchase_order_number:
    type: "string"
    label: "Purchase Order Number"
    required: true
    help: "PO number from the invoice"

  invoice_amount:
    type: "number"
    label: "Invoice Amount"
    required: true
    help: "Total invoice amount"

  currency:
    type: "enum"
    label: "Currency"
    required: false
    choices: ["USD", "EUR", "GBP", "CAD", "AUD", "SGD"]
    default: "USD"
    help: "Invoice currency"

  invoice_date:
    type: "date"
    label: "Invoice Date"
    required: true
    help: "Date on the invoice"

  is_approved:
    type: "boolean"
    label: "Approved"
    required: false
    default: false
    help: "Approval status"
```

### Insurance Document Schema (Based on Current Data)

```yaml
title: "Insurance Document Schema"
description: "Schema for insurance policy documents"

fields:
  supplier_name:
    type: "string"
    label: "Supplier Name"
    required: true
    help: "Insurance company name"

  client_name:
    type: "string"
    label: "Client Name"
    required: true
    help: "Name of the insured client"

  client:
    type: "string"
    label: "Client Address"
    required: false
    help: "Client's business address"

  invoice_amount:
    type: "number"
    label: "Invoice Amount"
    required: true
    help: "Premium amount"

  insurance_start_date:
    type: "date"
    label: "Insurance Start Date"
    required: true
    help: "Policy effective start date"

  insurance_end_date:
    type: "date"
    label: "Insurance End Date"
    required: true
    help: "Policy expiration date"

  policy_number:
    type: "string"
    label: "Policy Number"
    required: true
    help: "Unique policy identifier"

  serial_numbers:
    type: "array"
    label: "Serial Numbers"
    required: false
    help: "List of covered equipment serial numbers"
    items:
      type: "string"

  invoice_type:
    type: "enum"
    label: "Invoice Type"
    required: false
    choices: ["debit", "credit"]
    default: "debit"
    help: "Type of invoice transaction"
```

### Purchase Order Schema (Based on Current Data)

```yaml
title: "Purchase Order Schema"
description: "Schema for purchase order documents with line items"

fields:
  supplier_name:
    type: "string"
    label: "Supplier Name"
    required: true
    help: "Name of the supplier company"

  purchase_order_number:
    type: "string"
    label: "Purchase Order Number"
    required: true
    help: "PO number from the document"

  invoice_amount:
    type: "number"
    label: "Invoice Amount"
    required: true
    help: "Total invoice amount"

  project_number:
    type: "string"
    label: "Project Number"
    required: false
    help: "Associated project identifier"

  # Line Items Array (Fully Supported in Core System)
  items:
    type: "array"
    label: "Line Items"
    help: "List of items ordered"
    items:
      type: "object"
      properties:
        description:
          type: "string"
          label: "Description"
          required: true
          help: "Item description"
        quantity:
          type: "string"  # Note: Currently extracted as string
          label: "Quantity"
          required: true
          help: "Quantity ordered (with units)"

  # Note: update_reference and nanoid fields are system-generated
  # and should not be included in user-editable schemas
```

### Real Working Example: Invoice Schema

The system already includes a working `invoice_schema.yaml` with array of objects:

```yaml
"Line items":
  type: array
  label: "Line Items"
  required: false
  help: "Individual items on the invoice"
  items:
    type: object
    properties:
      "Item description":
        type: string
        label: "Item Description"
        required: true
        max_length: 200
      "Quantity":
        type: number
        label: "Quantity"
        required: true
        min_value: 0
      "Unit price":
        type: number
        label: "Unit Price"
        required: true
        min_value: 0
      "Total price":
        type: number
        label: "Total Price"
        required: true
        min_value: 0
```

This demonstrates that arrays of objects are fully functional in the core system.

## Creating Array Fields in Schema Editor

### Using ArrayFieldManager ✅

The Schema Editor now includes full support for creating and configuring array fields through the ArrayFieldManager component.

**Accessing Array Field Configuration:**
1. Open Schema Editor from the main navigation
2. Create a new field or edit an existing field
3. Select "array" as the field type
4. ArrayFieldManager interface appears with array-specific options

### Creating Scalar Arrays

**Step-by-Step Process:**

1. **Select Array Type**: Choose "scalar" from the Array Type dropdown
2. **Choose Item Type**: Select the type of values in your array:
   - `string` - Text values
   - `integer` - Whole numbers
   - `number` - Decimal numbers
   - `boolean` - True/false values
   - `date` - Date values
   - `enum` - Predefined choices

3. **Configure Constraints** (type-specific):

   **For String Items:**
   - Min Length: Minimum character count (optional)
   - Max Length: Maximum character count
   - Pattern: Regular expression for validation (optional)

   **For Number/Integer Items:**
   - Min Value: Minimum allowed value (supports negative values)
   - Max Value: Maximum allowed value
   - Step: Input step size (for numbers only)

   **For Boolean Items:**
   - Default Value: Checkbox for default state

   **For Enum Items:**
   - Enum Choices: Enter choices one per line
   - Default Choice: Select default from dropdown

4. **Save Field**: Click "Save Field" to add to schema

**Example: Creating a Serial Numbers Array**
```
Field Name: serial_numbers
Label: Serial Numbers
Type: array
Array Type: scalar
Item Type: string
Min Length: 5
Max Length: 20
Pattern: ^SN[0-9]{4}$
```

### Creating Object Arrays

**Step-by-Step Process:**

1. **Select Array Type**: Choose "object" from the Array Type dropdown
2. **Add Properties**: Define the properties for each object in the array

   **Adding a Property:**
   - Enter property name in "New Property Name" field
   - Click "Add Property" button
   - Property appears in expandable section

3. **Configure Each Property**:
   - **Label**: User-friendly display name
   - **Type**: Select from string, integer, number, boolean, date, enum
   - **Required**: Check if property is mandatory
   - **Constraints**: Configure type-specific constraints (same as scalar arrays)

4. **Manage Properties**:
   - **Edit**: Expand property section to modify configuration
   - **Delete**: Click trash icon (🗑️) to remove property (with confirmation)
   - **Add More**: Repeat process to add additional properties

5. **Save Field**: Click "Save Field" to add to schema

**Example: Creating a Line Items Array**
```
Field Name: line_items
Label: Line Items
Type: array
Array Type: object

Properties:
  1. description
     - Label: Item Description
     - Type: string
     - Required: Yes
     - Max Length: 200
  
  2. quantity
     - Label: Quantity
     - Type: integer
     - Required: Yes
     - Min Value: 1
  
  3. unit_price
     - Label: Unit Price
     - Type: number
     - Required: Yes
     - Min Value: 0.01
     - Step: 0.01
  
  4. taxable
     - Label: Taxable
     - Type: boolean
     - Required: No
     - Default: true
```

### ArrayFieldManager API Reference

**Key Methods:**

```python
ArrayFieldManager.render_array_field_config(field_id: str, field: Dict[str, Any]) -> None
```
Main entry point for rendering array field configuration interface.
- **field_id**: Unique identifier for the field (used for widget keys)
- **field**: Field configuration dictionary (modified in place)

```python
ArrayFieldManager.validate_array_config(field_config: Dict[str, Any]) -> List[str]
```
Validates array field configuration and returns list of error messages.
- Returns empty list if configuration is valid
- Returns list of error strings if validation fails

```python
ArrayFieldManager.generate_array_yaml(field_name: str, field_config: Dict[str, Any]) -> str
```
Generates YAML representation of array field configuration.
- **field_name**: Name of the field
- **field_config**: Field configuration dictionary
- Returns YAML string suitable for schema files

**Usage Example:**
```python
import streamlit as st
from utils.array_field_manager import ArrayFieldManager

# Initialize field configuration
field_config = {
    'type': 'array',
    'label': 'My Array Field',
    'required': False,
    'items': {'type': 'string'}
}

# Render configuration interface
ArrayFieldManager.render_array_field_config('my_field', field_config)

# Validate configuration
errors = ArrayFieldManager.validate_array_config(field_config)
if errors:
    for error in errors:
        st.error(error)
else:
    # Generate YAML
    yaml_output = ArrayFieldManager.generate_array_yaml('my_field', field_config)
    st.code(yaml_output, language='yaml')
```

### Best Practices for Array Field Creation

**1. Property Naming:**
- Use descriptive, clear property names
- Use snake_case for consistency (e.g., `unit_price`, not `unitPrice`)
- Avoid special characters except underscores

**2. Required Fields:**
- Mark truly essential properties as required
- Consider user experience - too many required fields can be frustrating
- Provide sensible defaults for optional fields

**3. Constraints:**
- Set realistic min/max values based on your data
- Use patterns for formatted strings (serial numbers, codes, etc.)
- Test constraints with sample data before deploying

**4. Object Array Design:**
- Keep object arrays focused - don't add too many properties
- Group related data in the same object
- Consider splitting complex structures into multiple arrays if needed

**5. Enum Choices:**
- Provide clear, descriptive choice labels
- Order choices logically (alphabetically or by frequency of use)
- Set appropriate defaults for better user experience

## Array Editing Capabilities

### Arrays of Scalars - Individual Item Editing ✅

When users encounter a scalar array in the edit queue, they get an intuitive editor:

**✅ What Users Can Do:**
- **Add Items**: Click "Add Item" button to append new items
- **Remove Items**: Click "Remove Item" button next to any item
- **Edit Values**: Each item has its own input widget based on type
- **Type-Safe Input**: Appropriate widgets for each type (text, number, date picker, dropdown)
- **Validation**: Real-time validation based on schema constraints

**Example User Workflow (String Array):**
1. User sees list of serial numbers with individual text inputs
2. User clicks "Add Item" to add a new serial number
3. User types "SN1234" in the new input field
4. System validates against pattern constraint
5. User can remove any item by clicking its "Remove Item" button
6. User clicks "Reset" to restore original values if needed

**Example User Workflow (Enum Array):**
1. User sees list of status values with dropdown selectors
2. User clicks "Add Item" to add a new status
3. New dropdown appears with available choices
4. User selects "approved" from dropdown
5. System validates selection against allowed choices

### Arrays of Objects - Table Editing ✅

When users encounter an object array in the edit queue, they get a powerful table editor:

**✅ What Users Can Do:**
- **Add Rows**: Click "Add Row" button to create new objects
- **Delete Rows**: Use row controls to remove objects
- **Edit Cells**: Click any cell to edit its value
- **Type-Safe Editing**: Each column respects its data type
- **Validation**: Real-time validation based on schema constraints

**Example User Workflow:**
1. User sees a table with existing line items (Description, Quantity, Unit Price columns)
2. User clicks "Add Row" to add a new line item
3. User fills in Description: "New Widget", Quantity: 5, Unit Price: 12.50
4. User can edit existing rows by clicking into cells
5. User can delete rows using the row controls
6. All changes are validated against the schema before submission
7. User clicks "Reset" to restore original array if needed

**Technical Implementation:**
- Uses `st.data_editor` with `num_rows="dynamic"`
- Column types configured based on schema property types
- Automatic NaN cleanup for JSON compatibility
- Type normalization for pandas/numpy types
- Returns updated array as list of dictionaries

### Future Enhancement Example (Not Yet Implemented)

```yaml
# This example shows planned features - DO NOT USE YET
title: "Advanced Purchase Order Schema"
description: "Future implementation with advanced features"

fields:
  # ... basic fields ...
  
  # Nested objects (PLANNED)
  vendor_info:
    type: "object"
    label: "Vendor Information"
    properties:
      name:
        type: "string"
        label: "Vendor Name"
        required: true
      contact_email:
        type: "string"
        label: "Contact Email"
        help: "Valid email address"

  # Advanced validation (PLANNED)
  po_number:
    type: "string"
    label: "PO Number"
    required: true
    pattern: "^PO-\\d{8}$"
    help: "8-digit PO number (PO-12345678)"

  # Calculated fields (PLANNED)
  total_amount:
    type: "number"
    label: "Total Amount"
    readonly: true
    help: "Calculated automatically"
```

## Best Practices

### 1. Field Naming
- Use descriptive, clear field names
- Use snake_case for field names (e.g., `supplier_name`, not `supplierName`)
- Avoid special characters except underscores
- Keep names concise but meaningful

### 2. Labels and Help Text
- Provide user-friendly labels that are different from field names
- Include help text for fields that might be unclear
- Explain format requirements in help text
- Use consistent terminology across schemas

### 3. Validation Rules
- Set appropriate min/max constraints for numbers
- Use regex patterns for formatted strings (phone numbers, IDs, etc.)
- Mark truly required fields as required
- Provide sensible default values where appropriate

### 4. Schema Organization
- Group related fields using objects when logical
- Use arrays for repeating data structures
- Keep schemas focused on a single document type
- Document the purpose of each schema in the description

### 5. Performance Considerations
- Avoid overly complex nested structures
- Limit array sizes for better UI performance
- Use readonly fields for calculated values
- Keep regex patterns simple and efficient

## Validation Rules Reference

### String Validation
```yaml
# Length constraints
min_length: 5          # Minimum 5 characters
max_length: 100        # Maximum 100 characters

# Pattern matching (regex)
pattern: "^[A-Z]{2}\\d{4}$"    # Two letters + 4 digits
pattern: "^\\d{3}-\\d{3}-\\d{4}$"  # Phone: 123-456-7890
pattern: "^[\\w\\.-]+@[\\w\\.-]+\\.[a-zA-Z]{2,}$"  # Email format
```

### Number Validation
```yaml
# Value constraints
min_value: 0           # Minimum value (inclusive)
max_value: 1000000     # Maximum value (inclusive)
step: 0.01             # Input step size

# Integer-specific
type: "integer"        # Whole numbers only
step: 1                # Integer step
```

### Enum Validation
```yaml
# Choice constraints
choices: ["option1", "option2", "option3"]  # Allowed values
default: "option1"     # Must be in choices list
```

## Troubleshooting

### Common Schema Errors

**1. Invalid YAML Syntax**
```
Error: YAML parsing failed
```
- Check indentation (use spaces, not tabs)
- Ensure proper quoting of strings with special characters
- Validate YAML syntax using an online validator

**2. Missing Required Properties**
```
Error: Field 'field_name' missing required property 'type'
```
- Every field must have a `type` property
- Every field must have a `label` property
- Check spelling of property names

**3. Invalid Field Type**
```
Error: Unsupported field type 'invalid_type'
```
- Use only supported types: string, number, integer, boolean, date, datetime, enum, array, object
- Check spelling of type names

**4. Invalid Constraints**
```
Error: min_value must be less than max_value
```
- Ensure min_value < max_value for numbers
- Ensure min_length < max_length for strings
- Check that default values meet constraints

**5. Enum Configuration Errors**
```
Error: enum type requires 'choices' property
```
- Enum fields must have a `choices` array
- Default value must be in the choices list
- Choices cannot be empty

**6. Array/Object Configuration Errors**
```
Error: array type requires 'items' property
```
- Array fields must define `items` structure
- Object fields must define `properties`
- Nested objects follow the same rules as top-level fields

### Array Field Troubleshooting

**Common Array Issues:**

**1. Array Items Not Validating**
```
Error: serial_numbers[2] must match pattern ^SN[0-9]{4}$
```
**Solution**: Check that each item in your array meets the defined constraints. The error message shows the specific array index (e.g., `[2]` means the third item).

**2. Object Array Property Missing**
```
Error: line_items[0].quantity is required
```
**Solution**: Ensure all required properties are present in each object. The error shows both the array index and property name.

**3. Cannot Add Properties in Schema Editor**
```
Issue: Property name field doesn't reset after adding a property
```
**Solution**: This was a known issue that has been fixed. If you encounter this:
- Ensure you're using the latest version
- Try refreshing the page
- Check that property names are unique

**4. Enum Items Not Showing Dropdown**
```
Issue: Enum array items show text input instead of dropdown
```
**Solution**: Verify your schema has both `choices` and `default` defined:
```yaml
items:
  type: "enum"
  choices: ["option1", "option2", "option3"]
  default: "option1"
```

**5. Object Array Shows Empty Table**
```
Issue: Table editor appears but has no columns
```
**Solution**: Ensure your object array has properties defined:
```yaml
items:
  type: "object"
  properties:
    field1:
      type: "string"
      label: "Field 1"
```

**6. Negative Numbers Not Accepted**
```
Issue: Cannot enter negative values even though min_value is negative
```
**Solution**: Ensure default values respect negative bounds:
```yaml
items:
  type: "number"
  min_value: -100  # Negative minimum
  default: -10     # Default must respect minimum
```

**7. Array Data Not Saving**
```
Issue: Array changes don't persist after submission
```
**Solution**: 
- Check validation errors - arrays won't save if validation fails
- Ensure all required properties in object arrays are filled
- Check browser console for JavaScript errors
- Verify JSON serialization compatibility (no NaN values)

**8. State Leakage Between Array Fields**
```
Issue: Editing one array field affects another array field
```
**Solution**: This was a known issue with session state keys that has been fixed. If you encounter this:
- Refresh the page to clear session state
- Ensure you're using the latest version with proper key namespacing

**9. Pandas/NumPy Type Errors**
```
Error: Object of type 'int64' is not JSON serializable
```
**Solution**: This should be handled automatically by the system. If you encounter this:
- Report as a bug - the system should auto-convert numpy types
- Temporary workaround: Manually convert values to native Python types

**10. Large Array Performance Issues**
```
Issue: Editing arrays with 100+ items is slow
```
**Solution**:
- Consider breaking large arrays into smaller chunks
- Use pagination if available
- For very large datasets, consider alternative data entry methods
- Performance is optimized for arrays up to 500 items

### Array Validation Error Messages

**Understanding Array Error Paths:**

Array validation errors use a specific path format to help you locate issues:

- `field_name[index]` - Error in scalar array item
  - Example: `serial_numbers[2]` means the third item in serial_numbers array
  
- `field_name[index].property` - Error in object array property
  - Example: `line_items[0].quantity` means the quantity property of the first line item

**Common Validation Messages:**

```
"serial_numbers[3] cannot be empty"
→ The fourth serial number is empty but required

"line_items[1].unit_price must be greater than 0"
→ The second line item has an invalid unit price

"tags[0] must match pattern ^[A-Z]{3}$"
→ The first tag doesn't match the required pattern (3 uppercase letters)

"addresses[2].postal_code is required"
→ The third address is missing the required postal code
```

### Debugging Tips

1. **Start Simple**: Begin with basic string/number fields, then add complexity
2. **Test Incrementally**: Add one field at a time and test
3. **Use Examples**: Copy from working schemas and modify
4. **Check Logs**: Application logs show detailed validation errors
5. **Validate YAML**: Use online YAML validators to check syntax
6. **Test with Sample Data**: Use real JSON data to test array configurations
7. **Check Array Indices**: Validation errors show specific array indices - use them to locate issues
8. **Verify Property Names**: Ensure property names in schema match your JSON data exactly

### Schema Validation Checklist

Before deploying a schema, verify:

**Basic Requirements**:
- [ ] YAML syntax is valid
- [ ] All fields have `type` and `label` properties
- [ ] Field types are from the supported list (string, number, integer, boolean, date, enum, array)
- [ ] Schema has title and description

**Array Field Requirements**:
- [ ] Array fields have `items` definitions
- [ ] Scalar arrays specify item type (string, number, integer, boolean, date, enum)
- [ ] Object arrays have `properties` defined with at least one property
- [ ] Object array properties are scalar types only (no nested objects)
- [ ] Enum items/properties have `choices` arrays defined
- [ ] Default values respect all constraints (including negative bounds)
- [ ] No arrays within arrays (not supported)
- [ ] No objects within objects (not supported)

**Validation Requirements**:
- [ ] Required properties are marked appropriately
- [ ] Min/max constraints are logical (min < max)
- [ ] Patterns are valid regular expressions
- [ ] Enum choices are non-empty
- [ ] Default values are in enum choices lists

**Best Practices**:
- [ ] Help text is clear and helpful
- [ ] Field names use snake_case or match your JSON data exactly
- [ ] Required fields are marked appropriately
- [ ] Field labels are user-friendly
- [ ] Array constraints are realistic for your data
- [ ] Object arrays have reasonable number of properties (< 10 recommended)

## Schema Editor Full Feature Support

### Schema Editor Capabilities ✅

The **Schema Editor** (visual YAML editor in the webapp) now supports all field types including arrays:

**✅ Fully Supported in Schema Editor:**
- **Scalar Fields**: string, number, integer, boolean, enum, date, datetime
- **Array Fields**: Both scalar arrays and object arrays via ArrayFieldManager
- **Field Properties**: label, required, help, min/max values, choices, patterns
- **Array Configuration**: Item types, constraints, object properties
- **Import/Export**: Full round-trip support for all field types

**✅ Array-Specific Features:**
- Visual array type selection (scalar vs object)
- Item type configuration with constraints
- Object property management (add/edit/delete)
- Real-time YAML generation
- Validation before save

**Current Limitations:**
- No nested objects within objects
- No arrays within arrays
- Object array properties must be scalar types

### Creating Arrays in Schema Editor

**Quick Start:**
1. Navigate to Schema Editor
2. Click "Add Field" or edit existing field
3. Select "array" as field type
4. Choose array type (scalar or object)
5. Configure item type and constraints
6. For object arrays, add properties
7. Save field

**See "Creating Array Fields in Schema Editor" section above for detailed instructions.**

### Importing Schemas with Arrays

**Full Import Support:**
- Schemas with scalar arrays import correctly
- Schemas with object arrays import with all properties
- All constraints and validation rules preserved
- No data loss during import/export cycle

**Import Process:**
1. Click "Import Schema" in Schema Editor
2. Select YAML file with array fields
3. System loads all fields including arrays
4. Edit arrays using ArrayFieldManager interface
5. Export updated schema

**Example: Importing Invoice Schema**
```yaml
# invoice_schema.yaml
title: "Invoice Schema"
fields:
  line_items:
    type: "array"
    label: "Line Items"
    items:
      type: "object"
      properties:
        description:
          type: "string"
          label: "Description"
        quantity:
          type: "integer"
          label: "Quantity"
```

After import:
- `line_items` field appears in field list
- Click edit to see ArrayFieldManager interface
- All properties (description, quantity) are editable
- Can add/remove properties
- Can modify constraints

## Implementation Status and Limitations

### Fully Implemented ✅

**Core System (JSON Processing & Validation):**
- **Scalar Fields**: string, number, integer, boolean, date, enum
- **Array of Scalars**: Arrays containing simple values with user-friendly editors
- **Array of Objects**: Arrays containing objects with table-style editing
- **Comprehensive Validation**: Required fields, type constraints, min/max values, patterns, enum choices
- **Form Generation**: Automatic UI generation for all supported field types
- **Error Reporting**: Detailed validation errors with array indices and property paths

**Edit Queue Interface:**
- **Scalar Array Editor**: Individual item editing with add/remove buttons
- **Object Array Editor**: Table-style editing with add/remove rows
- **Type-Specific Widgets**: Appropriate input widgets for each data type
- **Real-time Validation**: Immediate feedback on constraint violations
- **Reset Functionality**: Restore original values for any array field

**Schema Editor UI:**
- **All Field Types**: string, number, integer, boolean, enum, date, datetime, array
- **ArrayFieldManager**: Visual array field creation and configuration
- **Scalar Arrays**: Full configuration with item types and constraints
- **Object Arrays**: Property management with add/edit/delete operations
- **Import/Export**: Full round-trip support for schemas with arrays
- **YAML Generation**: Real-time YAML preview of array configurations

**Validation System:**
- **Array-Level Validation**: Min/max length, required fields
- **Item-Level Validation**: Type checking, constraint enforcement
- **Property-Level Validation**: Required properties, type constraints
- **Contextual Errors**: Specific error messages with array indices (e.g., `items[2].quantity`)
- **Enum Validation**: Choice validation for enum items and properties

### Current Limitations ❌

**Structural Limitations:**
- **No Deep Nesting**: Objects within objects not supported
- **No Array Nesting**: Arrays within arrays not supported
- **Scalar Properties Only**: Object array properties must be scalar types

**Feature Limitations:**
- **No Cross-Field Validation**: Cannot validate relationships between fields
- **No Calculated Fields**: No automatic field calculations
- **No Conditional Fields**: Fields cannot appear/hide based on other values
- **No Custom Validation**: Cannot define custom validation functions
- **No File Uploads**: File or image field types not supported

**Performance Considerations:**
- **Large Arrays**: Optimized for arrays up to 500-1000 items
- **Complex Objects**: Best performance with < 10 properties per object
- **Validation Speed**: Large arrays may take 1-2 seconds to validate

### Technology Dependencies

**Required Libraries:**
- **pandas >= 2.3.0**: Required for object array editing (st.data_editor)
- **numpy**: Transitive dependency for type normalization
- **streamlit**: Core framework (already required)
- **pydantic**: Validation framework (already required)

**Deployment Notes:**
- pandas must be included in requirements.txt
- No additional configuration required
- Works in all Streamlit deployment environments

### Working with Current Limitations

**For Deep Nesting Needs**:
- Flatten nested structures where possible
- Use multiple top-level fields instead of nested objects
- Consider separate schemas for complex nested data

**For Large Arrays**:
- Consider pagination for arrays > 500 items
- Break large datasets into multiple files
- Use batch processing for bulk operations

**For Complex Validation**:
- Use enum fields for controlled vocabularies
- Implement validation in application logic if needed
- Use patterns for format validation (regex)

**For Performance**:
- Keep object arrays under 500 rows for best performance
- Limit object properties to essential fields (< 10 recommended)
- Use appropriate data types (integer vs number) for efficiency

## Real-World Examples

Based on the current JSON extraction capabilities and array field support, here are comprehensive practical schema examples:

### Example 1: Insurance Policy Document with Serial Numbers

**Use Case**: Insurance policies covering multiple pieces of equipment, each with a serial number.

```yaml
title: "Insurance Policy Schema"
description: "For insurance documents with equipment serial numbers"

fields:
  supplier_name:
    type: "string"
    label: "Insurance Company"
    required: true
    max_length: 200
    help: "Name of the insurance provider"

  client_name:
    type: "string"
    label: "Client Name"
    required: true
    max_length: 200
    help: "Name of the insured party"

  client_address:
    type: "string"
    label: "Client Address"
    required: false
    max_length: 500
    help: "Business address of the client"

  policy_number:
    type: "string"
    label: "Policy Number"
    required: true
    pattern: "^[A-Z]{2}[0-9]{10}$"
    help: "Unique policy identifier (e.g., DF1234567890)"

  invoice_amount:
    type: "number"
    label: "Premium Amount"
    required: true
    min_value: 0.01
    step: 0.01
    help: "Total premium amount"

  currency:
    type: "enum"
    label: "Currency"
    required: false
    choices: ["USD", "EUR", "GBP", "SGD", "AUD"]
    default: "SGD"
    help: "Premium currency"

  insurance_start_date:
    type: "date"
    label: "Policy Start Date"
    required: true
    help: "Policy effective start date"

  insurance_end_date:
    type: "date"
    label: "Policy End Date"
    required: true
    help: "Policy expiration date"

  invoice_type:
    type: "enum"
    label: "Invoice Type"
    required: false
    choices: ["debit", "credit"]
    default: "debit"
    help: "Type of invoice transaction"

  serial_numbers:
    type: "array"
    label: "Equipment Serial Numbers"
    required: false
    help: "List of covered equipment serial numbers"
    items:
      type: "string"
      min_length: 5
      max_length: 50
      help: "Serial number of covered equipment"
```

**Sample JSON Data:**
```json
{
  "supplier_name": "China Taiping Insurance (Singapore) Pte. Ltd.",
  "client_name": "ABC Manufacturing Ltd",
  "policy_number": "DF1234567890",
  "invoice_amount": 490.50,
  "currency": "SGD",
  "insurance_start_date": "2024-01-01",
  "insurance_end_date": "2024-12-31",
  "serial_numbers": [
    "SN123456",
    "SN789012",
    "SN345678"
  ]
}
```

### Example 2: Purchase Order with Line Items

**Use Case**: Purchase orders with multiple line items, each having description, quantity, and pricing.

```yaml
title: "Purchase Order Schema"
description: "For purchase orders with detailed line items"

fields:
  supplier_name:
    type: "string"
    label: "Supplier Name"
    required: true
    max_length: 200
    help: "Name of the supplier company"

  purchase_order_number:
    type: "string"
    label: "PO Number"
    required: true
    pattern: "^PO-[0-9]{6}$"
    help: "Purchase order number (e.g., PO-123456)"

  order_date:
    type: "date"
    label: "Order Date"
    required: true
    help: "Date the order was placed"

  invoice_amount:
    type: "number"
    label: "Total Amount"
    required: true
    min_value: 0.01
    step: 0.01
    help: "Total order amount"

  currency:
    type: "enum"
    label: "Currency"
    required: false
    choices: ["USD", "EUR", "GBP", "SGD", "AUD"]
    default: "SGD"

  project_number:
    type: "string"
    label: "Project Number"
    required: false
    max_length: 50
    help: "Associated project identifier"

  delivery_address:
    type: "string"
    label: "Delivery Address"
    required: false
    max_length: 500
    help: "Shipping address for this order"

  items:
    type: "array"
    label: "Line Items"
    required: false
    help: "List of items in this order"
    items:
      type: "object"
      properties:
        item_code:
          type: "string"
          label: "Item Code"
          required: false
          max_length: 50
          help: "SKU or item code"
        description:
          type: "string"
          label: "Item Description"
          required: true
          max_length: 500
          help: "Detailed description of the item"
        quantity:
          type: "integer"
          label: "Quantity"
          required: true
          min_value: 1
          help: "Number of units ordered"
        unit:
          type: "enum"
          label: "Unit"
          required: false
          choices: ["PCS", "BOX", "KG", "M", "L", "SET"]
          default: "PCS"
          help: "Unit of measurement"
        unit_price:
          type: "number"
          label: "Unit Price"
          required: true
          min_value: 0.01
          step: 0.01
          help: "Price per unit"
        total_price:
          type: "number"
          label: "Total Price"
          required: true
          min_value: 0.01
          step: 0.01
          help: "Total price for this line item"
```

**Sample JSON Data:**
```json
{
  "supplier_name": "ITL Hardware & Engineering Supplies Pte Ltd",
  "purchase_order_number": "PO-123456",
  "order_date": "2024-01-15",
  "invoice_amount": 862.33,
  "currency": "SGD",
  "project_number": "PROJ-2024-001",
  "items": [
    {
      "item_code": "HC-9-22",
      "description": "#23-13 HOSE CLIP 100% S/S 9-22MM (190)",
      "quantity": 50,
      "unit": "PCS",
      "unit_price": 2.50,
      "total_price": 125.00
    },
    {
      "item_code": "HC-8-14",
      "description": "#23-27 HOSE CLIP 100% S/S 8-14MM (188)",
      "quantity": 5,
      "unit": "PCS",
      "unit_price": 3.20,
      "total_price": 16.00
    }
  ]
}
```

### Example 3: Invoice with Multiple Payment Methods

**Use Case**: Invoices that accept multiple payment methods, each with different details.

```yaml
title: "Invoice Schema with Payment Methods"
description: "For invoices with multiple payment options"

fields:
  invoice_number:
    type: "string"
    label: "Invoice Number"
    required: true
    pattern: "^INV-[0-9]{6}$"

  invoice_date:
    type: "date"
    label: "Invoice Date"
    required: true

  customer_name:
    type: "string"
    label: "Customer Name"
    required: true
    max_length: 200

  total_amount:
    type: "number"
    label: "Total Amount"
    required: true
    min_value: 0.01
    step: 0.01

  payment_methods:
    type: "array"
    label: "Accepted Payment Methods"
    help: "List of payment methods accepted for this invoice"
    items:
      type: "object"
      properties:
        method_type:
          type: "enum"
          label: "Payment Method"
          required: true
          choices: ["bank_transfer", "credit_card", "check", "cash"]
          help: "Type of payment method"
        account_number:
          type: "string"
          label: "Account Number"
          required: false
          max_length: 50
          help: "Bank account or card number (last 4 digits)"
        bank_name:
          type: "string"
          label: "Bank Name"
          required: false
          max_length: 100
          help: "Name of the bank"
        is_preferred:
          type: "boolean"
          label: "Preferred Method"
          required: false
          default: false
          help: "Mark as preferred payment method"
```

### Example 4: Product Catalog with Tags

**Use Case**: Product catalog where each product has multiple tags for categorization.

```yaml
title: "Product Catalog Schema"
description: "For product listings with tags and specifications"

fields:
  product_id:
    type: "string"
    label: "Product ID"
    required: true
    pattern: "^PROD-[0-9]{6}$"

  product_name:
    type: "string"
    label: "Product Name"
    required: true
    max_length: 200

  description:
    type: "string"
    label: "Description"
    required: false
    max_length: 1000

  price:
    type: "number"
    label: "Price"
    required: true
    min_value: 0.01
    step: 0.01

  in_stock:
    type: "boolean"
    label: "In Stock"
    required: false
    default: true

  tags:
    type: "array"
    label: "Product Tags"
    help: "Categorization tags for this product"
    items:
      type: "enum"
      choices: ["electronics", "hardware", "software", "accessories", "tools", "supplies"]
      help: "Product category tags"

  specifications:
    type: "array"
    label: "Specifications"
    help: "Technical specifications"
    items:
      type: "object"
      properties:
        spec_name:
          type: "string"
          label: "Specification Name"
          required: true
          max_length: 100
          help: "Name of the specification (e.g., 'Weight', 'Dimensions')"
        spec_value:
          type: "string"
          label: "Value"
          required: true
          max_length: 200
          help: "Specification value"
        unit:
          type: "string"
          label: "Unit"
          required: false
          max_length: 20
          help: "Unit of measurement (e.g., 'kg', 'cm')"
```

### Example 5: Employee Training Records

**Use Case**: Tracking employee training sessions with completion dates and scores.

```yaml
title: "Employee Training Schema"
description: "For tracking employee training and certifications"

fields:
  employee_id:
    type: "string"
    label: "Employee ID"
    required: true
    pattern: "^EMP-[0-9]{5}$"

  employee_name:
    type: "string"
    label: "Employee Name"
    required: true
    max_length: 200

  department:
    type: "enum"
    label: "Department"
    required: true
    choices: ["Engineering", "Sales", "Operations", "HR", "Finance"]

  training_sessions:
    type: "array"
    label: "Training Sessions"
    help: "List of completed training sessions"
    items:
      type: "object"
      properties:
        course_name:
          type: "string"
          label: "Course Name"
          required: true
          max_length: 200
        completion_date:
          type: "date"
          label: "Completion Date"
          required: true
        score:
          type: "integer"
          label: "Score (%)"
          required: false
          min_value: 0
          max_value: 100
        passed:
          type: "boolean"
          label: "Passed"
          required: true
          default: false
        instructor:
          type: "string"
          label: "Instructor"
          required: false
          max_length: 100

  certifications:
    type: "array"
    label: "Certifications"
    help: "Professional certifications held"
    items:
      type: "string"
      min_length: 2
      max_length: 100
      help: "Certification name or code"
```

### Example 6: Contract with Milestones

**Use Case**: Project contracts with multiple milestones and deliverables.

```yaml
title: "Project Contract Schema"
description: "For project contracts with milestones"

fields:
  contract_number:
    type: "string"
    label: "Contract Number"
    required: true
    pattern: "^CTR-[0-9]{6}$"

  client_name:
    type: "string"
    label: "Client Name"
    required: true
    max_length: 200

  contract_date:
    type: "date"
    label: "Contract Date"
    required: true

  total_value:
    type: "number"
    label: "Total Contract Value"
    required: true
    min_value: 0.01
    step: 0.01

  status:
    type: "enum"
    label: "Contract Status"
    required: true
    choices: ["draft", "active", "completed", "cancelled"]
    default: "draft"

  milestones:
    type: "array"
    label: "Project Milestones"
    help: "Key milestones and deliverables"
    items:
      type: "object"
      properties:
        milestone_name:
          type: "string"
          label: "Milestone Name"
          required: true
          max_length: 200
        due_date:
          type: "date"
          label: "Due Date"
          required: true
        payment_amount:
          type: "number"
          label: "Payment Amount"
          required: true
          min_value: 0.01
          step: 0.01
        completed:
          type: "boolean"
          label: "Completed"
          required: false
          default: false
        completion_date:
          type: "date"
          label: "Completion Date"
          required: false
        notes:
          type: "string"
          label: "Notes"
          required: false
          max_length: 500
```

These examples demonstrate the full capabilities of array field support in real-world scenarios, showing both scalar arrays (tags, certifications, serial numbers) and object arrays (line items, milestones, specifications) with appropriate constraints and validation rules.

## Migration Guide

### Migrating to Array Field Support

If you have existing schemas that were created before array field support, follow this guide to migrate them.

### Pre-Migration Checklist

Before migrating:
- [ ] Backup your existing schema files
- [ ] Review your JSON data to identify array fields
- [ ] Test migration on a copy of your schema first
- [ ] Verify you have the latest version of the application

### Migration Scenarios

#### Scenario 1: Manual YAML Arrays → Schema Editor

**Situation**: You manually created array fields in YAML and want to manage them in Schema Editor.

**Steps:**
1. **Backup**: Copy your schema file to a safe location
2. **Import**: Open Schema Editor and import your schema
3. **Verify**: Check that all array fields imported correctly
4. **Edit**: Use ArrayFieldManager to modify array configurations
5. **Test**: Export and test with sample JSON data

**Example:**
```yaml
# Original manual YAML
serial_numbers:
  type: array
  items:
    type: string
```

After import, you can:
- Add constraints (min_length, max_length, pattern)
- Change item type
- Add help text
- Configure validation rules

#### Scenario 2: String Fields → Scalar Arrays

**Situation**: You have fields that should be arrays but are currently strings.

**Before:**
```yaml
serial_number:
  type: "string"
  label: "Serial Number"
  help: "Enter serial number"
```

**After:**
```yaml
serial_numbers:
  type: "array"
  label: "Serial Numbers"
  help: "List of serial numbers"
  items:
    type: "string"
    min_length: 5
    max_length: 20
    pattern: "^SN[0-9]{4}$"
```

**Migration Steps:**
1. Create new array field with plural name
2. Set item type to match original field type
3. Copy constraints from original field to items config
4. Update JSON data to use array format: `"SN1234"` → `["SN1234"]`
5. Test with updated JSON data
6. Remove old string field once verified

#### Scenario 3: Multiple Fields → Object Array

**Situation**: You have multiple related fields that should be an object array.

**Before:**
```yaml
item_description_1:
  type: "string"
  label: "Item 1 Description"
item_quantity_1:
  type: "integer"
  label: "Item 1 Quantity"
item_description_2:
  type: "string"
  label: "Item 2 Description"
item_quantity_2:
  type: "integer"
  label: "Item 2 Quantity"
```

**After:**
```yaml
items:
  type: "array"
  label: "Items"
  help: "List of ordered items"
  items:
    type: "object"
    properties:
      description:
        type: "string"
        label: "Description"
        required: true
        max_length: 200
      quantity:
        type: "integer"
        label: "Quantity"
        required: true
        min_value: 1
```

**Migration Steps:**
1. Create new object array field
2. Add properties matching your original fields
3. Copy constraints from original fields to properties
4. Update JSON data structure:
```json
// Before
{
  "item_description_1": "Widget A",
  "item_quantity_1": 10,
  "item_description_2": "Widget B",
  "item_quantity_2": 5
}

// After
{
  "items": [
    {"description": "Widget A", "quantity": 10},
    {"description": "Widget B", "quantity": 5}
  ]
}
```
5. Test with updated JSON data
6. Remove old fields once verified

#### Scenario 4: JSON Text Area → Structured Array Editor

**Situation**: Users are editing arrays as raw JSON text and you want structured editing.

**Current State**: Array fields exist but use generic JSON text area
**Goal**: Enable user-friendly array editors

**Steps:**
1. **Verify Schema**: Ensure array fields have proper `items` configuration
2. **Add Constraints**: Use Schema Editor to add validation rules
3. **Test Editors**: Verify scalar/object array editors appear correctly
4. **Train Users**: Show users the new editing interface
5. **Monitor**: Check for validation errors or usability issues

**No JSON Data Changes Required** - This is purely a UI improvement.

### Data Migration Strategies

#### Strategy 1: Gradual Migration

**Best for**: Large datasets, production systems

**Process:**
1. Create new array fields alongside old fields
2. Update application to write to both old and new fields
3. Migrate existing data in batches
4. Verify data integrity after each batch
5. Switch application to read from new fields
6. Remove old fields after verification period

#### Strategy 2: One-Time Migration

**Best for**: Small datasets, development environments

**Process:**
1. Create migration script to transform JSON data
2. Backup all JSON files
3. Run migration script
4. Update schema to use array fields
5. Test with migrated data
6. Deploy updated schema

#### Strategy 3: Hybrid Approach

**Best for**: Mixed environments, phased rollout

**Process:**
1. Support both old and new formats in application
2. Migrate schemas first
3. Migrate data gradually as files are edited
4. Track migration progress
5. Remove old format support after full migration

### Migration Script Example

**Python script to migrate JSON data:**

```python
import json
import os
from pathlib import Path

def migrate_to_array(json_file, field_name, new_field_name=None):
    """
    Migrate a single-value field to an array field.
    
    Args:
        json_file: Path to JSON file
        field_name: Name of field to migrate
        new_field_name: New field name (defaults to field_name + 's')
    """
    new_field_name = new_field_name or f"{field_name}s"
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Migrate single value to array
    if field_name in data:
        value = data[field_name]
        data[new_field_name] = [value] if value else []
        del data[field_name]
    
    # Backup original
    backup_file = f"{json_file}.backup"
    os.rename(json_file, backup_file)
    
    # Write migrated data
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Migrated {json_file}: {field_name} → {new_field_name}")

def migrate_to_object_array(json_file, field_mapping, new_field_name):
    """
    Migrate multiple fields to an object array.
    
    Args:
        json_file: Path to JSON file
        field_mapping: Dict mapping old field names to new property names
        new_field_name: Name of new array field
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Extract values and create object array
    objects = []
    # Determine number of objects (assumes numbered fields like field_1, field_2)
    max_index = 0
    for old_field in field_mapping.keys():
        # Extract index from field name (e.g., "item_description_1" → 1)
        parts = old_field.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            max_index = max(max_index, int(parts[1]))
    
    # Create objects
    for i in range(1, max_index + 1):
        obj = {}
        for old_field, new_prop in field_mapping.items():
            field_with_index = f"{old_field}_{i}"
            if field_with_index in data:
                obj[new_prop] = data[field_with_index]
                del data[field_with_index]
        if obj:
            objects.append(obj)
    
    data[new_field_name] = objects
    
    # Backup and write
    backup_file = f"{json_file}.backup"
    os.rename(json_file, backup_file)
    
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Migrated {json_file}: {len(objects)} objects → {new_field_name}")

# Example usage
if __name__ == "__main__":
    # Migrate single field to array
    migrate_to_array("invoice_001.json", "serial_number", "serial_numbers")
    
    # Migrate multiple fields to object array
    field_mapping = {
        "item_description": "description",
        "item_quantity": "quantity",
        "item_price": "unit_price"
    }
    migrate_to_object_array("invoice_001.json", field_mapping, "items")
```

### Post-Migration Validation

After migration, verify:

**Schema Validation:**
- [ ] All array fields have proper `items` configuration
- [ ] Object arrays have all required properties defined
- [ ] Constraints are appropriate for your data
- [ ] Enum choices are complete

**Data Validation:**
- [ ] All JSON files load without errors
- [ ] Array data is in correct format
- [ ] No data loss during migration
- [ ] Validation passes for all migrated fields

**UI Validation:**
- [ ] Scalar array editors appear correctly
- [ ] Object array tables display all columns
- [ ] Add/remove operations work
- [ ] Validation errors are clear and helpful

**Testing Checklist:**
- [ ] Test with sample data before production
- [ ] Verify edit queue displays arrays correctly
- [ ] Test add/remove operations
- [ ] Test validation with invalid data
- [ ] Test submission and saving
- [ ] Verify audit logs capture array changes

### Rollback Plan

If migration issues occur:

1. **Stop Processing**: Pause any automated migration
2. **Restore Backups**: Use backup files to restore original data
3. **Revert Schema**: Switch back to old schema version
4. **Investigate**: Identify root cause of issues
5. **Fix and Retry**: Address issues and retry migration

**Backup Strategy:**
- Keep original JSON files in separate directory
- Keep original schema files with version numbers
- Document migration steps for reproducibility
- Test rollback procedure before production migration

### Common Migration Patterns

**Pattern 1: Simple to Array**
```yaml
# Before: Single value
serial_number:
  type: "string"
  label: "Serial Number"

# After: Multiple values
serial_numbers:
  type: "array"
  label: "Serial Numbers"
  items:
    type: "string"
```

**Pattern 2: Flat to Structured**
```yaml
# Before: Separate fields
item_description_1:
  type: "string"
item_quantity_1:
  type: "integer"

# After: Array of objects
items:
  type: "array"
  label: "Items"
  items:
    type: "object"
    properties:
      description:
        type: "string"
        label: "Description"
      quantity:
        type: "integer"
        label: "Quantity"
```

**Pattern 3: Adding Constraints**
```yaml
# Before: Basic array
tags:
  type: "array"
  items:
    type: "string"

# After: With constraints
tags:
  type: "array"
  label: "Tags"
  help: "Product tags"
  items:
    type: "string"
    min_length: 2
    max_length: 20
    pattern: "^[a-z0-9-]+$"
```

### Getting Help

If you encounter issues during migration:

1. **Check Troubleshooting Section**: Review array-specific troubleshooting above
2. **Validate YAML**: Use online YAML validator to check syntax
3. **Test with Sample**: Create small test schema and data to isolate issues
4. **Check Logs**: Review application logs for detailed error messages
5. **Backup First**: Always backup before making changes

This guide reflects the current implementation status and should help you create schemas that work with your existing JSON extraction system.
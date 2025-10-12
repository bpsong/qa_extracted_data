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

### 8. Array Fields ✅ CORE SUPPORT / ❌ SCHEMA EDITOR

**Type**: `array`
**Widget**: JSON editor or specialized array input

**Implementation Status:**
- ✅ **Core System**: Full support for arrays in JSON processing, validation, and form generation
- ❌ **Schema Editor**: Visual schema editor does not support creating/editing array fields yet

The system currently supports two types of arrays:

#### 8a. Array of Scalar Values ✅ IMPLEMENTED

For arrays containing simple values like strings, numbers, etc.

```yaml
serial_numbers:
  type: "array"
  label: "Serial Numbers"
  help: "List of serial numbers"
  items:
    type: "string"
    # Scalar constraints apply to each item
```

**Example JSON data**: `["SerialNo1", "SerialNo2", "SerialNo3"]`

#### 8b. Array of Objects (One Level Deep) ✅ CORE SUPPORT / ❌ SCHEMA EDITOR

For arrays containing objects with scalar fields only.

**Implementation Status:**
- ✅ **Core System**: Full support for arrays of objects in JSON processing, validation, and form generation
- ❌ **Schema Editor**: Visual schema editor does not support creating/editing array of objects yet

```yaml
items:
  type: "array"
  label: "Line Items"
  help: "Invoice line items"
  items:
    type: "object"
    properties:
      description:
        type: "string"
        label: "Description"
        required: true
      quantity:
        type: "string"  # Note: Currently extracted as strings
        label: "Quantity"
        required: true
```

**Example JSON data**:
```json
[
  {
    "Description": "#23-13 HOSE CLIP 100% S/S 9-22MM (190)",
    "Quantity": "50 PCS"
  },
  {
    "Description": "#23-27 HOSE CLIP 100% S/S 8-14MM (188)", 
    "Quantity": "5 PCS"
  }
]
```

**UI Rendering**: Arrays of objects are rendered using Streamlit's `st.data_editor` which provides:
- **✅ Add/Remove Objects**: Users can dynamically add new rows or delete existing rows
- **✅ Edit Scalar Fields**: Users can edit text, number, and boolean fields within each object
- **✅ Type-Specific Editing**: 
  - String fields: Text input with character limits
  - Number fields: Number input with min/max validation and step controls
  - Boolean fields: Checkbox controls
- **✅ Table Interface**: Spreadsheet-like editing with columns for each object property
- **✅ Real-time Validation**: Field constraints are enforced during editing
- **✅ Dynamic Rows**: `num_rows="dynamic"` enables full add/remove functionality

**Current Limitations**:
- Object arrays are limited to one level of nesting
- Nested objects within array objects are not supported
- Arrays of arrays are not supported
- **Schema Editor UI cannot create or edit array fields** (must be created manually in YAML)

**Schema Editor Behavior**:
- When importing schemas with arrays, the editor converts them to `string` type
- Shows warning: "Field type 'array' is not yet supported in the editor"
- Array fields must be added manually to YAML files

**Constraints**:
- `items`: Definition of array item structure (required)
- For scalar arrays: `items.type` must be a scalar type (string, number, integer, boolean, date)
- For object arrays: `items.type: "object"` with `properties` containing only scalar fields

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

## Array Editing Capabilities

### Arrays of Objects - Full Interactive Editing ✅

When users encounter an array of objects in the JSON QA interface, they get a powerful table editor:

**✅ What Users Can Do:**
- **Add New Objects**: Click to add new rows to the array
- **Remove Objects**: Delete unwanted rows from the array  
- **Edit Field Values**: Click into any cell to edit the value
- **Type-Safe Editing**: Each column respects its data type (text, number, boolean)
- **Validation**: Real-time validation based on schema constraints (required, min/max, etc.)

**Example User Workflow:**
1. User sees a table with existing line items
2. User clicks "Add row" to add a new line item
3. User fills in Description: "New Widget", Quantity: 5, Unit Price: 12.50
4. User can edit existing rows by clicking into cells
5. User can delete rows using the row controls
6. All changes are validated against the schema before submission

**Technical Implementation:**
- Uses `st.data_editor` with `num_rows="dynamic"`
- Column types configured based on schema field types
- Returns updated array as list of dictionaries
- Integrates with form validation system

### Arrays of Scalars - JSON Text Editing ⚠️

Arrays of scalar values use a simpler JSON text area interface:

**⚠️ What Users Must Do:**
- Edit the array as raw JSON: `["item1", "item2", "item3"]`
- Maintain proper JSON syntax (quotes, brackets, commas)
- Add/remove items by editing the JSON text
- No visual add/remove buttons or individual item editors

**Example User Workflow:**
1. User sees a text area with: `["SerialNo1", "SerialNo2"]`
2. User edits to: `["SerialNo1", "SerialNo2", "SerialNo3", "SerialNo4"]`
3. System validates JSON format and individual item constraints
4. Invalid JSON shows error message

This demonstrates that arrays of objects are fully functional in the core system.

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

### Debugging Tips

1. **Start Simple**: Begin with basic string/number fields, then add complexity
2. **Test Incrementally**: Add one field at a time and test
3. **Use Examples**: Copy from working schemas and modify
4. **Check Logs**: Application logs show detailed validation errors
5. **Validate YAML**: Use online YAML validators to check syntax

### Schema Validation Checklist

Before deploying a schema, verify:

**Basic Requirements**:
- [ ] YAML syntax is valid
- [ ] All fields have `type` and `label` properties
- [ ] Field types are from the supported list (string, number, integer, boolean, date, enum, array)
- [ ] Schema has title and description

**Field-Specific**:
- [ ] Enum fields have `choices` arrays
- [ ] Array fields have `items` definitions (must be created manually in YAML)
- [ ] Array items are either scalar types or objects with scalar properties only
- [ ] Object fields (in arrays) have `properties` definitions (must be created manually in YAML)
- [ ] No nested objects within objects
- [ ] No arrays within arrays

**Best Practices**:
- [ ] Help text is clear and helpful
- [ ] Field names use snake_case or match your JSON data exactly
- [ ] Required fields are marked appropriately
- [ ] Field labels are user-friendly

## Schema Editor vs Core System Support

### Schema Editor UI Limitations ⚠️

The **Schema Editor** (visual YAML editor in the webapp) currently supports only basic field types:

**✅ Supported in Schema Editor:**
- string, number, integer, boolean, enum, date, datetime
- Basic field properties (label, required, help, min/max values, choices)

**❌ Not Supported in Schema Editor:**
- Array fields (scalar arrays like `["item1", "item2"]`)
- Array of objects (like line items with multiple fields)
- Object fields (nested structures)
- Advanced validation (patterns, custom rules)
- Complex field properties

**What happens with unsupported fields:**
- When importing schemas with arrays/objects, they get converted to `string` type
- Editor shows: "Field type 'array' editing will be available in a future phase"
- Original array/object configuration is lost in the editor

### Workaround for Array Fields

**Option 1: Manual YAML Editing**
1. Create basic fields using Schema Editor
2. Export or save the schema
3. Manually edit the YAML file to add array fields
4. Use the complete schema in your JSON QA workflow

**Option 2: Hybrid Approach**
1. Use Schema Editor for simple fields
2. Keep a separate "master" YAML file with arrays
3. Copy simple fields from editor to master file as needed

**Example Manual Array Additions:**

*Array of Scalars:*
```yaml
# After using Schema Editor, manually add:
fields:
  "Serial Numbers":
    type: array
    label: "Serial Numbers"
    required: false
    help: "List of equipment serial numbers"
    items:
      type: string
```

*Array of Objects:*
```yaml
# After using Schema Editor, manually add:
fields:
  "Line Items":
    type: array
    label: "Line Items"
    required: false
    help: "Invoice line items"
    items:
      type: object
      properties:
        "Description":
          type: string
          label: "Item Description"
          required: true
        "Quantity":
          type: number
          label: "Quantity"
          required: true
          min_value: 0
        "Unit Price":
          type: number
          label: "Unit Price"
          required: true
          min_value: 0
```

## Implementation Status and Limitations

### Currently Supported ✅

**Core System (JSON Processing & Validation):**
- **Scalar Fields**: string, number, integer, boolean, date, enum
- **Array of Scalars**: Arrays containing simple values like `["item1", "item2"]`
- **Array of Objects**: Arrays containing objects with scalar fields only (one level deep)
- **Basic Validation**: Required fields, basic constraints
- **Form Generation**: Automatic UI generation for supported field types

**Schema Editor UI:**
- **Scalar Fields Only**: string, number, integer, boolean, enum, date, datetime
- **❌ Arrays (any type)**: Not supported in visual editor (must edit YAML manually)
- **❌ Objects (any type)**: Not supported in visual editor (must edit YAML manually)
- **❌ Array of Objects**: Not supported in visual editor (must edit YAML manually)

### Planned Features ⚠️

**Core System:**
- **DateTime Fields**: Date and time picker widgets
- **Advanced Validation**: Pattern matching, min/max length, custom validation
- **Calculated Fields**: Read-only fields with automatic calculation
- **Conditional Fields**: Fields that appear based on other field values
- **Custom Validation Messages**: User-defined error messages

**Schema Editor UI:**
- **Array Field Support**: Visual creation and editing of array fields
- **Object Field Support**: Visual creation and editing of nested objects
- **Advanced Field Properties**: Pattern validation, constraints, etc.

### Not Supported ❌
- **Deep Nesting**: Objects within objects, arrays within arrays
- **Complex Validation**: Cross-field validation, custom validation functions
- **Dynamic Schemas**: Schema modification at runtime
- **File Uploads**: File or image field types

### Working with Current Limitations

**For Schema Editor Users**:
- Use the visual editor for basic fields (string, number, enum, etc.)
- Manually edit YAML files for array and object fields
- Keep a backup of manually-edited schemas before importing to editor

**For Complex Data Structures**: 
- Use flat structures where possible in Schema Editor
- Break complex objects into separate top-level fields
- Use arrays of objects for repeating data (like line items) - but create manually

**For Validation**:
- Keep validation rules simple in Schema Editor
- Use enum fields for controlled vocabularies
- Add advanced validation manually in YAML

**For Arrays**:
- Array of scalars: `["value1", "value2", "value3"]` (manual YAML only)
- Array of objects: `[{"field1": "value1", "field2": "value2"}]` (manual YAML only)
- Objects in arrays can only contain scalar fields
- **UI Rendering**: Arrays of objects use Streamlit's `st.data_editor` for table-like editing with full add/remove/edit capabilities
- **UI Rendering**: Arrays of scalars use JSON text area for editing (manual JSON format required)

## Real-World Examples

Based on the current JSON extraction capabilities, here are practical schema examples:

### Example 1: Insurance Policy Document
```yaml
title: "Insurance Policy Schema"
description: "For insurance documents with serial numbers"

fields:
  supplier_name:
    type: "string"
    label: "Insurance Company"
    required: true

  client_name:
    type: "string"
    label: "Client Name"
    required: true

  invoice_amount:
    type: "number"
    label: "Premium Amount"
    required: true

  insurance_start_date:
    type: "date"
    label: "Policy Start Date"
    required: true

  insurance_end_date:
    type: "date"
    label: "Policy End Date"
    required: true

  policy_number:
    type: "string"
    label: "Policy Number"
    required: true

  serial_numbers:
    type: "array"
    label: "Equipment Serial Numbers"
    help: "List of covered equipment"
    items:
      type: "string"
```

### Example 2: Purchase Order with Line Items
```yaml
title: "Purchase Order Schema"
description: "For purchase orders with item details"

fields:
  supplier_name:
    type: "string"
    label: "Supplier Name"
    required: true

  purchase_order_number:
    type: "string"
    label: "PO Number"
    required: true

  invoice_amount:
    type: "number"
    label: "Total Amount"
    required: true

  project_number:
    type: "string"
    label: "Project Number"
    required: false

  items:
    type: "array"
    label: "Order Items"
    help: "List of items in this order"
    items:
      type: "object"
      properties:
        description:
          type: "string"
          label: "Item Description"
          required: true
        quantity:
          type: "string"
          label: "Quantity"
          required: true
          help: "Quantity with units (e.g., '50 PCS')"
```

## Migration Guide

### Updating Existing Schemas

When updating schemas:

1. **Test with Sample Data**: Use your actual JSON files to test schema changes
2. **Start Simple**: Begin with scalar fields, then add arrays
3. **Match Your Data**: Ensure field names match your JSON structure exactly
4. **Incremental Changes**: Add one field type at a time and test

### Common Migration Patterns

**From Simple to Array Fields**:
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

**From Flat to Structured**:
```yaml
# Before: Separate fields
item_description_1:
  type: "string"
item_quantity_1:
  type: "string"

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
        type: "string"
        label: "Quantity"
```

This guide reflects the current implementation status and should help you create schemas that work with your existing JSON extraction system.
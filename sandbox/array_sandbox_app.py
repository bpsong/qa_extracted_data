"""
Array Field Support Sandbox Application

This standalone Streamlit application provides a testing environment for array field functionality
before integration into the main codebase. It includes test scenarios for both scalar arrays
and object arrays with comprehensive validation and user feedback collection.
"""

import streamlit as st
import yaml
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import copy

# Configure Streamlit page
st.set_page_config(
    page_title="Array Field Support Sandbox",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_test_schemas() -> Dict[str, Dict[str, Any]]:
    """Load predefined test schemas for sandbox testing"""
    return {
        "insurance_document": {
            "title": "Insurance Document Schema",
            "description": "Schema for insurance documents with diverse array types",
            "fields": {
                "supplier_name": {
                    "type": "string",
                    "label": "Supplier Name",
                    "required": True,
                    "help": "Name of the insurance supplier"
                },
                "client_name": {
                    "type": "string", 
                    "label": "Client Name",
                    "required": True,
                    "help": "Name of the client"
                },
                "policy_number": {
                    "type": "string",
                    "label": "Policy Number", 
                    "required": True,
                    "help": "Insurance policy number"
                },
                "serial_numbers": {
                    "type": "array",
                    "label": "Serial Numbers (String Array)",
                    "required": False,
                    "help": "List of equipment serial numbers",
                    "items": {
                        "type": "string",
                        "min_length": 3,
                        "max_length": 20,
                        "pattern": "^[A-Z0-9]+$"
                    }
                },
                "coverage_amounts": {
                    "type": "array",
                    "label": "Coverage Amounts (Number Array)",
                    "required": False,
                    "help": "List of coverage amounts for different items",
                    "items": {
                        "type": "number",
                        "min_value": 0,
                        "max_value": 1000000,
                        "step": 0.01
                    }
                },
                "inspection_years": {
                    "type": "array",
                    "label": "Inspection Years (Integer Array)",
                    "required": False,
                    "help": "Years when inspections are required",
                    "items": {
                        "type": "integer",
                        "min_value": 2020,
                        "max_value": 2030,
                        "step": 1
                    }
                },
                "coverage_active": {
                    "type": "array",
                    "label": "Coverage Active Status (Boolean Array)",
                    "required": False,
                    "help": "Active status for each coverage type",
                    "items": {
                        "type": "boolean"
                    }
                },
                "renewal_dates": {
                    "type": "array",
                    "label": "Renewal Dates (Date Array)",
                    "required": False,
                    "help": "Important renewal dates to track",
                    "items": {
                        "type": "date"
                    }
                },
                "invoice_amount": {
                    "type": "number",
                    "label": "Invoice Amount",
                    "required": True,
                    "help": "Total invoice amount",
                    "min_value": 0
                },
                "tags": {
                    "type": "array",
                    "label": "Tags (String Array)",
                    "required": False,
                    "help": "Categorization tags",
                    "items": {
                        "type": "string",
                        "min_length": 1,
                        "max_length": 50
                    }
                }
            }
        },
        "purchase_order": {
            "title": "Purchase Order Schema", 
            "description": "Schema for purchase orders with line items",
            "fields": {
                "po_number": {
                    "type": "string",
                    "label": "PO Number",
                    "required": True,
                    "help": "Purchase order number"
                },
                "vendor_name": {
                    "type": "string",
                    "label": "Vendor Name", 
                    "required": True,
                    "help": "Name of the vendor"
                },
                "order_date": {
                    "type": "date",
                    "label": "Order Date",
                    "required": True,
                    "help": "Date the order was placed"
                },
                "line_items": {
                    "type": "array",
                    "label": "Line Items",
                    "required": True,
                    "help": "List of items being purchased",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_code": {
                                "type": "string",
                                "label": "Item Code",
                                "required": True,
                                "help": "Product item code"
                            },
                            "description": {
                                "type": "string", 
                                "label": "Description",
                                "required": True,
                                "help": "Item description"
                            },
                            "quantity": {
                                "type": "integer",
                                "label": "Quantity",
                                "required": True,
                                "help": "Number of items",
                                "min_value": 1
                            },
                            "unit_price": {
                                "type": "number",
                                "label": "Unit Price",
                                "required": True,
                                "help": "Price per unit",
                                "min_value": 0
                            },
                            "total_price": {
                                "type": "number",
                                "label": "Total Price", 
                                "required": False,
                                "help": "Total price for this line item"
                            }
                        }
                    }
                },
                "total_amount": {
                    "type": "number",
                    "label": "Total Amount",
                    "required": True,
                    "help": "Total purchase order amount",
                    "min_value": 0
                }
            }
        }
    }

def load_test_data() -> Dict[str, Dict[str, Any]]:
    """Load sample test data for each schema"""
    return {
        "insurance_document": {
            "supplier_name": "China Taiping Insurance (Singapore) Pte. Ltd.",
            "client_name": "KIM BOCK CONTRACTOR PTE LTD", 
            "policy_number": "DFIRSNA00046522412",
            "serial_numbers": ["SN001", "SN002", "SN003"],
            "coverage_amounts": [25000.00, 50000.00, 75000.00],
            "inspection_years": [2024, 2025, 2026],
            "coverage_active": [True, True, False],
            "renewal_dates": ["2024-12-31", "2025-06-30", "2025-12-31"],
            "invoice_amount": 490.5,
            "tags": ["insurance", "equipment", "annual"]
        },
        "purchase_order": {
            "po_number": "PO-2024-001",
            "vendor_name": "ABC Supplies Ltd",
            "order_date": "2024-01-15",
            "line_items": [
                {
                    "item_code": "ITM001",
                    "description": "Office Chair",
                    "quantity": 5,
                    "unit_price": 150.00,
                    "total_price": 750.00
                },
                {
                    "item_code": "ITM002", 
                    "description": "Desk Lamp",
                    "quantity": 10,
                    "unit_price": 45.00,
                    "total_price": 450.00
                }
            ],
            "total_amount": 1200.00
        }
    }

def main():
    """Main sandbox application interface"""
    st.title("🧪 Array Field Support Sandbox")
    st.markdown("---")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Test Area",
        [
            "Overview",
            "Scalar Array Editor", 
            "Object Array Editor",
            "Schema Editor",
            "Validation Testing",
            "Test Scenarios"
        ]
    )
    
    # Load test data
    test_schemas = load_test_schemas()
    test_data = load_test_data()
    
    if page == "Overview":
        render_overview_page()
    elif page == "Scalar Array Editor":
        render_scalar_array_page(test_schemas, test_data)
    elif page == "Object Array Editor":
        render_object_array_page(test_schemas, test_data)
    elif page == "Schema Editor":
        render_schema_editor_page()
    elif page == "Validation Testing":
        render_validation_page(test_schemas, test_data)
    elif page == "Test Scenarios":
        render_test_scenarios_page(test_schemas, test_data)

def render_overview_page():
    """Render the overview page with sandbox information"""
    st.header("Array Field Support Sandbox Overview")
    
    st.markdown("""
    This sandbox provides a testing environment for array field functionality before integration 
    into the main JSON QA webapp. Use this interface to:
    
    ### 🎯 Test Areas
    
    1. **Scalar Array Editor** - Test editing arrays of simple values (strings, numbers, etc.)
    2. **Object Array Editor** - Test editing arrays of complex objects with multiple properties  
    3. **Schema Editor** - Test creating array field configurations
    4. **Validation Testing** - Test validation rules and error handling
    5. **Test Scenarios** - Run predefined test cases and provide feedback
    
    ### 📋 Test Schemas Available
    
    - **Insurance Document**: Contains diverse scalar arrays:
      - **String arrays**: Serial numbers, tags
      - **Number arrays**: Coverage amounts  
      - **Integer arrays**: Inspection years
      - **Boolean arrays**: Coverage active status
      - **Date arrays**: Renewal dates
    - **Purchase Order**: Contains object arrays for line items with multiple properties
    
    ### 🔍 What to Test
    
    - Add/remove items from arrays
    - Edit individual array items
    - Validation with various constraints
    - Error handling and recovery
    - User experience and interface usability
    
    ### 📝 Feedback Collection
    
    Use the Test Scenarios page to provide structured feedback on functionality and user experience.
    """)
    
    # Display test schemas
    st.subheader("Available Test Schemas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Insurance Document Schema - Diverse Array Types**")
        st.code(yaml.dump({
            "serial_numbers": {
                "type": "array",
                "items": {"type": "string", "pattern": "^[A-Z0-9]+$"}
            },
            "coverage_amounts": {
                "type": "array",
                "items": {"type": "number", "min_value": 0, "max_value": 1000000}
            },
            "inspection_years": {
                "type": "array",
                "items": {"type": "integer", "min_value": 2020, "max_value": 2030}
            },
            "coverage_active": {
                "type": "array",
                "items": {"type": "boolean"}
            },
            "renewal_dates": {
                "type": "array",
                "items": {"type": "date"}
            }
        }), language="yaml")
    
    with col2:
        st.markdown("**Purchase Order Schema**")
        st.code(yaml.dump({
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_code": {"type": "string", "required": True},
                        "quantity": {"type": "integer", "min_value": 1},
                        "unit_price": {"type": "number", "min_value": 0}
                    }
                }
            }
        }), language="yaml")

def render_scalar_array_page(test_schemas: Dict, test_data: Dict):
    """Render scalar array editor testing page"""
    st.header("Scalar Array Editor Testing")
    st.markdown("Test editing arrays of scalar values with add/remove functionality")
    
    # Schema selection
    schema_choice = st.selectbox(
        "Select Test Schema",
        ["insurance_document"],
        format_func=lambda x: test_schemas[x]["title"]
    )
    
    schema = test_schemas[schema_choice]
    data = copy.deepcopy(test_data[schema_choice])
    
    # Initialize session state for array data
    if f"array_data_{schema_choice}" not in st.session_state:
        st.session_state[f"array_data_{schema_choice}"] = copy.deepcopy(data)
    
    current_data = st.session_state[f"array_data_{schema_choice}"]
    
    st.subheader("Original Test Data")
    st.json(data)
    
    st.subheader("Array Field Editors")
    
    # Find array fields in schema
    array_fields = {
        field_name: field_config 
        for field_name, field_config in schema["fields"].items()
        if field_config.get("type") == "array" and field_config.get("items", {}).get("type") != "object"
    }
    
    if not array_fields:
        st.warning("No scalar array fields found in selected schema")
        return
    
    # Render each scalar array field
    for field_name, field_config in array_fields.items():
        st.markdown(f"### {field_config.get('label', field_name)}")
        st.markdown(f"*{field_config.get('help', 'No description available')}*")
        
        # Get current array value
        current_array = current_data.get(field_name, [])
        
        # Render scalar array editor
        updated_array = render_scalar_array_editor(
            field_name, 
            field_config, 
            current_array
        )
        
        # Update session state
        current_data[field_name] = updated_array
        st.session_state[f"array_data_{schema_choice}"] = current_data
    
    st.subheader("Updated Data")
    st.json(current_data)
    
    # Reset button
    if st.button("Reset to Original Data"):
        st.session_state[f"array_data_{schema_choice}"] = copy.deepcopy(data)
        st.rerun()

def render_object_array_page(test_schemas: Dict, test_data: Dict):
    """Render object array editor testing page"""
    st.header("Object Array Editor Testing")
    st.markdown("Test editing arrays of objects using table-style interface")
    
    # Schema selection
    schema_choice = st.selectbox(
        "Select Test Schema",
        ["purchase_order"],
        format_func=lambda x: test_schemas[x]["title"]
    )
    
    schema = test_schemas[schema_choice]
    data = copy.deepcopy(test_data[schema_choice])
    
    # Initialize session state for array data
    if f"object_array_data_{schema_choice}" not in st.session_state:
        st.session_state[f"object_array_data_{schema_choice}"] = copy.deepcopy(data)
    
    current_data = st.session_state[f"object_array_data_{schema_choice}"]
    
    st.subheader("Original Test Data")
    st.json(data)
    
    st.subheader("Object Array Field Editors")
    
    # Find object array fields in schema
    object_array_fields = {
        field_name: field_config 
        for field_name, field_config in schema["fields"].items()
        if (field_config.get("type") == "array" and 
            field_config.get("items", {}).get("type") == "object")
    }
    
    if not object_array_fields:
        st.warning("No object array fields found in selected schema")
        return
    
    # Render each object array field
    for field_name, field_config in object_array_fields.items():
        st.markdown(f"### {field_config.get('label', field_name)}")
        st.markdown(f"*{field_config.get('help', 'No description available')}*")
        
        # Get current array value
        current_array = current_data.get(field_name, [])
        
        # Render object array editor
        updated_array = render_object_array_editor(
            field_name, 
            field_config, 
            current_array
        )
        
        # Update session state
        current_data[field_name] = updated_array
        st.session_state[f"object_array_data_{schema_choice}"] = current_data
    
    st.subheader("Updated Data")
    st.json(current_data)
    
    # Reset button
    if st.button("Reset to Original Data", key="reset_object_data"):
        st.session_state[f"object_array_data_{schema_choice}"] = copy.deepcopy(data)
        st.rerun()

def render_schema_editor_page():
    """Render schema editor testing page"""
    st.header("Schema Editor Testing")
    st.markdown("Test creating and configuring array fields")
    
    # Initialize session state for schema editor
    if "schema_editor_fields" not in st.session_state:
        st.session_state.schema_editor_fields = {}
    
    st.subheader("Create New Array Field")
    
    # Basic field information (outside form for immediate updates)
    col1, col2 = st.columns(2)
    
    with col1:
        field_name = st.text_input("Field Name", placeholder="e.g., serial_numbers", key="schema_field_name")
        field_label = st.text_input("Field Label", placeholder="e.g., Serial Numbers", key="schema_field_label")
        field_help = st.text_area("Help Text", placeholder="Description of this field", key="schema_field_help")
        field_required = st.checkbox("Required Field", key="schema_field_required")
    
    with col2:
        array_type = st.selectbox(
            "Array Type",
            ["scalar", "object"],
            help="Choose whether this array contains simple values or complex objects",
            key="schema_array_type"
        )
    
    # Array-specific configuration (outside form for dynamic updates)
    if array_type == "scalar":
        st.markdown("### Scalar Array Configuration")
        array_items_config = render_scalar_array_config()
    else:
        st.markdown("### Object Array Configuration")
        array_items_config = render_object_array_config()
    
    # Submit button (outside form)
    if st.button("Create Array Field", key="create_array_field_btn"):
        if field_name:
            # Create field configuration
            field_config = {
                "type": "array",
                "label": field_label or field_name,
                "required": field_required,
                "help": field_help or f"Array field: {field_name}"
            }
            
            field_config["items"] = array_items_config
            
            # Add to session state
            st.session_state.schema_editor_fields[field_name] = field_config
            st.success(f"Created array field: {field_name}")
            st.rerun()
        else:
            st.error("Please provide a field name")
    
    # Display created fields
    if st.session_state.schema_editor_fields:
        st.subheader("Created Array Fields")
        
        for field_name, field_config in st.session_state.schema_editor_fields.items():
            with st.expander(f"📋 {field_config.get('label', field_name)}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.json(field_config)
                
                with col2:
                    if st.button(f"🗑️ Delete", key=f"delete_{field_name}"):
                        del st.session_state.schema_editor_fields[field_name]
                        st.rerun()
        
        # Generate complete schema
        st.subheader("Generated Schema YAML")
        complete_schema = {
            "title": "Generated Schema",
            "description": "Schema created using array field editor",
            "fields": st.session_state.schema_editor_fields
        }
        
        st.code(yaml.dump(complete_schema, default_flow_style=False), language="yaml")
        
        # Clear all button
        if st.button("🗑️ Clear All Fields"):
            st.session_state.schema_editor_fields = {}
            st.rerun()

def render_validation_page(test_schemas: Dict, test_data: Dict):
    """Render validation testing page"""
    st.header("Validation Testing")
    st.markdown("Test validation rules and error handling for array fields")
    
    # Schema selection
    schema_choice = st.selectbox(
        "Select Test Schema",
        ["insurance_document", "purchase_order"],
        format_func=lambda x: test_schemas[x]["title"],
        key="validation_schema_choice"
    )
    
    schema = test_schemas[schema_choice]
    
    # Initialize session state for validation data
    if f"validation_data_{schema_choice}" not in st.session_state:
        st.session_state[f"validation_data_{schema_choice}"] = copy.deepcopy(test_data[schema_choice])
    
    current_data = st.session_state[f"validation_data_{schema_choice}"]
    
    st.subheader("Test Data for Validation")
    
    # Allow editing test data to introduce errors
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Edit Test Data")
        st.markdown("Modify the data below to test validation scenarios:")
        
        # Create editable JSON
        edited_json = st.text_area(
            "JSON Data",
            value=json.dumps(current_data, indent=2),
            height=300,
            key=f"validation_json_{schema_choice}"
        )
        
        # Parse edited JSON
        try:
            edited_data = json.loads(edited_json)
            st.session_state[f"validation_data_{schema_choice}"] = edited_data
            current_data = edited_data
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            edited_data = current_data
    
    with col2:
        st.markdown("#### Validation Results")
        
        # Validate button
        if st.button("🔍 Validate Data", key=f"validate_{schema_choice}"):
            validation_results = comprehensive_validate_data(current_data, schema)
            
            # Display validation results
            if validation_results["is_valid"]:
                st.success("✅ All data is valid!")
                st.balloons()
            else:
                st.error(f"❌ Found {len(validation_results['errors'])} validation errors:")
                
                # Group errors by field
                errors_by_field = {}
                for error in validation_results["errors"]:
                    field_path = error["field_path"]
                    if field_path not in errors_by_field:
                        errors_by_field[field_path] = []
                    errors_by_field[field_path].append(error)
                
                # Display errors by field
                for field_path, field_errors in errors_by_field.items():
                    with st.expander(f"🚨 {field_path} ({len(field_errors)} errors)"):
                        for error in field_errors:
                            st.error(f"**{error['error_type']}**: {error['message']}")
                            if error.get('suggestion'):
                                st.info(f"💡 Suggestion: {error['suggestion']}")
        
        # Real-time validation toggle
        real_time_validation = st.checkbox("Real-time Validation", key=f"realtime_{schema_choice}")
        
        if real_time_validation:
            validation_results = comprehensive_validate_data(current_data, schema)
            
            if validation_results["is_valid"]:
                st.success("✅ Real-time: Data is valid")
            else:
                st.warning(f"⚠️ Real-time: {len(validation_results['errors'])} errors found")
    
    # Validation scenarios section
    st.subheader("Pre-defined Validation Scenarios")
    
    scenarios = get_validation_scenarios(schema_choice)
    
    for scenario_name, scenario_data in scenarios.items():
        with st.expander(f"📋 {scenario_name}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.json(scenario_data["data"])
                st.markdown(f"**Expected Result**: {scenario_data['expected_result']}")
                if scenario_data.get("description"):
                    st.markdown(f"*{scenario_data['description']}*")
            
            with col2:
                if st.button(f"Test Scenario", key=f"test_{scenario_name}"):
                    validation_results = comprehensive_validate_data(scenario_data["data"], schema)
                    
                    # Check if result matches expectation
                    expected_valid = scenario_data["expected_result"] == "valid"
                    actual_valid = validation_results["is_valid"]
                    
                    if expected_valid == actual_valid:
                        st.success("✅ Scenario passed!")
                    else:
                        st.error("❌ Scenario failed!")
                    
                    # Show validation details
                    if not actual_valid:
                        for error in validation_results["errors"]:
                            st.error(f"{error['field_path']}: {error['message']}")
    
    # Reset button
    if st.button("🔄 Reset to Original Data", key=f"reset_validation_{schema_choice}"):
        st.session_state[f"validation_data_{schema_choice}"] = copy.deepcopy(test_data[schema_choice])
        st.rerun()

def render_scalar_array_editor(field_name: str, field_config: Dict[str, Any], current_value: List[Any]) -> List[Any]:
    """
    Render a user-friendly editor for arrays of scalar values
    
    Args:
        field_name: Name of the field
        field_config: Field configuration from schema
        current_value: Current array value
        
    Returns:
        Updated array value
    """
    items_config = field_config.get("items", {})
    item_type = items_config.get("type", "string")
    
    # Initialize array if empty
    if not current_value:
        current_value = []
    
    # Create a copy to work with
    working_array = current_value.copy()
    
    # Initialize removal state if not exists
    removal_key = f"remove_item_{field_name}"
    if removal_key not in st.session_state:
        st.session_state[removal_key] = None
    
    # Initialize add state for better button handling
    add_key = f"add_item_{field_name}"
    if add_key not in st.session_state:
        st.session_state[add_key] = False
    
    # Container for the array editor
    with st.container():
        # Instructions for scalar array editing
        st.info("💡 **How to edit**: Modify values in the input fields. Use '➕ Add Item' to add new items. Click '🗑️' next to any item to remove it.")
        
        # Add item section at the top
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**{field_config.get('label', field_name)}** ({item_type} array)")
        
        with col2:
            # Add item button with session state handling
            add_button_key = f"add_{field_name}_{item_type}"
            if st.button(f"➕ Add Item", key=add_button_key):
                st.session_state[add_key] = True
                st.rerun()  # Force immediate rerun
        
        # Handle add item request
        if st.session_state.get(add_key, False):
            default_value = get_default_value_for_type(item_type, items_config)
            working_array.append(default_value)
            st.session_state[add_key] = False  # Reset add state
        
        # Handle item removal first (check for removal requests)
        removal_key = f"remove_item_{field_name}"
        if removal_key in st.session_state and st.session_state[removal_key] is not None:
            item_to_remove = st.session_state[removal_key]
            if 0 <= item_to_remove < len(working_array):
                working_array.pop(item_to_remove)
            st.session_state[removal_key] = None  # Reset removal state
        
        # Render existing items
        for i, item_value in enumerate(working_array):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Render input based on item type
                new_value = render_scalar_input(
                    f"{field_name}[{i}]",
                    item_type,
                    item_value,
                    items_config,
                    key=f"{field_name}_item_{i}"
                )
                working_array[i] = new_value
            
            with col2:
                # Remove button - store removal request in session state
                if st.button("🗑️", key=f"remove_{field_name}_{i}", help="Remove this item"):
                    st.session_state[removal_key] = i
                    st.rerun()  # Force immediate rerun to process removal
        
        # Validation feedback
        validation_errors = validate_scalar_array(field_name, working_array, items_config)
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        else:
            if working_array:  # Only show success if array is not empty
                st.success(f"✅ {len(working_array)} items valid")
    
    return working_array

def get_default_value_for_type(item_type: str, items_config: Dict[str, Any]) -> Any:
    """Get appropriate default value for array item type, respecting constraints"""
    if item_type == "string":
        return ""
    elif item_type == "number":
        min_val = items_config.get("min_value", 0.0)
        return max(0.0, float(min_val)) if min_val is not None else 0.0
    elif item_type == "integer":
        min_val = items_config.get("min_value", 0)
        return max(0, int(min_val)) if min_val is not None else 0
    elif item_type == "boolean":
        return False
    elif item_type == "date":
        return datetime.now().strftime("%Y-%m-%d")
    else:
        return ""

def render_scalar_input(field_name: str, item_type: str, current_value: Any, items_config: Dict[str, Any], key: str) -> Any:
    """Render appropriate input widget for scalar array item"""
    
    if item_type == "string":
        value = st.text_input(
            f"Item {key.split('_')[-1]}",
            value=str(current_value) if current_value is not None else "",
            key=key,
            help=f"String value for {field_name}"
        )
        return value
    
    elif item_type == "number":
        min_val = items_config.get("min_value", None)
        max_val = items_config.get("max_value", None)
        step = items_config.get("step", 0.01)
        
        # Ensure all numeric types are consistent (float)
        min_val = float(min_val) if min_val is not None else None
        max_val = float(max_val) if max_val is not None else None
        step = float(step)
        
        value = st.number_input(
            f"Item {key.split('_')[-1]}",
            value=float(current_value) if current_value is not None else 0.0,
            min_value=min_val,
            max_value=max_val,
            step=step,
            format="%.2f",  # Limit to 2 decimal places like main codebase
            key=key,
            help=f"Number value for {field_name}"
        )
        # Round to 2 decimal places to avoid floating point precision issues
        return round(value, 2)
    
    elif item_type == "integer":
        min_val = items_config.get("min_value", None)
        max_val = items_config.get("max_value", None)
        step = items_config.get("step", 1)
        
        # Ensure all numeric types are consistent (int)
        min_val = int(min_val) if min_val is not None else None
        max_val = int(max_val) if max_val is not None else None
        step = int(step)
        
        value = st.number_input(
            f"Item {key.split('_')[-1]}",
            value=int(current_value) if current_value is not None else 0,
            min_value=min_val,
            max_value=max_val,
            step=step,
            format="%d",  # Integer format like main codebase
            key=key,
            help=f"Integer value for {field_name}"
        )
        return int(value)
    
    elif item_type == "boolean":
        value = st.checkbox(
            f"Item {key.split('_')[-1]}",
            value=bool(current_value) if current_value is not None else False,
            key=key,
            help=f"Boolean value for {field_name}"
        )
        return value
    
    elif item_type == "date":
        try:
            if isinstance(current_value, str):
                current_date = datetime.strptime(current_value, "%Y-%m-%d").date()
            elif isinstance(current_value, date):
                current_date = current_value
            else:
                current_date = datetime.now().date()
        except (ValueError, TypeError):
            current_date = datetime.now().date()
        
        value = st.date_input(
            f"Item {key.split('_')[-1]}",
            value=current_date,
            key=key,
            help=f"Date value for {field_name}"
        )
        return value.strftime("%Y-%m-%d")
    
    else:
        # Fallback to text input
        value = st.text_input(
            f"Item {key.split('_')[-1]}",
            value=str(current_value) if current_value is not None else "",
            key=key,
            help=f"Value for {field_name}"
        )
        return value

def validate_scalar_array(field_name: str, array_value: List[Any], items_config: Dict[str, Any]) -> List[str]:
    """Validate scalar array according to schema constraints"""
    errors = []
    item_type = items_config.get("type", "string")
    
    for i, item_value in enumerate(array_value):
        item_errors = validate_scalar_item(f"{field_name}[{i}]", item_value, item_type, items_config)
        errors.extend(item_errors)
    
    return errors

def validate_scalar_item(item_path: str, value: Any, item_type: str, items_config: Dict[str, Any]) -> List[str]:
    """Validate individual scalar array item"""
    errors = []
    
    # Type validation
    if item_type == "string":
        if not isinstance(value, str):
            errors.append(f"{item_path}: must be a string")
            return errors
        
        # String constraints
        min_length = items_config.get("min_length")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{item_path}: must be at least {min_length} characters long")
        
        max_length = items_config.get("max_length")
        if max_length is not None and len(value) > max_length:
            errors.append(f"{item_path}: must be no more than {max_length} characters long")
        
        pattern = items_config.get("pattern")
        if pattern and value:
            import re
            if not re.match(pattern, value):
                errors.append(f"{item_path}: must match pattern {pattern}")
    
    elif item_type in ["number", "integer"]:
        try:
            numeric_value = float(value) if item_type == "number" else int(value)
        except (ValueError, TypeError):
            errors.append(f"{item_path}: must be a valid {item_type}")
            return errors
        
        min_value = items_config.get("min_value")
        if min_value is not None and numeric_value < min_value:
            errors.append(f"{item_path}: must be at least {min_value}")
        
        max_value = items_config.get("max_value")
        if max_value is not None and numeric_value > max_value:
            errors.append(f"{item_path}: must be no more than {max_value}")
    
    elif item_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{item_path}: must be a boolean")
    
    elif item_type == "date":
        if isinstance(value, str):
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                errors.append(f"{item_path}: must be a valid date in YYYY-MM-DD format")
        elif not isinstance(value, date):
            errors.append(f"{item_path}: must be a valid date")
    
    return errors

def render_object_array_editor(field_name: str, field_config: Dict[str, Any], current_value: List[Dict]) -> List[Dict]:
    """
    Render a table-style editor for arrays of objects using st.data_editor
    
    Args:
        field_name: Name of the field
        field_config: Field configuration from schema
        current_value: Current array value
        
    Returns:
        Updated array value
    """
    items_config = field_config.get("items", {})
    properties = items_config.get("properties", {})
    
    # Initialize array if empty
    if not current_value:
        current_value = []
    
    # Create a copy to work with
    working_array = current_value.copy()
    
    # Generate column configuration for st.data_editor
    column_config = generate_column_config(properties)
    
    # Container for the object array editor
    with st.container():
        # Instructions for object array editing
        st.info("💡 **How to edit**: Click cells to edit values directly in the table. Use 'Add Row' to add new items. Use the row deletion section below to remove rows.")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            # Add row button
            if st.button(f"➕ Add Row", key=f"add_row_{field_name}"):
                new_object = create_default_object(properties)
                working_array.append(new_object)
                st.rerun()  # Force immediate rerun to show new row
        
        # Display the data editor if we have data
        if working_array:
            # Convert to DataFrame-like structure for st.data_editor
            import pandas as pd
            df = pd.DataFrame(working_array)
            
            # Use st.data_editor for table editing with delete capability
            edited_df = st.data_editor(
                df,
                column_config=column_config,
                num_rows="dynamic",
                use_container_width=True,
                key=f"data_editor_{field_name}",
                hide_index=False  # Show index to help with row identification
            )
            
            # Convert back to list of dictionaries
            working_array = edited_df.to_dict('records')
            
            # Clean up any NaN values that pandas might introduce
            working_array = clean_object_array(working_array)
            
            # Add manual row deletion interface
            if len(working_array) > 0:
                st.markdown("#### Manual Row Operations")
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    row_to_delete = st.selectbox(
                        "Select row to delete:",
                        options=list(range(len(working_array))),
                        format_func=lambda x: f"Row {x}: {working_array[x].get(list(working_array[x].keys())[0], 'N/A') if working_array[x] else 'Empty'}",
                        key=f"delete_row_select_{field_name}"
                    )
                
                with col2:
                    if st.button("🗑️ Delete Selected Row", key=f"delete_row_{field_name}"):
                        if 0 <= row_to_delete < len(working_array):
                            working_array.pop(row_to_delete)
                            st.success(f"Deleted row {row_to_delete}")
                            st.rerun()
        else:
            st.info("No items in array. Click 'Add Row' to add the first item.")
        
        # Validation feedback
        validation_errors = validate_object_array(field_name, working_array, items_config)
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        else:
            if working_array:  # Only show success if array is not empty
                st.success(f"✅ {len(working_array)} objects valid")
    
    return working_array

def generate_column_config(properties: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Generate column configuration for st.data_editor based on object properties"""
    column_config = {}
    
    for prop_name, prop_config in properties.items():
        prop_type = prop_config.get("type", "string")
        label = prop_config.get("label", prop_name)
        help_text = prop_config.get("help", "")
        required = prop_config.get("required", False)
        
        if prop_type == "string":
            column_config[prop_name] = st.column_config.TextColumn(
                label=label,
                help=help_text,
                required=required,
                max_chars=prop_config.get("max_length", None)
            )
        elif prop_type == "number":
            column_config[prop_name] = st.column_config.NumberColumn(
                label=label,
                help=help_text,
                required=required,
                min_value=prop_config.get("min_value", None),
                max_value=prop_config.get("max_value", None),
                step=prop_config.get("step", 0.01),
                format="%.2f"
            )
        elif prop_type == "integer":
            column_config[prop_name] = st.column_config.NumberColumn(
                label=label,
                help=help_text,
                required=required,
                min_value=prop_config.get("min_value", None),
                max_value=prop_config.get("max_value", None),
                step=prop_config.get("step", 1),
                format="%d"
            )
        elif prop_type == "boolean":
            column_config[prop_name] = st.column_config.CheckboxColumn(
                label=label,
                help=help_text,
                required=required
            )
        elif prop_type == "date":
            column_config[prop_name] = st.column_config.DateColumn(
                label=label,
                help=help_text,
                required=required
            )
        else:
            # Default to text column
            column_config[prop_name] = st.column_config.TextColumn(
                label=label,
                help=help_text,
                required=required
            )
    
    return column_config

def create_default_object(properties: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Create a default object with appropriate default values for each property"""
    default_object = {}
    
    for prop_name, prop_config in properties.items():
        prop_type = prop_config.get("type", "string")
        default_object[prop_name] = get_default_value_for_type(prop_type, prop_config)
    
    return default_object

def clean_object_array(array: List[Dict]) -> List[Dict]:
    """Clean object array by removing NaN values and converting types"""
    import pandas as pd
    import numpy as np
    
    cleaned_array = []
    for obj in array:
        cleaned_obj = {}
        for key, value in obj.items():
            # Handle pandas NaN values
            if pd.isna(value):
                cleaned_obj[key] = None
            elif isinstance(value, np.integer):
                cleaned_obj[key] = int(value)
            elif isinstance(value, np.floating):
                cleaned_obj[key] = float(value)
            else:
                cleaned_obj[key] = value
        cleaned_array.append(cleaned_obj)
    
    return cleaned_array

def validate_object_array(field_name: str, array_value: List[Dict], items_config: Dict[str, Any]) -> List[str]:
    """Validate object array according to schema constraints"""
    errors = []
    properties = items_config.get("properties", {})
    
    for i, obj in enumerate(array_value):
        obj_errors = validate_object_item(f"{field_name}[{i}]", obj, properties)
        errors.extend(obj_errors)
    
    return errors

def validate_object_item(item_path: str, obj: Dict[str, Any], properties: Dict[str, Dict[str, Any]]) -> List[str]:
    """Validate individual object in array"""
    errors = []
    
    # Check required properties
    for prop_name, prop_config in properties.items():
        required = prop_config.get("required", False)
        prop_type = prop_config.get("type", "string")
        
        if required and (prop_name not in obj or obj[prop_name] is None or obj[prop_name] == ""):
            errors.append(f"{item_path}.{prop_name}: is required")
            continue
        
        # Skip validation if property is not present or is None/empty (for optional fields)
        if prop_name not in obj or obj[prop_name] is None:
            continue
        
        value = obj[prop_name]
        
        # Validate property value
        prop_errors = validate_scalar_item(f"{item_path}.{prop_name}", value, prop_type, prop_config)
        errors.extend(prop_errors)
    
    return errors

def render_scalar_array_config() -> Dict[str, Any]:
    """Render configuration interface for scalar array fields"""
    
    # Initialize the selected type in session state
    if "scalar_array_item_type" not in st.session_state:
        st.session_state.scalar_array_item_type = "string"
    
    # Use session state to track the current selection
    current_selection = st.selectbox(
        "Item Type",
        ["string", "number", "integer", "boolean", "date", "enum"],
        index=["string", "number", "integer", "boolean", "date", "enum"].index(st.session_state.scalar_array_item_type),
        help="Type of values in the array",
        key="scalar_type_selectbox"
    )
    
    # Update session state and detect changes
    type_changed = st.session_state.scalar_array_item_type != current_selection
    if type_changed:
        st.session_state.scalar_array_item_type = current_selection
    
    item_type = current_selection
    
    # Debug information (can be removed in production)
    # st.write(f"🐛 DEBUG: Current selection: {current_selection}")
    # st.write(f"🐛 DEBUG: Session state type: {st.session_state.scalar_array_item_type}")
    # st.write(f"🐛 DEBUG: Type changed: {type_changed}")
    
    config = {"type": item_type}
    
    # Type-specific constraints with unique keys per type
    # st.write(f"🐛 DEBUG: Rendering constraints for type: {item_type}")
    
    if item_type == "string":
        st.markdown("#### String Constraints")
        # st.write("🐛 DEBUG: Showing STRING constraint widgets")
        col1, col2 = st.columns(2)
        with col1:
            min_length = st.number_input("Min Length", min_value=0, value=0, step=1, key="string_min_len")
            if min_length > 0:
                config["min_length"] = min_length
        
        with col2:
            max_length = st.number_input("Max Length", min_value=1, value=100, step=1, key="string_max_len")
            config["max_length"] = max_length
        
        pattern = st.text_input("Pattern (regex)", placeholder="e.g., ^[A-Z0-9]+$", key="string_pattern")
        if pattern:
            config["pattern"] = pattern
    
    elif item_type == "number":
        st.markdown("#### Number Constraints")
        # st.write("🐛 DEBUG: Showing NUMBER constraint widgets")
        col1, col2 = st.columns(2)
        with col1:
            min_value = st.number_input("Min Value", value=0.0, key="number_min", format="%.2f")
            config["min_value"] = round(min_value, 2)  # Round to 2 decimal places
        
        with col2:
            max_value = st.number_input("Max Value", value=1000.0, key="number_max", format="%.2f")
            config["max_value"] = round(max_value, 2)  # Round to 2 decimal places
        
        step = st.number_input("Step", min_value=0.01, value=0.01, step=0.01, key="number_step", format="%.2f")
        config["step"] = round(step, 2)  # Round to 2 decimal places
    
    elif item_type == "integer":
        st.markdown("#### Integer Constraints")
        # st.write("🐛 DEBUG: Showing INTEGER constraint widgets")
        col1, col2 = st.columns(2)
        with col1:
            min_value = st.number_input("Min Value", value=0, step=1, key="integer_min")
            config["min_value"] = int(min_value)
        
        with col2:
            max_value = st.number_input("Max Value", value=1000, step=1, key="integer_max")
            config["max_value"] = int(max_value)
        
        step = st.number_input("Step", min_value=1, value=1, step=1, key="integer_step")
        config["step"] = int(step)
    
    elif item_type == "boolean":
        st.markdown("#### Boolean Options")
        # st.write("🐛 DEBUG: Showing BOOLEAN constraint widgets")
        default_value = st.checkbox("Default Value", key="boolean_default")
        config["default"] = default_value
    
    elif item_type == "date":
        st.markdown("#### Date Options")
        # st.write("🐛 DEBUG: Showing DATE constraint widgets")
        st.info("Date arrays use YYYY-MM-DD format")
    
    elif item_type == "enum":
        st.markdown("#### Enum Options")
        # st.write("🐛 DEBUG: Showing ENUM constraint widgets")
        choices_text = st.text_area(
            "Choices (one per line)",
            placeholder="option1\noption2\noption3",
            key="enum_choices"
        )
        if choices_text:
            choices = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
            config["choices"] = choices
        else:
            st.warning("Please provide at least one choice for enum type")
    
    return config

def render_object_array_config() -> Dict[str, Any]:
    """Render configuration interface for object array fields"""
    st.markdown("#### Object Properties")
    
    # Initialize properties in session state with unique key
    props_key = "temp_object_properties_schema_editor"
    if props_key not in st.session_state:
        st.session_state[props_key] = {}
    
    # Add new property interface (outside form for dynamic updates)
    with st.expander("➕ Add New Property", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            prop_name = st.text_input("Property Name", placeholder="e.g., item_code", key="obj_prop_name")
            prop_label = st.text_input("Property Label", placeholder="e.g., Item Code", key="obj_prop_label")
            prop_required = st.checkbox("Required Property", key="obj_prop_required")
        
        with col2:
            prop_type = st.selectbox(
                "Property Type",
                ["string", "number", "integer", "boolean", "date", "enum"],
                key="obj_prop_type_select"
            )
            prop_help = st.text_input("Help Text", placeholder="Description of this property", key="obj_prop_help")
        
        # Property-specific constraints (dynamic based on type)
        prop_config = {"type": prop_type, "label": prop_label or prop_name, "required": prop_required}
        if prop_help:
            prop_config["help"] = prop_help
        
        # Dynamic constraints based on property type
        if prop_type == "string":
            st.markdown("**String Constraints**")
            col1, col2 = st.columns(2)
            with col1:
                min_len = st.number_input("Min Length", min_value=0, value=0, step=1, key="obj_prop_min_len")
                if min_len > 0:
                    prop_config["min_length"] = min_len
            
            with col2:
                max_len = st.number_input("Max Length", min_value=1, value=100, step=1, key="obj_prop_max_len")
                prop_config["max_length"] = max_len
            
            pattern = st.text_input("Pattern (regex)", key="obj_prop_pattern", placeholder="e.g., ^[A-Z0-9]+$")
            if pattern:
                prop_config["pattern"] = pattern
        
        elif prop_type == "number":
            st.markdown("**Number Constraints**")
            col1, col2 = st.columns(2)
            with col1:
                min_val = st.number_input("Min Value", value=0.0, key="obj_prop_min_val", format="%.2f")
                prop_config["min_value"] = round(min_val, 2)  # Round to 2 decimal places
            
            with col2:
                max_val = st.number_input("Max Value", value=1000.0, key="obj_prop_max_val", format="%.2f")
                prop_config["max_value"] = round(max_val, 2)  # Round to 2 decimal places
            
            step_val = st.number_input("Step", min_value=0.01, value=0.01, step=0.01, key="obj_prop_step", format="%.2f")
            prop_config["step"] = round(step_val, 2)  # Round to 2 decimal places
        
        elif prop_type == "integer":
            st.markdown("**Integer Constraints**")
            col1, col2 = st.columns(2)
            with col1:
                min_val = st.number_input("Min Value", value=0, step=1, key="obj_prop_min_val_int")
                prop_config["min_value"] = int(min_val)
            
            with col2:
                max_val = st.number_input("Max Value", value=1000, step=1, key="obj_prop_max_val_int")
                prop_config["max_value"] = int(max_val)
            
            step_val = st.number_input("Step", min_value=1, value=1, step=1, key="obj_prop_step_int")
            prop_config["step"] = int(step_val)
        
        elif prop_type == "boolean":
            st.markdown("**Boolean Options**")
            default_val = st.checkbox("Default Value", key="obj_prop_bool_default")
            prop_config["default"] = default_val
        
        elif prop_type == "enum":
            st.markdown("**Enum Options**")
            choices_text = st.text_area(
                "Choices (one per line)",
                placeholder="option1\noption2\noption3",
                key="obj_prop_enum_choices"
            )
            if choices_text:
                choices = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
                prop_config["choices"] = choices
        
        # Add property button (outside form)
        if st.button("Add Property", key="add_obj_property_btn") and prop_name:
            st.session_state[props_key][prop_name] = prop_config
            st.success(f"Added property: {prop_name}")
            st.rerun()
    
    # Display current properties
    if st.session_state[props_key]:
        st.markdown("#### Current Properties")
        
        for prop_name, prop_config in st.session_state[props_key].items():
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"**{prop_config.get('label', prop_name)}** ({prop_config['type']})")
                    if prop_config.get('required'):
                        st.markdown("🔴 *Required*")
                    else:
                        st.markdown("⚪ *Optional*")
                    if prop_config.get('help'):
                        st.markdown(f"*{prop_config['help']}*")
                    
                    # Show constraints
                    constraints = []
                    if 'min_length' in prop_config:
                        constraints.append(f"min_length: {prop_config['min_length']}")
                    if 'max_length' in prop_config:
                        constraints.append(f"max_length: {prop_config['max_length']}")
                    if 'min_value' in prop_config:
                        constraints.append(f"min_value: {prop_config['min_value']}")
                    if 'max_value' in prop_config:
                        constraints.append(f"max_value: {prop_config['max_value']}")
                    if 'pattern' in prop_config:
                        constraints.append(f"pattern: {prop_config['pattern']}")
                    if 'choices' in prop_config:
                        constraints.append(f"choices: {prop_config['choices']}")
                    
                    if constraints:
                        st.markdown(f"*Constraints: {', '.join(constraints)}*")
                
                with col2:
                    if st.button("🗑️", key=f"remove_obj_prop_{prop_name}", help="Remove property"):
                        del st.session_state[props_key][prop_name]
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info("No properties added yet. Add properties using the form above.")
    
    # Clear all properties button
    if st.session_state[props_key]:
        if st.button("🗑️ Clear All Properties", key="clear_all_obj_props"):
            st.session_state[props_key] = {}
            st.rerun()
    
    # Return object configuration
    return {
        "type": "object",
        "properties": st.session_state[props_key].copy()
    }

def comprehensive_validate_data(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive validation of data against schema with detailed error reporting
    
    Returns:
        Dict with 'is_valid' boolean and 'errors' list with detailed error information
    """
    errors = []
    fields = schema.get("fields", {})
    
    # Validate each field in the schema
    for field_name, field_config in fields.items():
        field_errors = validate_field_comprehensive(field_name, data.get(field_name), field_config)
        errors.extend(field_errors)
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors
    }

def validate_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validate a single field with comprehensive error reporting"""
    errors = []
    field_type = field_config.get("type")
    required = field_config.get("required", False)
    
    # Check required fields
    if required and (value is None or value == "" or (isinstance(value, list) and len(value) == 0)):
        errors.append({
            "field_path": field_name,
            "error_type": "Required Field",
            "message": f"Field '{field_name}' is required but is missing or empty",
            "suggestion": f"Provide a value for {field_name}"
        })
        return errors  # Don't continue validation if required field is missing
    
    # Skip validation if field is optional and empty
    if not required and (value is None or value == ""):
        return errors
    
    # Type-specific validation
    if field_type == "array":
        array_errors = validate_array_field_comprehensive(field_name, value, field_config)
        errors.extend(array_errors)
    elif field_type == "string":
        string_errors = validate_string_field_comprehensive(field_name, value, field_config)
        errors.extend(string_errors)
    elif field_type == "number":
        number_errors = validate_number_field_comprehensive(field_name, value, field_config)
        errors.extend(number_errors)
    elif field_type == "integer":
        integer_errors = validate_integer_field_comprehensive(field_name, value, field_config)
        errors.extend(integer_errors)
    elif field_type == "boolean":
        boolean_errors = validate_boolean_field_comprehensive(field_name, value, field_config)
        errors.extend(boolean_errors)
    elif field_type == "date":
        date_errors = validate_date_field_comprehensive(field_name, value, field_config)
        errors.extend(date_errors)
    
    return errors

def validate_array_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comprehensive validation for array fields"""
    errors = []
    
    # Check if value is actually an array
    if not isinstance(value, list):
        errors.append({
            "field_path": field_name,
            "error_type": "Type Error",
            "message": f"Field '{field_name}' must be an array, got {type(value).__name__}",
            "suggestion": "Ensure the field contains a JSON array (e.g., [\"item1\", \"item2\"])"
        })
        return errors
    
    items_config = field_config.get("items", {})
    items_type = items_config.get("type")
    
    # Validate each item in the array
    for i, item in enumerate(value):
        item_path = f"{field_name}[{i}]"
        
        if items_type == "object":
            # Validate object items
            properties = items_config.get("properties", {})
            if not isinstance(item, dict):
                errors.append({
                    "field_path": item_path,
                    "error_type": "Type Error",
                    "message": f"Array item at {item_path} must be an object, got {type(item).__name__}",
                    "suggestion": "Ensure array items are JSON objects with properties"
                })
                continue
            
            # Validate object properties
            for prop_name, prop_config in properties.items():
                prop_path = f"{item_path}.{prop_name}"
                prop_value = item.get(prop_name)
                prop_errors = validate_field_comprehensive(prop_path, prop_value, prop_config)
                errors.extend(prop_errors)
        else:
            # Validate scalar items
            item_errors = validate_scalar_item_comprehensive(item_path, item, items_config)
            errors.extend(item_errors)
    
    return errors

def validate_scalar_item_comprehensive(item_path: str, value: Any, items_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comprehensive validation for scalar array items"""
    errors = []
    item_type = items_config.get("type", "string")
    
    # Type validation with detailed messages
    if item_type == "string":
        if not isinstance(value, str):
            errors.append({
                "field_path": item_path,
                "error_type": "Type Error",
                "message": f"Item at {item_path} must be a string, got {type(value).__name__}",
                "suggestion": "Ensure the value is enclosed in quotes"
            })
            return errors
        
        # String constraints
        min_length = items_config.get("min_length")
        if min_length is not None and len(value) < min_length:
            errors.append({
                "field_path": item_path,
                "error_type": "Length Constraint",
                "message": f"Item at {item_path} must be at least {min_length} characters long, got {len(value)}",
                "suggestion": f"Add more characters to reach minimum length of {min_length}"
            })
        
        max_length = items_config.get("max_length")
        if max_length is not None and len(value) > max_length:
            errors.append({
                "field_path": item_path,
                "error_type": "Length Constraint",
                "message": f"Item at {item_path} must be no more than {max_length} characters long, got {len(value)}",
                "suggestion": f"Shorten the text to {max_length} characters or less"
            })
        
        pattern = items_config.get("pattern")
        if pattern and value:
            import re
            if not re.match(pattern, value):
                errors.append({
                    "field_path": item_path,
                    "error_type": "Pattern Constraint",
                    "message": f"Item at {item_path} must match pattern '{pattern}', got '{value}'",
                    "suggestion": f"Ensure the value follows the required pattern: {pattern}"
                })
    
    elif item_type in ["number", "integer"]:
        try:
            numeric_value = float(value) if item_type == "number" else int(value)
        except (ValueError, TypeError):
            errors.append({
                "field_path": item_path,
                "error_type": "Type Error",
                "message": f"Item at {item_path} must be a valid {item_type}, got '{value}'",
                "suggestion": f"Provide a numeric value (e.g., 42 for integer, 42.5 for number)"
            })
            return errors
        
        min_value = items_config.get("min_value")
        if min_value is not None and numeric_value < min_value:
            errors.append({
                "field_path": item_path,
                "error_type": "Range Constraint",
                "message": f"Item at {item_path} must be at least {min_value}, got {numeric_value}",
                "suggestion": f"Use a value of {min_value} or higher"
            })
        
        max_value = items_config.get("max_value")
        if max_value is not None and numeric_value > max_value:
            errors.append({
                "field_path": item_path,
                "error_type": "Range Constraint",
                "message": f"Item at {item_path} must be no more than {max_value}, got {numeric_value}",
                "suggestion": f"Use a value of {max_value} or lower"
            })
    
    elif item_type == "boolean":
        if not isinstance(value, bool):
            errors.append({
                "field_path": item_path,
                "error_type": "Type Error",
                "message": f"Item at {item_path} must be a boolean, got {type(value).__name__}",
                "suggestion": "Use true or false (without quotes)"
            })
    
    elif item_type == "date":
        if isinstance(value, str):
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                errors.append({
                    "field_path": item_path,
                    "error_type": "Format Error",
                    "message": f"Item at {item_path} must be a valid date in YYYY-MM-DD format, got '{value}'",
                    "suggestion": "Use format like '2024-01-15'"
                })
        elif not isinstance(value, date):
            errors.append({
                "field_path": item_path,
                "error_type": "Type Error",
                "message": f"Item at {item_path} must be a valid date, got {type(value).__name__}",
                "suggestion": "Use date format YYYY-MM-DD in quotes"
            })
    
    return errors

def validate_string_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comprehensive validation for string fields"""
    errors = []
    
    if not isinstance(value, str):
        errors.append({
            "field_path": field_name,
            "error_type": "Type Error",
            "message": f"Field '{field_name}' must be a string, got {type(value).__name__}",
            "suggestion": "Enclose the value in quotes"
        })
        return errors
    
    # Apply same string validation as scalar items
    string_errors = validate_scalar_item_comprehensive(field_name, value, field_config)
    return string_errors

def validate_number_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comprehensive validation for number fields"""
    errors = []
    
    try:
        numeric_value = float(value)
    except (ValueError, TypeError):
        errors.append({
            "field_path": field_name,
            "error_type": "Type Error",
            "message": f"Field '{field_name}' must be a valid number, got '{value}'",
            "suggestion": "Provide a numeric value (e.g., 42.5)"
        })
        return errors
    
    # Apply same numeric validation as scalar items
    numeric_errors = validate_scalar_item_comprehensive(field_name, numeric_value, field_config)
    return numeric_errors

def validate_integer_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comprehensive validation for integer fields"""
    errors = []
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        errors.append({
            "field_path": field_name,
            "error_type": "Type Error",
            "message": f"Field '{field_name}' must be a valid integer, got '{value}'",
            "suggestion": "Provide a whole number (e.g., 42)"
        })
        return errors
    
    # Apply same integer validation as scalar items
    integer_errors = validate_scalar_item_comprehensive(field_name, int_value, field_config)
    return integer_errors

def validate_boolean_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comprehensive validation for boolean fields"""
    errors = []
    
    if not isinstance(value, bool):
        errors.append({
            "field_path": field_name,
            "error_type": "Type Error",
            "message": f"Field '{field_name}' must be a boolean, got {type(value).__name__}",
            "suggestion": "Use true or false (without quotes)"
        })
    
    return errors

def validate_date_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comprehensive validation for date fields"""
    errors = []
    
    if isinstance(value, str):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            errors.append({
                "field_path": field_name,
                "error_type": "Format Error",
                "message": f"Field '{field_name}' must be a valid date in YYYY-MM-DD format, got '{value}'",
                "suggestion": "Use format like '2024-01-15'"
            })
    elif not isinstance(value, date):
        errors.append({
            "field_path": field_name,
            "error_type": "Type Error",
            "message": f"Field '{field_name}' must be a valid date, got {type(value).__name__}",
            "suggestion": "Use date format YYYY-MM-DD in quotes"
        })
    
    return errors

def get_validation_scenarios(schema_choice: str) -> Dict[str, Dict[str, Any]]:
    """Get predefined validation scenarios for testing"""
    
    if schema_choice == "insurance_document":
        return {
            "Valid Data": {
                "data": {
                    "supplier_name": "Test Insurance Co.",
                    "client_name": "Test Client",
                    "policy_number": "POL123456",
                    "serial_numbers": ["SN001", "SN002", "SN003"],
                    "coverage_amounts": [10000.00, 25000.00, 50000.00],
                    "inspection_years": [2024, 2025],
                    "coverage_active": [True, False, True],
                    "renewal_dates": ["2024-12-31", "2025-06-30"],
                    "invoice_amount": 500.00,
                    "tags": ["insurance", "equipment"]
                },
                "expected_result": "valid",
                "description": "All fields including diverse array types meet validation requirements"
            },
            "Missing Required Fields": {
                "data": {
                    "client_name": "Test Client",
                    "serial_numbers": ["SN001"],
                    "invoice_amount": 500.00
                },
                "expected_result": "invalid",
                "description": "Missing required supplier_name and policy_number"
            },
            "Invalid Serial Numbers": {
                "data": {
                    "supplier_name": "Test Insurance Co.",
                    "client_name": "Test Client", 
                    "policy_number": "POL123456",
                    "serial_numbers": ["SN", "sn002", ""],
                    "invoice_amount": 500.00
                },
                "expected_result": "invalid",
                "description": "Serial numbers violate length and pattern constraints"
            },
            "Negative Invoice Amount": {
                "data": {
                    "supplier_name": "Test Insurance Co.",
                    "client_name": "Test Client",
                    "policy_number": "POL123456",
                    "serial_numbers": ["SN001"],
                    "invoice_amount": -100.00
                },
                "expected_result": "invalid",
                "description": "Invoice amount cannot be negative"
            },
            "Invalid Array Types": {
                "data": {
                    "supplier_name": "Test Insurance Co.",
                    "client_name": "Test Client",
                    "policy_number": "POL123456",
                    "serial_numbers": ["SN001"],
                    "coverage_amounts": [-1000.00, 2000000.00],  # Negative and too high
                    "inspection_years": [2019, 2035],  # Outside valid range
                    "coverage_active": ["yes", "no"],  # Wrong type (should be boolean)
                    "renewal_dates": ["2024/12/31", "invalid-date"],  # Wrong format
                    "invoice_amount": 500.00
                },
                "expected_result": "invalid",
                "description": "Various array types with constraint violations"
            }
        }
    
    elif schema_choice == "purchase_order":
        return {
            "Valid Purchase Order": {
                "data": {
                    "po_number": "PO-2024-001",
                    "vendor_name": "Test Vendor",
                    "order_date": "2024-01-15",
                    "line_items": [
                        {
                            "item_code": "ITM001",
                            "description": "Test Item",
                            "quantity": 5,
                            "unit_price": 100.00
                        }
                    ],
                    "total_amount": 500.00
                },
                "expected_result": "valid",
                "description": "Valid purchase order with one line item"
            },
            "Empty Line Items": {
                "data": {
                    "po_number": "PO-2024-001",
                    "vendor_name": "Test Vendor",
                    "order_date": "2024-01-15",
                    "line_items": [],
                    "total_amount": 0.00
                },
                "expected_result": "invalid",
                "description": "Line items array is required but empty"
            },
            "Invalid Line Item Properties": {
                "data": {
                    "po_number": "PO-2024-001",
                    "vendor_name": "Test Vendor",
                    "order_date": "2024-01-15",
                    "line_items": [
                        {
                            "item_code": "",
                            "description": "Test Item",
                            "quantity": 0,
                            "unit_price": -50.00
                        }
                    ],
                    "total_amount": 500.00
                },
                "expected_result": "invalid",
                "description": "Line item has empty item_code, zero quantity, and negative price"
            }
        }
    
    return {}

def render_test_scenarios_page(test_schemas: Dict, test_data: Dict):
    """Render test scenarios and feedback collection page"""
    st.header("Test Scenarios & Feedback")
    st.markdown("Structured test scenarios with feedback collection")
    
    # Initialize session state for feedback
    if "test_results" not in st.session_state:
        st.session_state.test_results = {}
    if "feedback_data" not in st.session_state:
        st.session_state.feedback_data = {}
    
    # Test scenario selection
    st.subheader("📋 Test Scenarios")
    
    scenario_categories = {
        "Insurance Document Tests": {
            "description": "Test array editing with insurance documents containing serial numbers and tags",
            "schema": "insurance_document",
            "scenarios": [
                {
                    "name": "Basic Serial Number Editing",
                    "description": "Add, edit, and remove serial numbers from an insurance document",
                    "steps": [
                        "1. Navigate to 'Scalar Array Editor' page",
                        "2. Select 'Insurance Document Schema'",
                        "3. Add 3 new serial numbers (e.g., SN004, SN005, SN006)",
                        "4. Edit an existing serial number",
                        "5. Remove one serial number",
                        "6. Verify validation works for invalid patterns"
                    ],
                    "expected_result": "Serial numbers should be editable with proper validation",
                    "test_data": test_data["insurance_document"]
                },
                {
                    "name": "Tag Management",
                    "description": "Test adding and managing categorization tags",
                    "steps": [
                        "1. Navigate to 'Scalar Array Editor' page",
                        "2. Add new tags (e.g., 'commercial', 'high-value')",
                        "3. Try adding an empty tag (should show validation error)",
                        "4. Try adding a very long tag (should show validation error)",
                        "5. Remove existing tags"
                    ],
                    "expected_result": "Tags should be manageable with length validation",
                    "test_data": test_data["insurance_document"]
                },
                {
                    "name": "Validation Error Recovery",
                    "description": "Test how well users can recover from validation errors",
                    "steps": [
                        "1. Navigate to 'Validation Testing' page",
                        "2. Modify serial numbers to invalid values (e.g., 'ab', 'xyz123')",
                        "3. Click 'Validate Data'",
                        "4. Review error messages",
                        "5. Fix the errors based on suggestions",
                        "6. Validate again to confirm fixes"
                    ],
                    "expected_result": "Clear error messages help users fix validation issues",
                    "test_data": test_data["insurance_document"]
                }
            ]
        },
        "Purchase Order Tests": {
            "description": "Test object array editing with purchase order line items",
            "schema": "purchase_order",
            "scenarios": [
                {
                    "name": "Line Item Management",
                    "description": "Add, edit, and remove line items in a purchase order",
                    "steps": [
                        "1. Navigate to 'Object Array Editor' page",
                        "2. Select 'Purchase Order Schema'",
                        "3. Add a new line item using 'Add Row' button",
                        "4. Edit existing line item properties in the table",
                        "5. Delete a line item",
                        "6. Test column-specific validation (e.g., negative prices)"
                    ],
                    "expected_result": "Line items should be editable in table format with validation",
                    "test_data": test_data["purchase_order"]
                },
                {
                    "name": "Complex Object Validation",
                    "description": "Test validation of object properties with various constraints",
                    "steps": [
                        "1. Navigate to 'Object Array Editor' page",
                        "2. Try entering invalid data (empty item codes, zero quantities)",
                        "3. Observe real-time validation feedback",
                        "4. Test required vs optional field validation",
                        "5. Test numeric range constraints"
                    ],
                    "expected_result": "Object property validation should work correctly",
                    "test_data": test_data["purchase_order"]
                }
            ]
        },
        "Schema Creation Tests": {
            "description": "Test creating array fields using the Schema Editor",
            "schema": None,
            "scenarios": [
                {
                    "name": "Create Scalar Array Field",
                    "description": "Create a new scalar array field configuration",
                    "steps": [
                        "1. Navigate to 'Schema Editor' page",
                        "2. Create a new scalar array field (e.g., 'product_codes')",
                        "3. Configure string constraints (pattern, length)",
                        "4. Generate YAML and verify structure",
                        "5. Test with different scalar types (number, boolean, date)"
                    ],
                    "expected_result": "Scalar array fields should be configurable with proper YAML output",
                    "test_data": {}
                },
                {
                    "name": "Create Object Array Field",
                    "description": "Create a new object array field with multiple properties",
                    "steps": [
                        "1. Navigate to 'Schema Editor' page",
                        "2. Create a new object array field (e.g., 'employees')",
                        "3. Add multiple properties with different types",
                        "4. Configure constraints for each property",
                        "5. Generate YAML and verify nested structure"
                    ],
                    "expected_result": "Object array fields should be configurable with property management",
                    "test_data": {}
                }
            ]
        }
    }
    
    # Render test scenarios
    for category_name, category_info in scenario_categories.items():
        with st.expander(f"📁 {category_name}", expanded=False):
            st.markdown(f"*{category_info['description']}*")
            
            for i, scenario in enumerate(category_info["scenarios"]):
                scenario_key = f"{category_name}_{i}"
                
                st.markdown(f"### 🧪 {scenario['name']}")
                st.markdown(f"**Description**: {scenario['description']}")
                
                # Test steps
                st.markdown("**Test Steps**:")
                for step in scenario["steps"]:
                    st.markdown(f"- {step}")
                
                st.markdown(f"**Expected Result**: {scenario['expected_result']}")
                
                # Test execution buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"▶️ Start Test", key=f"start_{scenario_key}"):
                        st.session_state.test_results[scenario_key] = {
                            "status": "in_progress",
                            "start_time": datetime.now().isoformat()
                        }
                        st.success(f"Started test: {scenario['name']}")
                
                with col2:
                    if st.button(f"✅ Mark Complete", key=f"complete_{scenario_key}"):
                        if scenario_key in st.session_state.test_results:
                            st.session_state.test_results[scenario_key]["status"] = "completed"
                            st.session_state.test_results[scenario_key]["end_time"] = datetime.now().isoformat()
                        st.success("Test marked as completed!")
                
                with col3:
                    if st.button(f"❌ Mark Failed", key=f"fail_{scenario_key}"):
                        if scenario_key in st.session_state.test_results:
                            st.session_state.test_results[scenario_key]["status"] = "failed"
                            st.session_state.test_results[scenario_key]["end_time"] = datetime.now().isoformat()
                        st.error("Test marked as failed!")
                
                # Show test status
                if scenario_key in st.session_state.test_results:
                    status = st.session_state.test_results[scenario_key]["status"]
                    if status == "in_progress":
                        st.info("🔄 Test in progress...")
                    elif status == "completed":
                        st.success("✅ Test completed!")
                    elif status == "failed":
                        st.error("❌ Test failed!")
                
                # Feedback form for completed/failed tests
                if (scenario_key in st.session_state.test_results and 
                    st.session_state.test_results[scenario_key]["status"] in ["completed", "failed"]):
                    
                    with st.form(f"feedback_{scenario_key}"):
                        st.markdown("#### 📝 Test Feedback")
                        
                        # Usability rating
                        usability_rating = st.select_slider(
                            "How easy was this functionality to use?",
                            options=[1, 2, 3, 4, 5],
                            value=3,
                            format_func=lambda x: f"{x} - {'Very Hard' if x==1 else 'Hard' if x==2 else 'Neutral' if x==3 else 'Easy' if x==4 else 'Very Easy'}"
                        )
                        
                        # Performance rating
                        performance_rating = st.select_slider(
                            "How well did the functionality perform?",
                            options=[1, 2, 3, 4, 5],
                            value=3,
                            format_func=lambda x: f"{x} - {'Very Poor' if x==1 else 'Poor' if x==2 else 'Neutral' if x==3 else 'Good' if x==4 else 'Excellent'}"
                        )
                        
                        # Issues encountered
                        issues = st.text_area(
                            "Issues or bugs encountered:",
                            placeholder="Describe any problems you encountered..."
                        )
                        
                        # Suggestions
                        suggestions = st.text_area(
                            "Suggestions for improvement:",
                            placeholder="How could this functionality be improved?"
                        )
                        
                        # Overall comments
                        comments = st.text_area(
                            "Additional comments:",
                            placeholder="Any other feedback or observations..."
                        )
                        
                        # Submit feedback
                        if st.form_submit_button("Submit Feedback"):
                            st.session_state.feedback_data[scenario_key] = {
                                "scenario_name": scenario["name"],
                                "usability_rating": usability_rating,
                                "performance_rating": performance_rating,
                                "issues": issues,
                                "suggestions": suggestions,
                                "comments": comments,
                                "timestamp": datetime.now().isoformat()
                            }
                            st.success("Feedback submitted! Thank you!")
                
                st.markdown("---")
    
    # Test summary and feedback export
    st.subheader("📊 Test Summary & Export")
    
    if st.session_state.test_results:
        # Test results summary
        total_tests = len(st.session_state.test_results)
        completed_tests = sum(1 for result in st.session_state.test_results.values() if result["status"] == "completed")
        failed_tests = sum(1 for result in st.session_state.test_results.values() if result["status"] == "failed")
        in_progress_tests = sum(1 for result in st.session_state.test_results.values() if result["status"] == "in_progress")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Tests", total_tests)
        col2.metric("Completed", completed_tests)
        col3.metric("Failed", failed_tests)
        col4.metric("In Progress", in_progress_tests)
        
        # Feedback summary
        if st.session_state.feedback_data:
            st.markdown("### 📈 Feedback Summary")
            
            feedback_list = list(st.session_state.feedback_data.values())
            avg_usability = sum(f["usability_rating"] for f in feedback_list) / len(feedback_list)
            avg_performance = sum(f["performance_rating"] for f in feedback_list) / len(feedback_list)
            
            col1, col2 = st.columns(2)
            col1.metric("Average Usability Rating", f"{avg_usability:.1f}/5")
            col2.metric("Average Performance Rating", f"{avg_performance:.1f}/5")
            
            # Export feedback
            if st.button("📥 Export Test Results & Feedback"):
                export_data = {
                    "test_results": st.session_state.test_results,
                    "feedback_data": st.session_state.feedback_data,
                    "summary": {
                        "total_tests": total_tests,
                        "completed_tests": completed_tests,
                        "failed_tests": failed_tests,
                        "average_usability_rating": avg_usability,
                        "average_performance_rating": avg_performance,
                        "export_timestamp": datetime.now().isoformat()
                    }
                }
                
                st.download_button(
                    label="Download JSON Report",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"array_field_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        # Clear all data button
        if st.button("🗑️ Clear All Test Data"):
            st.session_state.test_results = {}
            st.session_state.feedback_data = {}
            st.success("All test data cleared!")
            st.rerun()
    
    else:
        st.info("No test results yet. Start a test scenario above to begin collecting data.")
    
    # Instructions section
    st.subheader("📖 Testing Instructions")
    
    st.markdown("""
    ### How to Use This Testing Interface
    
    1. **Select a Test Category**: Choose from Insurance Document, Purchase Order, or Schema Creation tests
    2. **Read the Scenario**: Each test scenario has a description and expected result
    3. **Follow the Steps**: Execute the test steps in the specified order
    4. **Mark Progress**: Use the buttons to track test status (Start → Complete/Failed)
    5. **Provide Feedback**: Fill out the feedback form for completed tests
    6. **Export Results**: Download a comprehensive report of all test results and feedback
    
    ### What to Look For
    
    - **Usability**: How intuitive and easy to use is the interface?
    - **Performance**: How responsive and reliable is the functionality?
    - **Validation**: Do error messages help users understand and fix issues?
    - **Edge Cases**: How well does the system handle unusual or invalid input?
    - **Visual Design**: Is the interface clear and well-organized?
    
    ### Reporting Issues
    
    When you encounter issues:
    1. Note the exact steps that led to the problem
    2. Describe what you expected vs. what actually happened
    3. Include any error messages or unexpected behavior
    4. Suggest how the issue could be resolved or prevented
    
    Your feedback is valuable for improving the array field functionality before integration into the main application!
    """)
    
    # Quick feedback section
    st.subheader("💬 Quick Feedback")
    
    with st.form("quick_feedback"):
        st.markdown("Have general feedback about the array field functionality?")
        
        overall_impression = st.selectbox(
            "Overall impression of array field support:",
            ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
        )
        
        most_useful_feature = st.text_input(
            "Most useful feature:",
            placeholder="What feature did you find most helpful?"
        )
        
        biggest_concern = st.text_input(
            "Biggest concern or issue:",
            placeholder="What is your main concern about this functionality?"
        )
        
        general_comments = st.text_area(
            "General comments:",
            placeholder="Any other thoughts or observations..."
        )
        
        if st.form_submit_button("Submit Quick Feedback"):
            quick_feedback = {
                "overall_impression": overall_impression,
                "most_useful_feature": most_useful_feature,
                "biggest_concern": biggest_concern,
                "general_comments": general_comments,
                "timestamp": datetime.now().isoformat()
            }
            
            if "quick_feedback" not in st.session_state:
                st.session_state.quick_feedback = []
            st.session_state.quick_feedback.append(quick_feedback)
            
            st.success("Quick feedback submitted! Thank you!")
            
            # Show download option for quick feedback
            if st.session_state.quick_feedback:
                st.download_button(
                    label="Download Quick Feedback",
                    data=json.dumps(st.session_state.quick_feedback, indent=2),
                    file_name=f"quick_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

if __name__ == "__main__":
    main()
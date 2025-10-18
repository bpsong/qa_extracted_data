"""
Array Field Support Sandbox Application

This standalone Streamlit application provides a testing environment for array field functionality
before integration into the main codebase. It includes test scenarios for both scalar arrays
and object arrays with comprehensive validation and user feedback collection.
"""
# pyright: reportArgumentType=false
# type: ignore

import streamlit as st
import yaml
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, MutableMapping, cast
from datetime import datetime, date
import copy
import logging

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.schema_editor_view import (  # noqa: E402
    SchemaEditor,
    list_schema_files as production_list_schema_files,
    validate_schema_structure as production_validate_schema_structure,
)

# Logger aligned with production utilities for consistent diagnostics
logger = logging.getLogger(__name__)

# Fallback session state used when Streamlit's real session_state is unavailable (e.g., unit tests)
_FAKE_STREAMLIT_SESSION: Dict[str, Any] = {}


def _get_session_state() -> MutableMapping[str, Any]:
    """
    Retrieve the active Streamlit session_state or a deterministic fallback for tests.
    
    Streamlit raises a RuntimeError when session_state is accessed outside an active app
    context (as happens in unit tests). This helper aligns sandbox behaviour with production
    code paths by providing a shared mutable mapping in that scenario.
    """
    try:
        return cast(MutableMapping[str, Any], st.session_state)
    except RuntimeError:
        return _FAKE_STREAMLIT_SESSION


class SandboxSessionManager:
    """
    Minimal session manager that mirrors the production SessionManager contract for array editors.
    
    The real application persists form data, original data, and validation errors in Streamlit's
    session state via dedicated helpers. The sandbox needs the same behaviour so experiments here
    accurately reflect production side-effects.
    """

    FORM_DATA_KEY = "_sandbox_form_data"
    ORIGINAL_DATA_KEY = "_sandbox_original_data"
    VALIDATION_ERRORS_KEY = "_sandbox_validation_errors"

    @classmethod
    def _ensure_defaults(cls) -> None:
        state = _get_session_state()
        state.setdefault(cls.FORM_DATA_KEY, {})
        state.setdefault(cls.ORIGINAL_DATA_KEY, {})
        state.setdefault(cls.VALIDATION_ERRORS_KEY, [])
        _FAKE_STREAMLIT_SESSION.setdefault(cls.FORM_DATA_KEY, {})
        _FAKE_STREAMLIT_SESSION.setdefault(cls.ORIGINAL_DATA_KEY, {})
        _FAKE_STREAMLIT_SESSION.setdefault(cls.VALIDATION_ERRORS_KEY, [])

    @classmethod
    def get_form_data(cls) -> Dict[str, Any]:
        cls._ensure_defaults()
        state = _get_session_state()
        try:
            return state[cls.FORM_DATA_KEY]
        except Exception:
            return _FAKE_STREAMLIT_SESSION[cls.FORM_DATA_KEY]

    @classmethod
    def set_form_data(cls, data: Dict[str, Any]) -> None:
        cls._ensure_defaults()
        state = _get_session_state()
        state[cls.FORM_DATA_KEY] = data
        _FAKE_STREAMLIT_SESSION[cls.FORM_DATA_KEY] = copy.deepcopy(data)

    @classmethod
    def update_form_field(cls, field_name: str, value: Any) -> None:
        form_data = cls.get_form_data().copy()
        form_data[field_name] = value
        cls.set_form_data(form_data)

    @classmethod
    def get_original_data(cls) -> Dict[str, Any]:
        cls._ensure_defaults()
        return _get_session_state()[cls.ORIGINAL_DATA_KEY]

    @classmethod
    def set_original_data(cls, data: Dict[str, Any]) -> None:
        cls._ensure_defaults()
        state = _get_session_state()
        state[cls.ORIGINAL_DATA_KEY] = data
        _FAKE_STREAMLIT_SESSION[cls.ORIGINAL_DATA_KEY] = copy.deepcopy(data)

    @classmethod
    def get_validation_errors(cls) -> List[str]:
        cls._ensure_defaults()
        state = _get_session_state()
        try:
            return state[cls.VALIDATION_ERRORS_KEY]
        except Exception:
            return _FAKE_STREAMLIT_SESSION[cls.VALIDATION_ERRORS_KEY]

    @classmethod
    def set_validation_errors(cls, errors: List[str]) -> None:
        cls._ensure_defaults()
        state = _get_session_state()
        state[cls.VALIDATION_ERRORS_KEY] = errors
        _FAKE_STREAMLIT_SESSION[cls.VALIDATION_ERRORS_KEY] = list(errors)

    @classmethod
    def clear_validation_errors(cls) -> None:
        cls.set_validation_errors([])

    @classmethod
    def sync_array_field(cls, field_name: str, array_value: List[Any]) -> None:
        """
        Mirror production array synchronisation by persisting values under both `field_*`
        and `scalar_array_*` keys and keeping the sandbox form data in sync.
        """
        state = _get_session_state()
        state[f"field_{field_name}"] = array_value
        state[f"scalar_array_{field_name}_size"] = len(array_value)
        _FAKE_STREAMLIT_SESSION[f"field_{field_name}"] = copy.deepcopy(array_value)
        _FAKE_STREAMLIT_SESSION[f"scalar_array_{field_name}_size"] = len(array_value)
        cls.update_form_field(field_name, array_value)
        logger.debug("[SandboxSessionManager] Synced %s with %d items", field_name, len(array_value))

    @classmethod
    def reset(cls) -> None:
        """
        Reset sandbox-specific session keys. Useful for unit tests to start from a clean slate.
        """
        state = _get_session_state()
        cls.set_form_data({})
        cls.set_original_data({})
        cls.clear_validation_errors()
        removable_keys = [
            key for key in list(state.keys())
            if key.startswith("field_") or key.startswith("scalar_array_") or key.startswith("object_array_")
        ]
        for key in removable_keys:
            state.pop(key, None)
        fallback_keys = [
            key for key in list(_FAKE_STREAMLIT_SESSION.keys())
            if key.startswith("field_") or key.startswith("scalar_array_") or key.startswith("object_array_")
        ]
        for key in fallback_keys:
            _FAKE_STREAMLIT_SESSION.pop(key, None)

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
    """Render scalar array editor testing page with production-like form semantics."""
    st.header("Scalar Array Editor Testing")
    st.markdown("Test editing arrays of scalar values with add/remove functionality")

    schema_choice = st.selectbox(
        "Select Test Schema",
        ["insurance_document"],
        format_func=lambda x: test_schemas[x]["title"]
    )

    schema = test_schemas[schema_choice]
    data = copy.deepcopy(test_data[schema_choice])

    state = _get_session_state()

    if f"array_data_{schema_choice}" not in st.session_state:
        st.session_state[f"array_data_{schema_choice}"] = copy.deepcopy(data)

    current_data = st.session_state[f"array_data_{schema_choice}"]

    st.subheader("Original Test Data")
    st.json(data)

    array_fields = {
        field_name: field_config
        for field_name, field_config in schema["fields"].items()
        if field_config.get("type") == "array" and field_config.get("items", {}).get("type") != "object"
    }

    if not array_fields:
        st.warning("No scalar array fields found in selected schema")
        return

    form_init_key = f"scalar_form_initialized_{schema_choice}"
    if not state.get(form_init_key):
        SandboxSessionManager.set_form_data(copy.deepcopy(current_data))
        state[form_init_key] = True
    else:
        form_snapshot = SandboxSessionManager.get_form_data()
        for field_name in array_fields:
            if field_name in form_snapshot:
                current_data[field_name] = form_snapshot[field_name]
        st.session_state[f"array_data_{schema_choice}"] = current_data

    st.subheader("Array Field Editors")

    with st.form(f"scalar_array_form_{schema_choice}", clear_on_submit=False):
        updated_values: Dict[str, List[Any]] = {}
        for field_name, field_config in array_fields.items():
            st.markdown(f"### {field_config.get('label', field_name)}")
            st.caption(field_config.get('help', 'No description provided.'))
            current_array = current_data.get(field_name, [])
            updated_values[field_name] = render_scalar_array_editor(field_name, field_config, current_array)

        commit = st.form_submit_button("Sync scalar array changes", type="primary")

    if commit:
        for field_name, value in updated_values.items():
            current_data[field_name] = value
        st.session_state[f"array_data_{schema_choice}"] = current_data
        SandboxSessionManager.set_form_data(copy.deepcopy(current_data))
        st.success("Scalar array values synchronized with sandbox state.")
        st.rerun()

    st.subheader("Updated Data")
    st.json(current_data)

    if st.button("Reset to Original Data"):
        SandboxSessionManager.reset()
        st.session_state[f"array_data_{schema_choice}"] = copy.deepcopy(data)
        state.pop(form_init_key, None)
        st.rerun()


def render_schema_editor_page() -> None:
    """Render the production Schema Editor experience inside the sandbox."""

    st.header("Schema Editor (Sandbox Parity Mode)")
    st.caption(
        "This view embeds the production Schema Editor controller so every workflow "
        "(file management, editor, validation) behaves identically before promoting changes."
    )

    # Flag the session so downstream components can adapt messaging if needed.
    st.session_state.setdefault("schema_editor_environment", "sandbox")

    # Delegate to the production controller. All state management, error handling,
    # and UI rendering is owned by SchemaEditor.render(), which guarantees parity
    # with the live application.
    SchemaEditor.render()


def render_validation_page(test_schemas: Dict[str, Dict[str, Any]], test_data: Dict[str, Dict[str, Any]]) -> None:
    """Expose the production schema validation helpers for parity testing."""

    st.header("Validation Testing (Sandbox Parity Mode)")
    st.caption(
        "Run the same schema validation engine that powers production to verify sandbox "
        "changes before rollout."
    )

    schema_files = production_list_schema_files()
    if not schema_files:
        st.info("No schema files available. Create or import a schema from the Schema Editor first.")
        return

    file_lookup = {info["filename"]: info for info in schema_files}
    selected_filename = st.selectbox(
        "Schema file",
        options=list(file_lookup.keys()),
        format_func=lambda name: f"{name} ({'valid' if file_lookup[name]['is_valid'] else 'invalid'})",
    )

    selected_info = file_lookup[selected_filename]
    with open(selected_info["path"], "r", encoding="utf-8") as handle:
        raw_contents = handle.read()

    st.subheader("Schema Preview")
    st.code(raw_contents, language="yaml")

    schema_dict = yaml.safe_load(raw_contents) if raw_contents.strip() else {}

    st.subheader("Validation Results")
    is_valid, validation_errors = production_validate_schema_structure(schema_dict)

    if is_valid:
        st.success("✅ Schema passed structural validation.")
    else:
        st.error("❌ Schema failed validation. Review the issues below.")
        for idx, message in enumerate(validation_errors, start=1):
            st.write(f"{idx}. {message}")

    st.markdown("---")
    st.subheader("Quick Test Data")
    st.caption(
        "Load representative sandbox data to spot-check downstream validators that use this schema."
    )

    schema_key = selected_filename.replace(".yaml", "")
    sample_data = test_data.get(schema_key, {})
    if sample_data:
        st.json(sample_data)
    else:
        st.info("No sandbox fixture data found for this schema filename.")


def render_object_array_page(test_schemas: Dict, test_data: Dict):
    """Render object array editor testing page with production-like behaviour."""
    st.header("Object Array Editor Testing")
    st.markdown("Test editing arrays of objects using table-style interface")

    schema_choice = st.selectbox(
        "Select Test Schema",
        ["purchase_order"],
        format_func=lambda x: test_schemas[x]["title"]
    )

    schema = test_schemas[schema_choice]
    data = copy.deepcopy(test_data[schema_choice])
    state = _get_session_state()

    if f"object_array_data_{schema_choice}" not in st.session_state:
        st.session_state[f"object_array_data_{schema_choice}"] = copy.deepcopy(data)

    current_data = st.session_state[f"object_array_data_{schema_choice}"]

    st.subheader("Original Test Data")
    st.json(data)

    object_array_fields = {
        field_name: field_config
        for field_name, field_config in schema["fields"].items()
        if field_config.get("type") == "array" and field_config.get("items", {}).get("type") == "object"
    }

    if not object_array_fields:
        st.warning("No object array fields found in selected schema")
        return

    form_init_key = f"object_form_initialized_{schema_choice}"
    if not state.get(form_init_key):
        SandboxSessionManager.set_form_data(copy.deepcopy(current_data))
        state[form_init_key] = True
    else:
        form_snapshot = SandboxSessionManager.get_form_data()
        for field_name in object_array_fields:
            if field_name in form_snapshot:
                current_data[field_name] = form_snapshot[field_name]
        st.session_state[f"object_array_data_{schema_choice}"] = current_data

    st.subheader("Object Array Field Editors")

    with st.form(f"object_array_form_{schema_choice}", clear_on_submit=False):
        updated_values: Dict[str, List[Dict[str, Any]]] = {}
        for field_name, field_config in object_array_fields.items():
            st.markdown(f"### {field_config.get('label', field_name)}")
            st.caption(field_config.get('help', 'No description provided.'))
            current_array = current_data.get(field_name, [])
            updated_values[field_name] = render_object_array_editor(field_name, field_config, current_array)

        commit = st.form_submit_button("Sync object array changes", type="primary")

    if commit:
        for field_name, value in updated_values.items():
            current_data[field_name] = value
        st.session_state[f"object_array_data_{schema_choice}"] = current_data
        SandboxSessionManager.set_form_data(copy.deepcopy(current_data))
        st.success("Object array values synchronized with sandbox state.")
        st.rerun()

    st.subheader("Updated Data")
    st.json(current_data)

    if st.button("Reset to Original Data"):
        SandboxSessionManager.reset()
        st.session_state[f"object_array_data_{schema_choice}"] = copy.deepcopy(data)
        state.pop(form_init_key, None)
        st.rerun()

def render_scalar_array_editor(field_name: str, field_config: Dict[str, Any], current_value: List[Any]) -> List[Any]:
    """
    Production-aligned editor for arrays of scalar values.

    This implementation mirrors the production form generator so sandbox experiments share
    the same state management semantics and validation flow.
    """
    items_config = field_config.get("items", {})
    item_type = items_config.get("type", "string")

    # Always work on a shallow copy to avoid mutating caller state in-place
    working_array = list(current_value or [])

    field_key = f"scalar_array_{field_name}"
    action_key = f"{field_key}_action"
    target_index_key = f"{field_key}_target_index"
    size_key = f"{field_key}_size"

    state = _get_session_state()
    if size_key not in state:
        state[size_key] = len(working_array)

    # Sync initial data so downstream validators and collectors see the same values
    SandboxSessionManager.sync_array_field(field_name, working_array)

    with st.container():
        st.markdown(f"**{field_config.get('label', field_name)}** ({item_type} array)")
        st.caption(
            "Edit values below. Use the array action controls to add or remove items, "
            "then apply the change to update the working list."
        )

        action_choices = [
            ("none", "-- Select action --"),
            ("add", "Add new item"),
            ("remove", "Remove selected item"),
        ]
        action_lookup = {value: label for value, label in action_choices}
        action_values = [value for value, _ in action_choices]

        def format_action_choice(choice: str) -> str:
            return action_lookup.get(choice, str(choice))

        selected_action = st.selectbox(
            "Array action",
            options=action_values,
            format_func=format_action_choice,
            key=action_key,
            help="Choose an action to apply to this array",
        )

        target_index = None
        requires_index = selected_action in {"remove"}
        if requires_index and working_array:
            target_index = st.selectbox(
                "Target item",
                options=list(range(len(working_array))),
                format_func=lambda idx: f"Index {idx}: {working_array[idx]!r}",
                key=target_index_key,
                help="Select which item the action should target",
            )
        elif requires_index:
            if target_index_key in state:
                del state[target_index_key]
            st.info("No items available for the selected action.")
        elif target_index_key in state:
            del state[target_index_key]

        apply_action = st.form_submit_button(
            f"Apply to {field_config.get('label', field_name)}",
            key=f"{field_key}_apply_action",
            help="Submit the selected array action",
        )

        if apply_action:
            action_performed = False

            if selected_action == "add":
                default_value = get_default_value_for_type(item_type, items_config)
                working_array.append(default_value)
                state[size_key] = len(working_array)
                st.success(f"Added new item at index {len(working_array) - 1}")
                action_performed = True
            elif selected_action == "remove":
                if working_array and target_index is not None:
                    removed_value = working_array.pop(target_index)
                    state[size_key] = len(working_array)
                    st.success(f"Removed item {target_index}: {removed_value!r}")
                    action_performed = True
                else:
                    st.warning("Select an item to remove before applying.")
            else:
                st.info("Select an action before applying.")

            if action_performed:
                SandboxSessionManager.sync_array_field(field_name, working_array)
                st.rerun()

        for index in range(len(working_array)):
            new_value = render_scalar_input(
                f"{field_name}[{index}]",
                item_type,
                working_array[index],
                items_config,
                key=f"{field_key}_item_{index}",
            )
            if new_value != working_array[index]:
                working_array[index] = new_value
                SandboxSessionManager.sync_array_field(field_name, working_array)
            else:
                working_array[index] = new_value

        validation_errors = validate_scalar_array(field_name, working_array, items_config)
        if validation_errors:
            for error in validation_errors:
                st.error(error)
                logger.debug("[ScalarArrayEditor] %s validation error: %s", field_name, error)
        elif working_array:
            st.success(f"{len(working_array)} items valid")

    SandboxSessionManager.sync_array_field(field_name, working_array)
    return working_array


def get_default_value_for_type(item_type: str, items_config: Dict[str, Any]) -> Any:
    """Get appropriate default value for array item type, respecting constraints."""
    if item_type == "string":
        return ""
    elif item_type == "number":
        min_val = items_config.get("min_value")
        if min_val is not None:
            return max(0.0, float(min_val)) if min_val >= 0 else float(min_val)
        return 0.0
    elif item_type == "integer":
        min_val = items_config.get("min_value")
        if min_val is not None:
            return max(0, int(min_val)) if min_val >= 0 else int(min_val)
        return 0
    elif item_type == "boolean":
        return items_config.get("default", False)
    elif item_type == "date":
        return datetime.now().strftime("%Y-%m-%d")
    elif item_type == "enum":
        choices = items_config.get("choices", [])
        return items_config.get("default", choices[0] if choices else "")
    else:
        return ""


def render_scalar_input(field_name: str, item_type: str, current_value: Any, items_config: Dict[str, Any], key: str) -> Any:
    """Render appropriate input widget for scalar array item with enum support."""

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
            format="%.2f",
            key=key,
            help=f"Number value for {field_name}"
        )
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
            format="%d",
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
                from dateutil import parser
                current_date = parser.parse(current_value).date()
            elif isinstance(current_value, datetime):
                current_date = current_value.date()
            elif isinstance(current_value, date):
                current_date = current_value
            else:
                current_date = datetime.now().date()
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse date value '{current_value}': {e}")
            current_date = datetime.now().date()

        value = st.date_input(
            f"Item {key.split('_')[-1]}",
            value=current_date,
            key=key,
            help=f"Date value for {field_name}"
        )
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        logger.warning("date_input returned non-date value: %s", type(value))
        return str(value) if value is not None else ""

    elif item_type == "enum":
        choices = items_config.get("choices", [])
        if not choices:
            return st.text_input(
                f"Item {key.split('_')[-1]}",
                value=str(current_value) if current_value is not None else "",
                key=key,
                help=f"Enum value for {field_name}"
            )

        try:
            current_index = choices.index(current_value) if current_value in choices else 0
        except (ValueError, TypeError):
            current_index = 0

        value = st.selectbox(
            f"Item {key.split('_')[-1]}",
            choices,
            index=current_index,
            key=key,
            help=f"Select value for {field_name}"
        )
        return value

    else:
        value = st.text_input(
            f"Item {key.split('_')[-1]}",
            value=str(current_value) if current_value is not None else "",
            key=key,
            help=f"Value for {field_name}"
        )
        return value


def validate_scalar_array(field_name: str, array_value: List[Any], items_config: Dict[str, Any]) -> List[str]:
    """Validate an array of scalar values using production-equivalent rules."""
    errors = []

    if not isinstance(array_value, list):
        errors.append(f"{field_name} must be an array")
        return errors

    item_type = items_config.get("type", "string")

    for index, item_value in enumerate(array_value):
        item_errors = validate_scalar_item(f"{field_name}[{index}]", item_value, item_type, items_config)
        errors.extend(item_errors)

    return errors


def validate_scalar_item(field_path: str, value: Any, item_type: str, items_config: Dict[str, Any]) -> List[str]:
    """Validate a single scalar value with detailed error reporting."""
    errors = []

    if item_type == "string":
        if not isinstance(value, str):
            errors.append(f"{field_path} must be a string")
            return errors

        min_length = items_config.get("min_length")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{field_path} must be at least {min_length} characters")

        max_length = items_config.get("max_length")
        if max_length is not None and len(value) > max_length:
            errors.append(f"{field_path} must be no more than {max_length} characters")

        pattern = items_config.get("pattern")
        if pattern:
            import re
            try:
                if not re.match(pattern, value):
                    errors.append(f"{field_path} must match pattern: {pattern}")
            except re.error:
                errors.append(f"{field_path} has invalid pattern: {pattern}")

    elif item_type == "number":
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            errors.append(f"{field_path} must be a valid number")
            return errors

        min_value = items_config.get("min_value")
        if min_value is not None and numeric_value < min_value:
            errors.append(f"{field_path} must be at least {min_value}")

        max_value = items_config.get("max_value")
        if max_value is not None and numeric_value > max_value:
            errors.append(f"{field_path} must be no more than {max_value}")

    elif item_type == "integer":
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            errors.append(f"{field_path} must be a valid integer")
            return errors

        min_value = items_config.get("min_value")
        if min_value is not None and int_value < min_value:
            errors.append(f"{field_path} must be at least {min_value}")

        max_value = items_config.get("max_value")
        if max_value is not None and int_value > max_value:
            errors.append(f"{field_path} must be no more than {max_value}")

    elif item_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{field_path} must be a boolean")

    elif item_type == "date":
        if isinstance(value, str):
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                errors.append(f"{field_path} must be a valid date in YYYY-MM-DD format")
        elif not isinstance(value, date):
            errors.append(f"{field_path} must be a valid date")

    elif item_type == "enum":
        choices = items_config.get("choices", [])
        if choices and value not in choices:
            allowed = ", ".join(map(str, choices))
            errors.append(f"{field_path} must be one of: {allowed}")

    return errors


def render_object_array_editor(field_name: str, field_config: Dict[str, Any], current_value: List[Dict]) -> List[Dict]:
    """Production-aligned editor for arrays of objects using Streamlit's data_editor."""
    import pandas as pd

    items_config = field_config.get("items", {})
    properties = items_config.get("properties", {})

    working_array = list(current_value or [])
    column_config = generate_column_config(properties)

    SandboxSessionManager.sync_array_field(field_name, working_array)

    with st.container():
        st.info("How to edit: Click cells to edit values directly in the table. Use 'Add Row' to add new items. Use the row deletion section below to remove rows.")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{field_config.get('label', field_name)}**")

        with col2:
            if st.button("Add Row", key=f"add_row_{field_name}"):
                new_object = create_default_object(properties)
                working_array.append(new_object)
                SandboxSessionManager.sync_array_field(field_name, working_array)
                st.rerun()

        if working_array:
            df = pd.DataFrame(working_array)

            edited_df = st.data_editor(
                df,
                column_config=column_config,
                num_rows="dynamic",
                use_container_width=True,
                key=f"data_editor_{field_name}",
                hide_index=False
            )

            working_array = edited_df.to_dict('records')
            working_array = clean_object_array(working_array)
            SandboxSessionManager.sync_array_field(field_name, working_array)

            if len(working_array) > 0:
                st.markdown("#### Manual Row Operations")
                col1, col2 = st.columns([2, 1])

                with col1:
                    def _format_row(idx: int) -> str:
                        row = working_array[idx]
                        first_key = next(iter(row.keys()), "N/A") if row else "N/A"
                        first_value = row.get(first_key, "N/A") if row else "Empty"
                        return f"Row {idx}: {first_value}"

                    row_to_delete = st.selectbox(
                        "Select row to delete:",
                        options=list(range(len(working_array))),
                        format_func=_format_row,
                        key=f"delete_row_select_{field_name}"
                    )

                with col2:
                    if st.button("Delete Selected Row", key=f"delete_row_{field_name}"):
                        if 0 <= row_to_delete < len(working_array):
                            working_array.pop(row_to_delete)
                            SandboxSessionManager.sync_array_field(field_name, working_array)
                            st.success(f"Deleted row {row_to_delete}")
                            st.rerun()
        else:
            st.info("No items in array. Click 'Add Row' to add the first item.")

        validation_errors = validate_object_array(field_name, working_array, items_config)
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        elif working_array:
            st.success(f"{len(working_array)} objects valid")

    SandboxSessionManager.sync_array_field(field_name, working_array)
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
    
    state = _get_session_state()

    # Initialize the selected type in session state
    if "scalar_array_item_type" not in state:
        state["scalar_array_item_type"] = "string"
    
    # Use session state to track the current selection
    current_selection = st.selectbox(
        "Item Type",
        ["string", "number", "integer", "boolean", "date", "enum"],
        index=["string", "number", "integer", "boolean", "date", "enum"].index(state["scalar_array_item_type"]),  # type: ignore[arg-type]
        help="Type of values in the array",
        key="scalar_type_selectbox"
    )
    
    # Update session state and detect changes
    type_changed = state["scalar_array_item_type"] != current_selection  # type: ignore[index]
    if type_changed:
        state["scalar_array_item_type"] = current_selection
    
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
                config["min_length"] = int(min_length)
        
        with col2:
            max_length = st.number_input("Max Length", min_value=1, value=100, step=1, key="string_max_len")
            config["max_length"] = int(max_length)
        
        pattern = st.text_input("Pattern (regex)", placeholder="e.g., ^[A-Z0-9]+$", key="string_pattern")
        if pattern:
            config["pattern"] = pattern
    
    elif item_type == "number":
        st.markdown("#### Number Constraints")
        # st.write("🐛 DEBUG: Showing NUMBER constraint widgets")
        col1, col2 = st.columns(2)
        with col1:
            min_value = st.number_input("Min Value", value=0.0, key="number_min", format="%.2f")
            config["min_value"] = round(min_value, 2)
        
        with col2:
            max_value = st.number_input("Max Value", value=1000.0, key="number_max", format="%.2f")
            config["max_value"] = round(max_value, 2)
        
        # Validation: Check if min > max
        if min_value > max_value:
            st.error(f"⚠️ Min Value ({min_value:.2f}) cannot be greater than Max Value ({max_value:.2f})")
        
        step = st.number_input("Step", min_value=0.01, value=0.01, step=0.01, key="number_step", format="%.2f")
        config["step"] = round(step, 2)
    
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
        
        # Validation: Check if min > max
        if int(min_value) > int(max_value):
            st.error(f"⚠️ Min Value ({int(min_value)}) cannot be greater than Max Value ({int(max_value)})")
        
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
            config["choices"] = str(choices)
        else:
            st.warning("Please provide at least one choice for enum type")
    
    return config


def render_object_array_config() -> Dict[str, Any]:
    """Render configuration interface for object array fields."""
    st.markdown("#### Object Properties")

    state = _get_session_state()
    props_key = "temp_object_properties_schema_editor"
    properties_state = cast(Dict[str, Dict[str, Any]], state.setdefault(props_key, {}))
    counter = int(state.setdefault("obj_prop_counter", 0))

    with st.expander("? Add New Property", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            prop_name = st.text_input("Property Name", placeholder="e.g., item_code", key=f"obj_prop_name_{counter}")
            prop_label = st.text_input("Property Label", placeholder="e.g., Item Code", key=f"obj_prop_label_{counter}")
            prop_required = st.checkbox("Required Property", key=f"obj_prop_required_{counter}")

        with col2:
            prop_type = st.selectbox(
                "Property Type",
                ["string", "number", "integer", "boolean", "date", "enum"],
                key=f"obj_prop_type_select_{counter}",
            )
            prop_help = st.text_input(
                "Help Text",
                placeholder="Description of this property",
                key=f"obj_prop_help_{counter}",
            )

        prop_config: Dict[str, Any] = {
            "type": prop_type,
            "label": prop_label or prop_name,
            "required": prop_required,
        }
        if prop_help:
            prop_config["help"] = prop_help

        if prop_type == "string":
            st.markdown("**String Constraints**")
            col1, col2 = st.columns(2)
            with col1:
                min_len = st.number_input(
                    "Min Length", min_value=0, value=0, step=1, key=f"obj_prop_min_len_{counter}"
                )
                if min_len > 0:
                    prop_config["min_length"] = str(min_len)
            with col2:
                max_len = st.number_input(
                    "Max Length", min_value=1, value=100, step=1, key=f"obj_prop_max_len_{counter}"
                )
                prop_config["max_length"] = str(max_len)
            pattern = st.text_input(
                "Pattern (regex)",
                key=f"obj_prop_pattern_{counter}",
                placeholder="e.g., ^[A-Z0-9]+$",
            )
            if pattern:
                prop_config["pattern"] = pattern

        elif prop_type == "number":
            st.markdown("**Number Constraints**")
            col1, col2 = st.columns(2)
            with col1:
                min_val = st.number_input(
                    "Min Value", value=0.0, key=f"obj_prop_min_val_{counter}", format="%.2f"
                )
                prop_config["min_value"] = str(round(min_val, 2))
            with col2:
                max_val = st.number_input(
                    "Max Value", value=1000.0, key=f"obj_prop_max_val_{counter}", format="%.2f"
                )
                prop_config["max_value"] = str(round(max_val, 2))
            if min_val > max_val:
                st.error(f"?? Min Value ({min_val:.2f}) cannot be greater than Max Value ({max_val:.2f})")
            step_val = st.number_input(
                "Step",
                min_value=0.01,
                value=0.01,
                step=0.01,
                key=f"obj_prop_step_{counter}",
                format="%.2f",
            )
            prop_config["step"] = str(round(step_val, 2))

        elif prop_type == "integer":
            st.markdown("**Integer Constraints**")
            col1, col2 = st.columns(2)
            with col1:
                min_val = st.number_input(
                    "Min Value", value=0, step=1, key=f"obj_prop_min_val_int_{counter}"
                )
                prop_config["min_value"] = str(int(min_val))
            with col2:
                max_val = st.number_input(
                    "Max Value", value=1000, step=1, key=f"obj_prop_max_val_int_{counter}"
                )
                prop_config["max_value"] = str(int(max_val))
            if int(min_val) > int(max_val):
                st.error(f"?? Min Value ({int(min_val)}) cannot be greater than Max Value ({int(max_val)})")
            step_val = st.number_input("Step", min_value=1, value=1, step=1, key=f"obj_prop_step_int_{counter}")
            prop_config["step"] = str(int(step_val))

        elif prop_type == "boolean":
            st.markdown("**Boolean Options**")
            default_val = st.checkbox("Default Value", key=f"obj_prop_bool_default_{counter}")
            prop_config["default"] = str(default_val)

        elif prop_type == "enum":
            st.markdown("**Enum Options**")
            choices_text = st.text_area(
                "Choices (one per line)",
                placeholder="option1\noption2\noption3",
                key=f"obj_prop_enum_choices_{counter}",
            )
            if choices_text:
                choices = [choice.strip() for choice in choices_text.splitlines() if choice.strip()]
                prop_config["choices"] = str(choices)

        if st.button("Add Property", key=f"add_obj_property_btn_{counter}") and prop_name:
            if prop_name in properties_state:
                st.warning(f"Property '{prop_name}' already exists. Use a different name.")
            else:
                properties_state[prop_name] = prop_config
                state["obj_prop_counter"] = counter + 1
                st.success(f"Added property: {prop_name}")
                st.rerun()

    if properties_state:
        st.markdown("#### Current Properties")
        for prop_name, prop_config in list(properties_state.items()):
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{prop_config.get('label', prop_name)}** ({prop_config['type']})")
                    if prop_config.get("required"):
                        st.markdown("? *Required*")
                    else:
                        st.markdown("?? *Optional*")
                    if prop_config.get("help"):
                        st.markdown(f"*{prop_config['help']}*")

                    constraints = []
                    if "min_length" in prop_config:
                        constraints.append(f"min_length: {prop_config['min_length']}")
                    if "max_length" in prop_config:
                        constraints.append(f"max_length: {prop_config['max_length']}")
                    if "min_value" in prop_config:
                        constraints.append(f"min_value: {prop_config['min_value']}")
                    if "max_value" in prop_config:
                        constraints.append(f"max_value: {prop_config['max_value']}")
                    if "pattern" in prop_config:
                        constraints.append(f"pattern: {prop_config['pattern']}")
                    if "choices" in prop_config:
                        constraints.append(f"choices: {prop_config['choices']}")
                    if constraints:
                        st.markdown(f"*Constraints: {', '.join(constraints)}*")
                with col2:
                    if st.button("??? Remove", key=f"remove_obj_prop_{prop_name}"):
                        properties_state.pop(prop_name, None)
                        st.rerun()
                st.markdown("---")
    else:
        st.info("No properties added yet. Add properties using the form above.")

    if properties_state and st.button("??? Clear All Properties", key="clear_all_obj_props"):
        properties_state.clear()
        st.rerun()

    return {
        "type": "object",
        "properties": copy.deepcopy(properties_state),
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

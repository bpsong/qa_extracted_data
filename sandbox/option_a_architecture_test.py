"""
Option A Architecture Test: Widget State as Single Source of Truth

This sandbox demonstrates:
- Original data always read from JSON file
- Current data always read from widget session state keys
- No SessionManager.form_data duplication
- Validation using Pydantic models
- Diff calculation between file and widgets
- Complex form with all field types and constraints
"""

import streamlit as st
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError
import pandas as pd
from deepdiff import DeepDiff

# ============================================================================
# MOCK DATA & SCHEMA
# ============================================================================

ORIGINAL_JSON_DATA = {
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "total_amount": 1250.50,
    "customer_name": "Acme Corp",
    "is_paid": False,
    "tags": ["urgent", "wholesale"],
    "line_items": [
        {"description": "Widget A", "quantity": 10, "unit_price": 50.00, "total": 500.00},
        {"description": "Widget B", "quantity": 15, "unit_price": 50.03, "total": 750.45}
    ],
    "notes": "Net 30 payment terms"
}

SCHEMA = {
    "title": "Invoice Schema",
    "fields": {
        "invoice_number": {
            "type": "string",
            "label": "Invoice Number",
            "required": True,
            "pattern": r"^INV-\d{4}-\d{3}$"
        },
        "invoice_date": {
            "type": "date",
            "label": "Invoice Date",
            "required": True
        },
        "total_amount": {
            "type": "number",
            "label": "Total Amount",
            "required": True,
            "minimum": 0,
            "maximum": 1000000
        },
        "customer_name": {
            "type": "string",
            "label": "Customer Name",
            "required": True,
            "minLength": 2,
            "maxLength": 100
        },
        "is_paid": {
            "type": "boolean",
            "label": "Payment Status",
            "required": False
        },
        "tags": {
            "type": "array",
            "label": "Tags",
            "items": {"type": "string"},
            "required": False
        },
        "line_items": {
            "type": "array",
            "label": "Line Items",
            "required": True,
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "required": True},
                    "quantity": {"type": "integer", "required": True, "minimum": 1},
                    "unit_price": {"type": "number", "required": True, "minimum": 0},
                    "total": {"type": "number", "required": True, "minimum": 0}
                }
            }
        },
        "notes": {
            "type": "string",
            "label": "Notes",
            "required": False,
            "maxLength": 500
        }
    }
}

# ============================================================================
# PYDANTIC MODELS FOR VALIDATION
# ============================================================================

class LineItem(BaseModel):
    description: str = Field(..., min_length=3, max_length=50)
    quantity: int = Field(..., ge=1, le=1000)
    unit_price: float = Field(..., ge=0.01, le=100000)
    total: float = Field(..., ge=0)
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """Description cannot be just whitespace"""
        if not v or v.strip() == "":
            raise ValueError("Description cannot be empty or whitespace")
        return v
    
    @field_validator('total')
    @classmethod
    def validate_total(cls, v, info):
        """Validate that total = quantity * unit_price"""
        if 'quantity' in info.data and 'unit_price' in info.data:
            expected = info.data['quantity'] * info.data['unit_price']
            if abs(v - expected) > 0.01:  # Allow small floating point differences
                raise ValueError(f"Total {v} doesn't match quantity * unit_price = {expected:.2f}")
        return v

class InvoiceModel(BaseModel):
    invoice_number: str = Field(..., pattern=r"^INV-\d{4}-\d{3}$")
    invoice_date: date
    total_amount: float = Field(..., ge=0, le=1000000)
    customer_name: str = Field(..., min_length=2, max_length=100)
    is_paid: bool = False
    tags: Optional[List[str]] = Field(None, min_length=1, max_length=10)
    line_items: List[LineItem] = Field(..., min_length=1, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Each tag must be non-empty and unique"""
        if v is not None:
            # Check for empty strings
            for i, tag in enumerate(v):
                if not tag or tag.strip() == "":
                    raise ValueError(f"Tag at position {i+1} cannot be empty")
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError("Tags must be unique (no duplicates)")
        return v
    
    @model_validator(mode='after')
    def validate_total_amount(self):
        """Validate that total_amount matches sum of line items"""
        expected = sum(item.total for item in self.line_items)
        if abs(self.total_amount - expected) > 0.01:
            raise ValueError(f"Total amount {self.total_amount:.2f} doesn't match sum of line items = {expected:.2f}")
        return self

# ============================================================================
# FILE OPERATIONS
# ============================================================================

def load_original_data_from_file() -> Dict[str, Any]:
    """Always read original data fresh from file."""
    if 'json_file_path' not in st.session_state:
        # Create temp file on first run
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(ORIGINAL_JSON_DATA, temp_file, indent=2)
        temp_file.close()
        st.session_state.json_file_path = temp_file.name
    
    with open(st.session_state.json_file_path, 'r') as f:
        return json.load(f)

def save_to_file(data: Dict[str, Any]) -> None:
    """Save corrected data to file."""
    corrected_path = st.session_state.json_file_path.replace('.json', '_corrected.json')
    with open(corrected_path, 'w') as f:
        json.dump(data, f, indent=2)
    st.success(f"✅ Saved to: {corrected_path}")

# ============================================================================
# WIDGET RENDERING
# ============================================================================

def render_form_widgets(schema: Dict, initial_data: Dict) -> None:
    """Render all form widgets. Widgets manage their own state via keys."""
    
    st.subheader("📝 Edit Form")
    
    fields = schema.get('fields', {})
    
    # Get form version for reset functionality
    # When form_version changes, all widget keys change, forcing a complete re-render
    form_version = st.session_state.get('form_version', 0)
    
    # Scalar fields
    st.markdown("### Basic Information")
    
    # Invoice Number
    if 'invoice_number' in fields:
        key = f'field_invoice_number_v{form_version}'
        if key not in st.session_state:
            st.session_state[key] = initial_data.get('invoice_number', '')
        st.text_input(
            fields['invoice_number']['label'],
            key=key,
            help="Format: INV-YYYY-NNN"
        )
    
    # Invoice Date
    if 'invoice_date' in fields:
        key = f'field_invoice_date_v{form_version}'
        if key not in st.session_state:
            date_str = initial_data.get('invoice_date', '')
            st.session_state[key] = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
        st.date_input(
            fields['invoice_date']['label'],
            key=key
        )
    
    # Customer Name
    if 'customer_name' in fields:
        key = f'field_customer_name_v{form_version}'
        if key not in st.session_state:
            st.session_state[key] = initial_data.get('customer_name', '')
        st.text_input(
            fields['customer_name']['label'],
            key=key
        )
    
    # Total Amount
    if 'total_amount' in fields:
        key = f'field_total_amount_v{form_version}'
        if key not in st.session_state:
            st.session_state[key] = initial_data.get('total_amount', 0.0)
        st.number_input(
            fields['total_amount']['label'],
            key=key,
            min_value=0.0,
            max_value=1000000.0,
            format="%.2f"
        )
    
    # Is Paid (boolean)
    if 'is_paid' in fields:
        key = f'field_is_paid_v{form_version}'
        if key not in st.session_state:
            st.session_state[key] = initial_data.get('is_paid', False)
        st.checkbox(
            fields['is_paid']['label'],
            key=key
        )
    
    # Notes
    if 'notes' in fields:
        key = f'field_notes_v{form_version}'
        if key not in st.session_state:
            st.session_state[key] = initial_data.get('notes', '')
        st.text_area(
            fields['notes']['label'],
            key=key,
            max_chars=500
        )
    
    st.divider()
    
    # Array of scalars: Tags
    if 'tags' in fields:
        st.markdown("### Tags (Array of Strings)")
        render_scalar_array('tags', initial_data.get('tags', []))
    
    st.divider()
    
    # Array of objects: Line Items
    if 'line_items' in fields:
        st.markdown("### Line Items (Array of Objects)")
        render_object_array('line_items', initial_data.get('line_items', []))

def render_scalar_array(field_name: str, initial_value: List[str]) -> None:
    """Render array of scalars with add/delete buttons."""
    form_version = st.session_state.get('form_version', 0)
    key = f'array_{field_name}_v{form_version}'
    
    # Initialize if needed
    if key not in st.session_state:
        st.session_state[key] = initial_value.copy()
    
    # Display current items
    items = st.session_state[key]
    
    for i, item in enumerate(items):
        col1, col2 = st.columns([4, 1])
        with col1:
            item_key = f'{key}_item_{i}'
            if item_key not in st.session_state:
                st.session_state[item_key] = item
            st.text_input(
                f"Tag {i+1}",
                key=item_key,
                label_visibility="collapsed"
            )
        with col2:
            if st.button("🗑️", key=f'delete_{key}_{i}'):
                # Delete this item
                del st.session_state[item_key]
                items.pop(i)
                st.rerun()
    
    # Add button
    if st.button(f"➕ Add Tag", key=f'add_{key}'):
        items.append("")
        st.rerun()

def render_object_array(field_name: str, initial_value: List[Dict]) -> None:
    """Render array of objects using st.data_editor with manual add/delete buttons."""
    form_version = st.session_state.get('form_version', 0)
    array_key = f'array_{field_name}_v{form_version}'
    
    # Initialize array in session state if needed
    if array_key not in st.session_state:
        st.session_state[array_key] = initial_value.copy()
    
    # Get current items from session state
    current_items = st.session_state[array_key]
    
    # Default row for adding new items
    DEFAULT_LINE_ITEM = {
        "description": "New Item",
        "quantity": 1,
        "unit_price": 0.01,
        "total": 0.01
    }
    
    # Add/Delete buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➕ Add Line Item", key=f'add_{array_key}'):
            st.session_state[array_key].append(DEFAULT_LINE_ITEM.copy())
            st.rerun()
    with col2:
        if len(current_items) > 0:
            if st.button("🗑️ Delete Last Item", key=f'delete_{array_key}'):
                st.session_state[array_key].pop()
                st.rerun()
    
    # Render data editor (without dynamic rows to avoid conflicts)
    df = pd.DataFrame(current_items) if current_items else pd.DataFrame(columns=["description", "quantity", "unit_price", "total"])
    
    edited_df = st.data_editor(
        df,
        num_rows="fixed",  # Use manual buttons instead
        use_container_width=True,
        column_config={
            "description": st.column_config.TextColumn("Description", required=True),
            "quantity": st.column_config.NumberColumn("Quantity", min_value=1, required=True),
            "unit_price": st.column_config.NumberColumn("Unit Price", min_value=0.01, format="%.2f", required=True),
            "total": st.column_config.NumberColumn("Total", min_value=0.01, format="%.2f", required=True)
        },
        hide_index=False,
        key=f'editor_{array_key}'
    )
    
    # CRITICAL: Store edited DataFrame in a separate key for data collection
    # This is read during data collection, NOT used to update the source array
    st.session_state[f'{array_key}_current'] = edited_df

# ============================================================================
# DATA COLLECTION FROM WIDGETS
# ============================================================================

def collect_current_data_from_widgets(schema: Dict) -> Dict[str, Any]:
    """
    Collect all current values from widget session state.
    This is the ONLY source of current data - no duplication.
    """
    current_data = {}
    fields = schema.get('fields', {})
    
    # Get current form version
    form_version = st.session_state.get('form_version', 0)
    
    # Collect scalar fields
    for field_name, field_config in fields.items():
        field_type = field_config.get('type')
        
        if field_type == 'array':
            # Handle arrays separately
            continue
        
        # Read from versioned widget key
        key = f'field_{field_name}_v{form_version}'
        if key in st.session_state:
            value = st.session_state[key]
            
            # Convert date to string for JSON serialization
            if isinstance(value, date):
                value = value.isoformat()
            
            current_data[field_name] = value
    
    # Collect array of scalars
    for field_name, field_config in fields.items():
        if field_config.get('type') == 'array':
            items_config = field_config.get('items', {})
            
            if items_config.get('type') == 'string':
                # Scalar array with versioned keys
                array_key = f'array_{field_name}_v{form_version}'
                if array_key in st.session_state:
                    # Collect from individual item keys
                    items = []
                    for i in range(len(st.session_state[array_key])):
                        item_key = f'{array_key}_item_{i}'
                        if item_key in st.session_state:
                            items.append(st.session_state[item_key])
                    current_data[field_name] = items
            
            elif items_config.get('type') == 'object':
                # Object array - read from the stored edited DataFrame
                array_key = f'array_{field_name}_v{form_version}'
                current_key = f'{array_key}_current'
                
                if current_key in st.session_state:
                    # Use the edited DataFrame stored during rendering
                    edited_df = st.session_state[current_key]
                    current_data[field_name] = edited_df.to_dict('records')
                elif array_key in st.session_state:
                    # Fallback to array state if editor hasn't been rendered yet
                    current_data[field_name] = st.session_state[array_key]
    
    return current_data

# ============================================================================
# VALIDATION
# ============================================================================

def validate_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate data using Pydantic model."""
    errors = []
    
    try:
        # Convert date string back to date object for validation
        validation_data = data.copy()
        if 'invoice_date' in validation_data and isinstance(validation_data['invoice_date'], str):
            validation_data['invoice_date'] = datetime.strptime(validation_data['invoice_date'], '%Y-%m-%d').date()
        
        # Validate using Pydantic
        InvoiceModel(**validation_data)
        return True, []
    
    except ValidationError as e:
        for error in e.errors():
            field = ' -> '.join(str(x) for x in error['loc']) if error['loc'] else 'Model'
            message = error['msg']
            errors.append(f"**{field}**: {message}")
        return False, errors
    except Exception as e:
        # Catch any other errors
        errors.append(f"**Validation Error**: {str(e)}")
        return False, errors

# ============================================================================
# DIFF CALCULATION
# ============================================================================

def calculate_diff(original: Dict, current: Dict) -> Dict:
    """Calculate diff between original file data and current widget data."""
    diff = DeepDiff(original, current, ignore_order=False, report_repetition=True)
    return diff

def format_diff(diff: Dict, original: Dict, current: Dict) -> str:
    """Format diff for display."""
    if not diff:
        return "✅ **No changes detected**"
    
    output = []
    
    # Values changed
    if 'values_changed' in diff:
        output.append("### 🔄 Modified Fields")
        for path, change in diff['values_changed'].items():
            field = path.replace("root['", "").replace("']", "").replace("']['", " -> ")
            output.append(f"- **{field}**")
            output.append(f"  - Old: `{change['old_value']}`")
            output.append(f"  - New: `{change['new_value']}`")
    
    # Items added
    if 'iterable_item_added' in diff:
        output.append("### ➕ Items Added")
        for path, value in diff['iterable_item_added'].items():
            output.append(f"- {path}: `{value}`")
    
    # Items removed
    if 'iterable_item_removed' in diff:
        output.append("### ➖ Items Removed")
        for path, value in diff['iterable_item_removed'].items():
            output.append(f"- {path}: `{value}`")
    
    return "\n".join(output)

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(page_title="Option A Architecture Test", layout="wide")
    
    st.title("🧪 Option A Architecture Test")
    st.caption("Widget State as Single Source of Truth")
    
    # Load original data from file (always fresh)
    original_data = load_original_data_from_file()
    
    # Two columns: Form and Actions
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Render form widgets
        render_form_widgets(SCHEMA, original_data)
    
    with col2:
        st.subheader("🎯 Actions")
        
        # Show validation constraints
        with st.expander("📋 Validation Rules to Test", expanded=False):
            st.markdown("""
            **Scalar Fields:**
            - `invoice_number`: Must match pattern `INV-YYYY-NNN`
            - `customer_name`: 2-100 characters
            - `total_amount`: Must equal sum of line items
            
            **Array of Strings (Tags):**
            - ❌ Cannot have empty tags
            - ❌ Cannot have duplicate tags
            - Must have 1-10 tags
            
            **Array of Objects (Line Items):**
            - `description`: 3-50 chars, not just whitespace
            - `quantity`: 1-1000
            - `unit_price`: $0.01-$100,000
            - `total`: Must equal quantity × unit_price
            - Must have 1-50 line items
            
            **Try Breaking These:**
            1. Add empty tag (click Add, leave blank)
            2. Add duplicate tag (type "urgent" again)
            3. Change line item total to wrong value
            4. Set quantity to 0 or 1001
            5. Make description less than 3 chars
            6. Change total_amount to not match sum
            """)
        
        # Validate button
        if st.button("✅ Validate Data", type="primary", width='stretch'):
            current_data = collect_current_data_from_widgets(SCHEMA)
            is_valid, errors = validate_data(current_data)
            
            if is_valid:
                st.success("✅ All validations passed!")
            else:
                st.error(f"❌ {len(errors)} validation error(s)")
                for error in errors:
                    st.markdown(f"- {error}")
        
        # Reset button
        if st.button("🔄 Reset to Original", width='stretch'):
            # Increment form version to force complete re-render
            # This is necessary because Streamlit widgets persist their state
            # even after deleting session state keys
            st.session_state['form_version'] = st.session_state.get('form_version', 0) + 1
            st.success("🔄 Reset complete - form will reload from original JSON")
            st.rerun()
        
        # Submit button
        if st.button("💾 Submit Corrections", width='stretch'):
            current_data = collect_current_data_from_widgets(SCHEMA)
            is_valid, errors = validate_data(current_data)
            
            if is_valid:
                save_to_file(current_data)
            else:
                st.error("❌ Cannot submit: validation failed")
                for error in errors:
                    st.markdown(f"- {error}")
    
    # Diff section (full width)
    st.divider()
    st.subheader("🔍 Changes Preview")
    
    # Always calculate diff fresh from file vs widgets
    current_data = collect_current_data_from_widgets(SCHEMA)
    diff = calculate_diff(original_data, current_data)
    
    if diff:
        # Show metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Modified", len(diff.get('values_changed', {})))
        with col2:
            st.metric("Added", len(diff.get('iterable_item_added', {})))
        with col3:
            st.metric("Removed", len(diff.get('iterable_item_removed', {})))
        
        # Show formatted diff
        st.markdown(format_diff(diff, original_data, current_data))
    else:
        st.success("✅ No changes detected")
    
    # Debug section
    with st.expander("🐛 Debug Info"):
        st.markdown("### Original Data (from file)")
        st.json(original_data)
        
        st.markdown("### Current Data (from widgets)")
        st.json(current_data)
        
        st.markdown("### Widget Session State Keys")
        widget_keys = {k: v for k, v in st.session_state.items() if k.startswith(('field_', 'array_', 'data_editor_'))}
        st.json(widget_keys, expanded=False)

if __name__ == "__main__":
    main()

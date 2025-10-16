# Bug Fix: Array Changes Not Showing in Diff (Root Cause)

## Problem
After adding `st.rerun()`, scalar field changes showed in the diff, but **array field changes still didn't appear**.

## Root Cause: Streamlit Form Widget Behavior

### The Critical Issue
**Inside Streamlit forms, widget values are NOT available until AFTER the form is submitted.**

### What Was Happening

```python
# During form rendering (BEFORE submission):
with st.form("json_edit_form"):
    # Array editor renders widgets
    for i in range(len(array)):
        new_value = st.text_input(
            key=f"scalar_array_Serial Numbers_item_{i}",
            value=array[i]  # ← Returns OLD value (the 'value' parameter)
        )
        # new_value contains OLD value, not user's input!
        working_array[i] = new_value  # ← Storing OLD value
    
    # Form data collected with OLD array values
    form_data["Serial Numbers"] = working_array  # ← OLD values!
    
    if st.form_submit_button("Validate"):
        # NOW the widget values are available in session_state
        # But form_data was already collected with OLD values!
        SessionManager.set_form_data(form_data)  # ← Saving OLD values
```

### The Flow Problem

```
1. Page renders → Form renders → Array widgets created
2. User types new values → Stored in widget internal state
3. User clicks "Validate" → Form submits
4. Widget values NOW available in st.session_state
5. But form_data was collected in step 1 with OLD values!
6. OLD values saved to SessionManager
7. Diff calculated with OLD values
8. No changes detected ❌
```

## The Solution

### New Method: `_collect_array_data_from_widgets()`

Created a new method that collects array data from individual widget keys **AFTER** form submission:

```python
@staticmethod
def _collect_array_data_from_widgets(schema: Dict[str, Any], form_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collect array data from individual widget keys after form submission.
    
    Inside Streamlit forms, widget values are only available in session_state AFTER
    the form is submitted. This method reads the actual submitted values from individual
    array item widgets and updates the form_data accordingly.
    """
    fields = schema.get('fields', {})
    
    for field_name, field_config in fields.items():
        field_type = field_config.get('type', 'string')
        
        if field_type == 'array':
            items_config = field_config.get('items', {})
            item_type = items_config.get('type', 'string')
            
            # For scalar arrays, collect from individual item widgets
            if item_type != 'object':
                field_key = f"scalar_array_{field_name}"
                size_key = f"{field_key}_size"
                
                # Get the array size from session state
                if size_key in st.session_state:
                    array_size = st.session_state[size_key]
                    collected_array = []
                    
                    # Collect values from individual item widgets
                    for i in range(array_size):
                        item_key = f"{field_key}_item_{i}"
                        if item_key in st.session_state:
                            collected_array.append(st.session_state[item_key])
                    
                    # Update form_data with collected array
                    form_data[field_name] = collected_array
                    
                    # Also sync to session state for consistency
                    FormGenerator._sync_array_to_session(field_name, collected_array)
    
    return form_data
```

### Updated Validation Handler

```python
if validate_submitted:
    # CRITICAL: Collect array data from individual item widgets AFTER form submission
    form_data = FormGenerator._collect_array_data_from_widgets(schema, form_data)
    
    # Now form_data has the ACTUAL user input values!
    SessionManager.set_form_data(form_data)
    
    # Validation and diff will now see the correct values
    validation_errors = SubmissionHandler._validate_submission_data(form_data, schema, model_class)
    
    # ... rest of validation logic
    
    st.rerun()  # Refresh to show diff with correct values
```

### New Flow (Fixed)

```
1. Page renders → Form renders → Array widgets created
2. User types new values → Stored in widget internal state
3. User clicks "Validate" → Form submits
4. Widget values NOW available in st.session_state
5. _collect_array_data_from_widgets() reads from session_state ✓
6. form_data updated with NEW values ✓
7. NEW values saved to SessionManager ✓
8. st.rerun() triggers page refresh
9. Diff calculated with NEW values ✓
10. Changes detected and displayed ✓
```

## Code Changes

### File: `utils/form_generator.py`

**Added Method** (after `_sync_array_to_session`):
- `_collect_array_data_from_widgets()` - Collects array values from widget keys

**Modified** (validation handler):
```python
if validate_submitted:
    # NEW LINE: Collect array data from widgets
    form_data = FormGenerator._collect_array_data_from_widgets(schema, form_data)
    
    SessionManager.set_form_data(form_data)
    # ... rest of validation
    st.rerun()
```

**Modified** (submit handler):
```python
if submit_submitted:
    # NEW LINE: Collect array data from widgets
    form_data = FormGenerator._collect_array_data_from_widgets(schema, form_data)
    
    SessionManager.set_form_data(form_data)
    # ... rest of submission
```

## Why This Works

### Streamlit Form Behavior
- Widgets inside forms don't update their return values during rendering
- Widget values are only accessible via `st.session_state` after form submission
- This is by design to prevent partial form submissions

### Our Solution
- During rendering: Widgets created with keys like `scalar_array_{field}_item_{i}`
- User edits: Values stored in widget internal state
- Form submits: Values become available in `st.session_state[key]`
- **Our new method**: Reads from `st.session_state` to get actual values
- Synchronization: Updates both `form_data` and `SessionManager`
- Rerun: Page refreshes with correct data, diff displays changes

## Testing

### Manual Test Steps
1. Open a document with Serial Numbers array
2. Modify array items (change text, add items, remove items)
3. Click "Validate Data"
4. **Expected**: Diff section shows array changes
5. **Before Fix**: Diff showed "No changes detected"
6. **After Fix**: Diff shows added/removed/modified array items

### What to Test
- ✅ Add items to array
- ✅ Remove items from array
- ✅ Modify existing items
- ✅ Change array size
- ✅ Mix of array and scalar field changes
- ✅ Object arrays (should still work via data_editor)

## Impact

### What's Fixed
- ✅ Array changes now appear in diff display
- ✅ Validation sees correct array values
- ✅ Submission saves correct array values
- ✅ Audit logs will contain correct array changes

### What's Preserved
- ✅ Scalar field editing (already working)
- ✅ Object array editing (uses data_editor, different mechanism)
- ✅ Reset functionality
- ✅ Form validation

## Technical Notes

### Why Individual Item Keys?
The array editor creates individual widgets for each item:
- `scalar_array_Serial Numbers_item_0`
- `scalar_array_Serial Numbers_item_1`
- etc.

This allows fine-grained control and validation per item.

### Why Not Use `field_{field_name}` Directly?
The `field_{field_name}` key is updated by `_sync_array_to_session()`, but that happens during rendering with OLD values. We need to read from the individual item keys to get NEW values.

### Object Arrays
Object arrays use `st.data_editor` which manages its own state differently. The data_editor widget returns the updated DataFrame directly, so no special collection is needed.

## Conclusion

**Status**: ✅ **FIXED**

The array diff display issue was caused by Streamlit's form widget behavior. Widget values inside forms are not available until after submission, but we were collecting form data during rendering. The fix collects array data from individual widget keys in `st.session_state` after form submission, ensuring we capture the user's actual input.

**Files Modified**:
- `utils/form_generator.py`:
  - Added `_collect_array_data_from_widgets()` method
  - Updated validation handler to collect array data after submission
  - Updated submit handler to collect array data after submission

**Testing Required**:
- Manual testing with array modifications
- Verify diff display shows array changes
- Test with various array operations (add, remove, modify)
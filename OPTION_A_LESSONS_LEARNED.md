# Option A Architecture: Lessons Learned

## Summary
After extensive testing with `option_a_architecture_test.py`, we've identified the correct patterns for implementing array field support in the production application.

## ✅ Proven Patterns (What Works)

### 1. **Widget State as Single Source of Truth**
- Original data: Always read fresh from JSON file
- Current data: Always read from widget session state keys
- No duplication in SessionManager.form_data

### 2. **Form Version Counter for Reset**
```python
# On reset button click
st.session_state['form_version'] = st.session_state.get('form_version', 0) + 1
st.rerun()

# In widget rendering
form_version = st.session_state.get('form_version', 0)
key = f'field_{field_name}_v{form_version}'
```

**Why it works:** Changing the key forces Streamlit to treat it as a completely new widget, which re-initializes from original data.

### 3. **Data Editor MUST Be Outside Forms**
```python
# ❌ WRONG - Inside form
with st.form("my_form"):
    st.data_editor(df, key="editor")  # Edits NOT captured until form submit

# ✅ CORRECT - Outside form  
st.data_editor(df, key="editor")  # Edits captured immediately
```

**Why:** `st.data_editor` with a key only captures edits when rendered outside a form context.

### 4. **Scalar Arrays: Individual Fields Pattern**

For scalar arrays (tags, serial numbers, categories), use individual input fields with delete icons instead of tables:

```python
# Render each item with its own field
for i, item in enumerate(current_items):
    col1, col2 = st.columns([5, 1])
    with col1:
        item_key = f'{array_key}_item_{i}'
        if item_key not in st.session_state:
            st.session_state[item_key] = item
        
        # Use appropriate widget for type
        st.text_input(f"Item {i+1}", key=item_key, label_visibility="collapsed")
    
    with col2:
        if st.button("🗑️", key=f'delete_{array_key}_{i}'):
            del st.session_state[item_key]
            current_items.pop(i)
            st.rerun()

# Add button
if st.button(f"➕ Add Item"):
    current_items.append(default_value)
    st.rerun()
```

**Data Collection:**
```python
# Collect from individual item keys
items = []
for i in range(len(st.session_state[array_key])):
    item_key = f'{array_key}_item_{i}'
    if item_key in st.session_state:
        items.append(st.session_state[item_key])
current_data[field_name] = items
```

**Why individual fields:**
- More intuitive for users
- Better for short values (tags, categories)
- Clearer visual hierarchy
- Easier to scan
- More precise deletion (per-item vs last-item)
- Mobile friendly

### 5. **Object Arrays: Data Editor with Manual Buttons**

For object arrays (line items, complex records), use `data_editor` with manual add/delete buttons:

```python
# Store edited DataFrame separately for data collection
array_key = f'array_{field_name}_v{form_version}'
df = pd.DataFrame(st.session_state[array_key])
edited_df = st.data_editor(df, num_rows="fixed", key=f'editor_{array_key}')
st.session_state[f'{array_key}_current'] = edited_df

# Data collection reads from _current
current_key = f'{array_key}_current'
if current_key in st.session_state:
    current_data[field_name] = st.session_state[current_key].to_dict('records')
```

### 6. **No Feedback Loop**
```python
# ❌ WRONG - Creates feedback loop
current_data = collect_from_widgets()
render_widgets(current_data)  # Passes collected data back!

# ✅ CORRECT - One-way flow
render_widgets(original_data)  # Only pass original on first render
current_data = collect_from_widgets()  # Collect for display/validation
```

**Why:** Passing collected data back to widgets resets them on every render.

### 7. **Validation Runs on Collected Data**
```python
# Collect current values
current_data = collect_current_data_from_widgets(schema)

# Validate
is_valid, errors = validate_data(current_data)

# Calculate diff
diff = calculate_diff(original_data, current_data)
```

## 🎨 UX Decision: Scalar Arrays vs Object Arrays

### Scalar Arrays → Individual Fields with Delete Icons

**Use for:** Tags, serial numbers, categories, simple lists

**Pattern:**
- Each item gets its own input field
- Delete icon (🗑️) next to each item
- Single "Add" button at bottom
- Stacked vertically

**Advantages:**
- More intuitive ("add a tag" vs "add a row")
- Better for short values
- Clearer visual hierarchy
- Easier to scan
- More precise deletion
- Mobile friendly

### Object Arrays → Data Editor Table

**Use for:** Line items, complex records with multiple properties

**Pattern:**
- Table with columns for each property
- Manual Add/Delete buttons above table
- `num_rows="fixed"` to avoid feedback loops

**Advantages:**
- Compact for many items
- Shows all properties side-by-side
- Natural for structured data
- Easier to compare values

### Implementation Guide

```python
# Decision logic for production
if field_type == "array":
    items_type = items_config.get("type")
    
    if items_type == "object":
        # Always use data_editor for object arrays
        render_object_array_editor()
    else:
        # Use individual fields for scalar arrays
        render_scalar_array_individual_fields()
```

## 🚨 Critical Discovery: Session State Naming Conflicts

### **NEVER use "items" as a session state key!**

```python
# ❌ WRONG - "items" conflicts with dict.items() method
st.session_state.items = [...]  # Actually calls dict.items()!

# ✅ CORRECT - Use a different name
st.session_state.items_list = [...]
st.session_state.line_items = [...]
```

**Why:** `st.session_state` is dict-like, and accessing `.items` returns the dictionary's `.items()` method, not a key named "items". This causes:
- `AttributeError: 'function' object has no attribute 'append'`
- `ValueError: DataFrame constructor not properly called!`

**Other reserved names to avoid:**
- `keys` - dict.keys() method
- `values` - dict.values() method  
- `get` - dict.get() method
- `pop` - dict.pop() method
- `update` - dict.update() method

### 8. **Avoiding Feedback Loops with data_editor**

The key insight from `manual_add_row_test.py`:

```python
# ❌ WRONG - Creates feedback loop
edited_df = st.data_editor(df, key="editor")
st.session_state.items = edited_df.to_dict('records')  # Immediate update
# Next rerun: df is created from session state, which was just updated
# This causes the "jump back" behavior on edits

# ✅ CORRECT - Store edited DataFrame separately
edited_df = st.data_editor(df, key="editor")
st.session_state['items_edited'] = edited_df  # Store for collection
# Don't update the source array here!

# Only update source array on button clicks (Add/Delete)
if st.button("Add"):
    st.session_state.items.append(default_row)
    st.rerun()
```

**Why this works:**
1. `data_editor` reads from the source array (session state)
2. User edits are captured in the returned DataFrame
3. We store the edited DataFrame separately for data collection
4. Source array only changes on explicit button clicks
5. No circular dependency between source and edited data

**Symptoms of feedback loop:**
- Changes "jump back" to previous value
- Need to click/edit twice for changes to stick
- Dropdown selections revert on first try

### 9. **Manual Add/Delete Buttons Pattern for Object Arrays**

```python
# Define default row
DEFAULT_ROW = {"name": "New Item", "quantity": 1, "price": 0.01}

# Add button
if st.button("➕ Add Row"):
    st.session_state.items_list.append(DEFAULT_ROW.copy())
    st.rerun()

# Delete last row button  
if len(st.session_state.items_list) > 0:
    if st.button("🗑️ Delete Last Row"):
        st.session_state.items_list.pop()
        st.rerun()

# Render data_editor with num_rows="fixed"
df = pd.DataFrame(st.session_state.items_list)
edited_df = st.data_editor(df, num_rows="fixed", key="editor")

# Store edited DataFrame (don't update source!)
st.session_state['items_list_edited'] = edited_df
```

**Benefits:**
- No feedback loop issues
- Predictable behavior
- User controls when rows are added/deleted
- Works reliably with all column types (text, number, selectbox)

## ❌ Anti-Patterns (What Doesn't Work)

### 1. **Pre-setting data_editor Session State**
```python
# ❌ WRONG - Streamlit throws error
st.session_state['data_editor_key'] = initial_df
st.data_editor(..., key='data_editor_key')
```

**Error:** `StreamlitValueAssignmentNotAllowedError`

### 2. **Trying to Clear Session State for Reset**
```python
# ❌ WRONG - Widget state persists
for key in list(st.session_state.keys()):
    if key.startswith('field_'):
        del st.session_state[key]
st.rerun()  # Widgets still show old values!
```

**Why:** Streamlit's internal widget cache persists even after deleting session state keys.

### 3. **Syncing During Rendering**
```python
# ❌ WRONG - Overwrites user edits
def render_widget(field_name, value):
    key = f'field_{field_name}'
    st.session_state[key] = value  # Overwrites edits!
    st.text_input(..., key=key)
```

**Why:** Setting session state during rendering overwrites any edits the user made.

### 4. **Using Forms for data_editor**
```python
# ❌ WRONG - Edits not captured
with st.form("form"):
    st.data_editor(df, key="editor")
    st.form_submit_button("Submit")
```

**Why:** `data_editor` only updates session state on form submission, not during editing.

## 🔥 Critical Pydantic Validation Issue

### **Use `@model_validator` for Cross-Field Validation**

When validating that one field matches a calculation from another field (e.g., total_amount = sum of line_items), you MUST use `@model_validator(mode='after')`, not `@field_validator`.

```python
# ❌ WRONG - field_validator runs before other fields are validated
@field_validator('total_amount')
@classmethod
def validate_total_amount(cls, v, info):
    if 'line_items' in info.data:  # line_items might not be validated yet!
        expected = sum(item.total for item in info.data['line_items'])
        if abs(v - expected) > 0.01:
            raise ValueError(f"Mismatch: {v} != {expected}")
    return v

# ✅ CORRECT - model_validator runs after all fields are validated
@model_validator(mode='after')
def validate_total_amount(self):
    expected = sum(item.total for item in self.line_items)  # line_items is guaranteed to exist
    if abs(self.total_amount - expected) > 0.01:
        raise ValueError(f"Total amount {self.total_amount:.2f} doesn't match sum = {expected:.2f}")
    return self
```

**Why:** Pydantic validates fields in the order they're defined in the model. If `total_amount` is defined before `line_items`, the `@field_validator` for `total_amount` runs before `line_items` is parsed, so `info.data['line_items']` doesn't exist yet. Using `@model_validator(mode='after')` ensures all fields are validated first.

**Import required:**
```python
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError
```

## 🎯 Production Implementation Checklist

For implementing array support in the main application:

- [ ] Remove `SessionManager.form_data` duplication
- [ ] Add `form_version` counter to all widget keys
- [ ] Move `data_editor` rendering outside form context
- [ ] **Use manual Add/Delete buttons with `num_rows="fixed"`**
- [ ] **Store edited DataFrame separately (don't update source immediately)**
- [ ] **Avoid reserved session state key names (items, keys, values, etc.)**
- [ ] Collect data from `_edited` keys when needed (validation, diff, submit)
- [ ] Never pass collected data back to widgets during rendering
- [ ] Use form_version increment for reset functionality
- [ ] Only update source arrays on button clicks, not during data_editor rendering

## 📊 Test Results

All scenarios tested successfully in `option_a_architecture_test.py`:

✅ Scalar field editing  
✅ Array of scalars (add/delete/edit)  
✅ Array of objects (add/delete/edit rows)  
✅ Validation with constraints  
✅ Diff calculation  
✅ Reset functionality  
✅ Submit with validation  

## 🔑 Key Insights

### The Fundamental Principle
**Streamlit widgets manage their own state via keys.** Our job is to:
1. Initialize them once with original data
2. Read from them when we need current values
3. Never write back to them during normal rendering
4. Use key versioning to force re-initialization when needed

This is simpler and more reliable than trying to manage state ourselves!

### The data_editor Pattern
**Avoid feedback loops by separating source and edited data:**
1. Source array lives in session state (e.g., `items_list`)
2. `data_editor` reads from source array
3. Edited DataFrame stored separately (e.g., `items_list_edited`)
4. Source array only updated on button clicks (Add/Delete)
5. Data collection reads from `_edited` key

**This prevents the "jump back" behavior** where edits revert on first try.

### Session State Naming
**Avoid Python dict method names** like `items`, `keys`, `values`, `get`, `pop`, `update`. These conflict with `st.session_state`'s dict-like interface and cause cryptic errors.


## 🎓 Final Summary

After extensive testing and debugging, we've established the complete Option A architecture:

### Scalar Arrays (Individual Fields Pattern)
```python
# 1. Initialize with form version
form_version = st.session_state.get('form_version', 0)
array_key = f'scalar_array_{field_name}_v{form_version}'

if array_key not in st.session_state:
    st.session_state[array_key] = initial_data.copy()

# 2. Render each item with delete icon
for i, item in enumerate(st.session_state[array_key]):
    col1, col2 = st.columns([5, 1])
    with col1:
        item_key = f'{array_key}_item_{i}'
        st.text_input(f"Item {i+1}", key=item_key, label_visibility="collapsed")
    with col2:
        if st.button("🗑️", key=f'delete_{array_key}_{i}'):
            del st.session_state[item_key]
            st.session_state[array_key].pop(i)
            st.rerun()

# 3. Add button
if st.button(f"➕ Add Item"):
    st.session_state[array_key].append(default_value)
    st.rerun()

# 4. Data collection from individual keys
items = []
for i in range(len(st.session_state[array_key])):
    item_key = f'{array_key}_item_{i}'
    if item_key in st.session_state:
        items.append(st.session_state[item_key])
```

### Object Arrays (Data Editor Pattern)
```python
# 1. Initialize with form version
form_version = st.session_state.get('form_version', 0)
array_key = f'array_{field_name}_v{form_version}'

if array_key not in st.session_state:
    st.session_state[array_key] = initial_data.copy()

# 2. Manual Add/Delete buttons
if st.button("➕ Add Row"):
    st.session_state[array_key].append(default_row.copy())
    st.rerun()

if st.button("🗑️ Delete Last Row"):
    st.session_state[array_key].pop()
    st.rerun()

# 3. Render with num_rows="fixed"
df = pd.DataFrame(st.session_state[array_key])
edited_df = st.data_editor(df, num_rows="fixed", key=f'editor_{array_key}')

# 4. Store edited DataFrame separately
st.session_state[f'{array_key}_current'] = edited_df

# 5. Data collection reads from _current
current_key = f'{array_key}_current'
if current_key in st.session_state:
    current_data = st.session_state[current_key].to_dict('records')
```

### Cross-Field Validation
```python
from pydantic import model_validator

@model_validator(mode='after')
def validate_total_amount(self):
    expected = sum(item.total for item in self.line_items)
    if abs(self.total_amount - expected) > 0.01:
        raise ValueError(f"Total {self.total_amount:.2f} != sum {expected:.2f}")
    return self
```

### Session State Naming
**Never use:** `items`, `keys`, `values`, `get`, `pop`, `update`  
**Use instead:** `items_list`, `line_items`, `data_items`, etc.

This architecture is now implemented in both `option_a_architecture_test.py` and `array_sandbox_app.py` for consistent testing.


## 📦 Unified Sandbox Application

All Option A architecture tests are now integrated into a single sandbox application for easy testing:

```bash
python -m streamlit run sandbox/array_sandbox_app.py
```

### Available Test Pages:

1. **Overview** - Introduction and available schemas
2. **Complete Editor Test** - Full integration with scalars + scalar arrays + object arrays
3. **Scalar Array Editor** - Test string, number, integer, boolean, date arrays
4. **Object Array Editor** - Test complex object arrays with multiple properties
5. **Schema Editor** - Create and edit array field schemas
6. **Validation Testing** - Test validation rules and error handling
7. **Test Scenarios** - Structured test cases (coming soon)

### Quick Start:

1. Run the sandbox: `python -m streamlit run sandbox/array_sandbox_app.py`
2. Select "Complete Editor Test" from the sidebar
3. Try breaking validation rules to see error handling
4. Use Reset button to test form version counter
5. Check the diff preview to see changes

All tests use the same proven patterns documented in this file.

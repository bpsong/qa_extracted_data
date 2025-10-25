"""
Minimal test to diagnose data_editor behavior with forms.
Run with: streamlit run sandbox/test_data_editor_form.py
"""

import streamlit as st
import pandas as pd

st.title("Data Editor Form Test")

# Sample data - initialize properly
if 'items' not in st.session_state:
    st.session_state['items'] = [
        {'Description': 'Item A', 'Quantity': '10 PCS'},
        {'Description': 'Item B', 'Quantity': '20 PCS'},
        {'Description': 'Item C', 'Quantity': '30 PCS'},
    ]

# Get items
items = st.session_state['items']

st.write("## Test 1: data_editor INSIDE form")
st.write("Edit a description, then click Validate")

with st.form("test_form_inside"):
    df = pd.DataFrame(items)
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_inside_form",
        hide_index=True
    )
    
    validate_btn = st.form_submit_button("Validate (Inside Form)")
    
    if validate_btn:
        st.write("### Session State After Submit:")
        st.write(f"editor_inside_form type: {type(st.session_state.get('editor_inside_form'))}")
        st.write(f"editor_inside_form value: {st.session_state.get('editor_inside_form')}")
        
        st.write("### Edited DataFrame:")
        st.write(edited_df)
        
        st.write("### Converted to records:")
        records = edited_df.to_dict('records')
        st.write(records)
        
        st.write("### Comparison:")
        st.write(f"Original: {items}")
        st.write(f"Edited: {records}")
        st.write(f"Are they equal? {items == records}")

st.write("---")

st.write("## Test 2: data_editor OUTSIDE form")
st.write("Edit a description, then click Validate")

df2 = pd.DataFrame(items)

edited_df2 = st.data_editor(
    df2,
    num_rows="dynamic",
    use_container_width=True,
    key="editor_outside_form",
    hide_index=True
)

with st.form("test_form_outside"):
    validate_btn2 = st.form_submit_button("Validate (Outside Form)")
    
    if validate_btn2:
        st.write("### Session State After Submit:")
        st.write(f"editor_outside_form type: {type(st.session_state.get('editor_outside_form'))}")
        st.write(f"editor_outside_form value: {st.session_state.get('editor_outside_form')}")
        
        st.write("### Edited DataFrame (from session state):")
        # Try to get the edited data from session state
        editor_state = st.session_state.get('editor_outside_form')
        if hasattr(editor_state, 'to_dict'):
            records2 = editor_state.to_dict('records')
        elif isinstance(editor_state, dict):
            st.write("Editor state is a dict with keys:", list(editor_state.keys()))
            records2 = editor_state
        else:
            records2 = []
        
        st.write("### Converted to records:")
        st.write(records2)
        
        st.write("### Comparison:")
        st.write(f"Original: {items}")
        st.write(f"Edited: {records2}")

st.write("---")

st.write("## Debug: All Session State Keys")
st.write({k: type(v).__name__ for k, v in st.session_state.items() if 'editor' in str(k)})

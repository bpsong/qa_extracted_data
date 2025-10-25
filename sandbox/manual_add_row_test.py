"""
Test: Manual Add Row with Default Values

This demonstrates how to add rows with default values instead of relying
on data_editor's built-in + button.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any

st.set_page_config(page_title="Manual Add Row Test", layout="wide")

# Sample data - use 'items_list' to avoid conflict with dict.items() method
if 'items_list' not in st.session_state:
    st.session_state.items_list = [
        {"name": "Item 1", "quantity": 10, "price": 50.00, "category": "electronics"},
        {"name": "Item 2", "quantity": 5, "price": 25.00, "category": "furniture"}
    ]

st.title("Manual Add Row Test")

# Define default values for new rows
DEFAULT_ROW = {
    "name": "New Item",
    "quantity": 1,
    "price": 0.01,
    "category": "supplies"
}

# Add Row button
if st.button("➕ Add New Row with Defaults"):
    st.session_state.items_list.append(DEFAULT_ROW.copy())
    st.rerun()

# Display data editor (without dynamic rows)
items_list = st.session_state.items_list
df = pd.DataFrame(items_list) if items_list else pd.DataFrame(columns=["name", "quantity", "price", "category"])

edited_df = st.data_editor(
    df,
    num_rows="fixed",  # Disable built-in add/delete
    use_container_width=True,
    column_config={
        "name": st.column_config.TextColumn("Name", required=True),
        "quantity": st.column_config.NumberColumn("Quantity", min_value=1, required=True),
        "price": st.column_config.NumberColumn("Price", min_value=0.01, format="%.2f", required=True),
        "category": st.column_config.SelectboxColumn(
            "Category",
            options=["electronics", "furniture", "supplies", "equipment"],
            required=True
        )
    },
    hide_index=False,
    key="items_editor"
)

# Convert edited DataFrame to list for use below
current_items = edited_df.to_dict('records')

# Delete last row button
if len(current_items) > 0:
    if st.button("🗑️ Delete Last Row"):
        st.session_state.items_list = current_items
        st.session_state.items_list.pop()
        st.rerun()

# Show current data
st.subheader("Current Data")
st.json(current_items)

# Validation
st.subheader("Validation")
errors = []
for i, item in enumerate(current_items):
    if not item.get('name') or item['name'].strip() == "":
        errors.append(f"Row {i+1}: Name is required")
    if item.get('quantity', 0) < 1:
        errors.append(f"Row {i+1}: Quantity must be at least 1")
    if item.get('price', 0) < 0.01:
        errors.append(f"Row {i+1}: Price must be at least 0.01")

if errors:
    st.error(f"❌ {len(errors)} validation error(s)")
    for error in errors:
        st.error(f"  • {error}")
else:
    st.success("✅ All rows valid!")

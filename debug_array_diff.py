"""
Debug script to test array diff functionality.
Run this to see debug output for array changes.
"""

import logging
import sys

# Set up logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

from utils.diff_utils import calculate_diff, format_diff_for_display

# Test case: Array of objects with a description change
original_data = {
    "invoice_number": "INV-001",
    "line_items": [
        {"description": "Widget A", "quantity": 2, "price": 10.00},
        {"description": "Widget B", "quantity": 1, "price": 20.00}
    ]
}

modified_data = {
    "invoice_number": "INV-001",
    "line_items": [
        {"description": "Widget A - Updated", "quantity": 2, "price": 10.00},  # Changed description
        {"description": "Widget B", "quantity": 1, "price": 20.00}
    ]
}

print("\n" + "="*80)
print("TESTING ARRAY OF OBJECTS DIFF")
print("="*80)

print("\nOriginal data:")
print(original_data)

print("\nModified data:")
print(modified_data)

print("\n" + "-"*80)
print("CALCULATING DIFF...")
print("-"*80)

diff = calculate_diff(original_data, modified_data)

print("\n" + "-"*80)
print("DIFF RESULT:")
print("-"*80)
print(diff)

print("\n" + "-"*80)
print("FORMATTED DIFF:")
print("-"*80)
formatted = format_diff_for_display(diff, original_data, modified_data)
print(formatted)

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)

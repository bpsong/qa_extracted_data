from datetime import date
import deepdiff
from utils.diff_utils import format_diff_for_display

original = {
    "Invoice Amount": 862.33,  # money number
    "Project ID": 123.456,     # non-money number
    "Description": "Original description",  # string
    "Is Active": True,         # boolean
    "Status": "pending",       # enum (string)
    "Invoice Date": date(2023, 10, 1),  # date
    "Optional Field": None     # null
}
modified = {
    "Invoice Amount": 862.3100000000001,  # money: expect 862.33 -> 862.31
    "Project ID": 123.4567,               # non-money: expect generic, e.g., 123.46 if cleanup, not forced 2dp
    "Description": "Modified description", # string: literal change
    "Is Active": False,                   # boolean: True -> False
    "Status": "approved",                 # enum: pending -> approved
    "Invoice Date": date(2023, 10, 2),    # date: expect ISO str change, e.g., 2023-10-01 -> 2023-10-02
    "Optional Field": "now a string"      # null -> string (type change, but format values)
}

diff = deepdiff.DeepDiff(original, modified, ignore_order=True)
formatted_lines = format_diff_for_display(diff, modified_data=modified, original_data=original)
print("\n".join(formatted_lines))
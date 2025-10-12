from utils.diff_utils import format_diff_for_display

original = {
    "Supplier name": "ITL HARDWARE & ENGINEERING SUPPLIES PTE LTD",
    "Purchase Order number": "1781037",
    "Invoice Amount": 862.33,
    "Project number": "S268588",
}

modified = {
    "Supplier name": "ITL HARDWARE and ENGINEERING SUPPLIES PTE LTD",
    "Purchase Order number": "17810371",
    "Invoice Amount": 862.34,
    "Project number": "S268588a",
    "Currency": "USD",
    "schema_version": 1757925532.490492,
}

# Emulate how your audit file currently stores values_changed (stringified SetOrdered)
fake_diff = {
    "values_changed": "SetOrdered([<root['Supplier name'] t1:\"ITL HARDWARE & ENGINEERING SUP...TD\", t2:\"ITL HARDWARE and ENGINEERING S...TD\">, <root['Purchase Order number'] t1:1781037, t2:17810371>, <root['Invoice Amount'] t1:862.33, t2:862.34>, <root['Project number'] t1:\"S268588\", t2:\"S268588a\">])",
    "dictionary_item_added": {"Currency": "USD", "schema_version": 1757925532.490492},
}

print(format_diff_for_display(fake_diff, original, modified))
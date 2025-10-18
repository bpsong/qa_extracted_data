"""
Diff utilities for JSON QA webapp.
Provides comprehensive JSON document comparison, change tracking, and visualization
using DeepDiff library with enhanced formatting and normalization capabilities.
Supports audit logging, change summarization, and multiple output formats for UI display.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from deepdiff import DeepDiff
import json
import re
import logging

logger = logging.getLogger(__name__)

_MONEY_NAME_TOKENS = {
    "amount", "amt", "price", "cost", "subtotal", "sub total",
    "tax", "gst", "vat", "total", "grand total", "grand_total",
    "balance", "paid", "due", "payment", "charge", "fee"
}


def _is_money_field(field_name: str) -> bool:
    """Return True if the field name suggests a money-like number."""
    if not field_name:
        return False
    name = field_name.strip().lower()
    return any(tok in name for tok in _MONEY_NAME_TOKENS)


def _format_value_for_field(value: Any, field_name: str) -> str:
    """
    Field-aware formatter:
    - If the field name looks money-like and value is float/int -> format to 2dp.
    - Else fallback to _format_value (generic pretty printer).
    """
    try:
        if isinstance(value, (int, float)):
            # Check if it's a money field
            if _is_money_field(field_name):
                return f"{float(value):.2f}"
            # For other numeric fields, clean up floating point precision issues
            elif isinstance(value, float):
                # Round to reasonable precision to avoid 242.98000000000002
                rounded = round(value, 10)  # Remove tiny floating point errors
                if rounded == int(rounded):
                    return str(int(rounded))
                else:
                    return f"{rounded:g}"  # Use 'g' format to avoid unnecessary decimals
    except Exception:
        pass
    return _format_value(value)


def calculate_diff(original: Dict[str, Any], modified: Dict[str, Any], fields: Optional[Set[str]] = None) -> Dict[str, Any]:
    """
    Calculate differences between original and modified data with comprehensive normalization.

    If `fields` is provided, only keys present in the given set will be included from
    both `original` and `modified` before computing the diff. This scopes the diff to
    specific schema fields while preserving the existing behavior when `fields` is None.

    This function performs deep comparison using DeepDiff with extensive data normalization
    to handle common data inconsistencies. Key processing steps include:

    1. **Normalization**: Converts numeric strings to int/float, empty strings to None,
       and recursively normalizes nested structures
    2. **DeepDiff Configuration**: Uses tree view with ignore_order=True for consistent
       list comparison and verbose output
    3. **Output Processing**: Handles multiple DeepDiff output formats (dict, string, SetOrdered)
       and extracts meaningful field names from complex path strings using regex parsing

    Args:
        original: Original data dictionary (will be normalized before comparison)
        modified: Modified data dictionary (will be normalized before comparison)

    Returns:
        Dict containing processed differences with consistent field naming and values:
        - values_changed: Modified fields with old/new values
        - dictionary_item_added: Added fields with their values
        - dictionary_item_removed: Removed fields with their previous values
        - type_changes: Fields with type conversions
        - iterable_item_added/removed: List/array changes
    """
    try:
        # Create normalized copies to avoid modifying originals
        orig = dict(original)
        mod = dict(modified)

        # If fields is provided, filter to only the specified keys before normalization.
        # This scopes the diff to schema fields requested by the caller.
        if fields is not None:
            orig = {k: original.get(k) for k in fields if k in original}
            mod = {k: modified.get(k) for k in fields if k in modified}

        def normalize_value(v: Any) -> Any:
            """Normalize values for comparison.
            
            Handles:
            - Empty strings and None values converted to None
            - Numeric strings converted to int or float
            - Recursive normalization of lists and dictionaries
            """
            if v is None or v == '':
                return None  # Standardize empty values to None
            if isinstance(v, str):
                # Convert numeric strings to appropriate numeric types
                v = v.strip()
                try:
                    if '.' in v:
                        return float(v)  # Handle floating-point numbers
                    return int(v)        # Handle integers
                except ValueError:
                    return v  # Return original string if not numeric
            if isinstance(v, list):
                return [normalize_value(i) for i in v]  # Recursively normalize list items
            if isinstance(v, dict):
                return normalize_dict(v)  # Recursively normalize dictionary
            return v  # Return other types unchanged

        def normalize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            """Normalize dictionary values.
            
            Iterates through all key-value pairs, applies value normalization,
            and preserves keys even when the normalized value is None so DeepDiff
            can accurately detect additions/removals/changes between versions.
            """
            result = {}
            for k, v in d.items():
                normalized = normalize_value(v)
                # Preserve keys even if the normalized value is None. This keeps the
                # presence/absence of fields explicit for DeepDiff comparison.
                result[k] = normalized
            return result

        # Normalize both dictionaries
        normalized_original = normalize_dict(orig)
        normalized_modified = normalize_dict(mod)

        # Calculate differences using DeepDiff with specific configuration
        diff = DeepDiff(
            normalized_original,
            normalized_modified,
            ignore_order=True,  # Ignore list order changes to focus on content differences
            report_repetition=True,  # Report repeated items in lists for completeness
            verbose_level=2,  # Include detailed change information
            view='tree'  # Use tree view for structured output with path information
        )

        # Convert to dictionary and process the diff
        diff_dict = diff.to_dict() if hasattr(diff, 'to_dict') else dict(diff)

        # Ensure all changes are captured in a consistent format
        processed_diff: Dict[str, Any] = {}

        # Handle value changes
        if 'values_changed' in diff_dict:
            processed_diff['values_changed'] = diff_dict['values_changed']

        # Handle added items - process different DeepDiff output formats
        if 'dictionary_item_added' in diff_dict:
            added_items = diff_dict['dictionary_item_added']
            # Convert to consistent dictionary format if not already in dict form
            if not isinstance(added_items, dict):
                added: Dict[str, Any] = {}
                if isinstance(added_items, str):
                    # Handle SetOrdered format which may be stringified (e.g., from serialization)
                    import re
                    # Regex pattern to extract field names from DeepDiff path strings
                    # Example: <root['Currency'] t1:..., t2:...> -> extracts 'Currency'
                    paths = re.findall(r"root\['([^']+)'\]", added_items)
                    for path in paths:
                        key = path
                        added[key] = normalized_modified.get(key)  # Get actual value from modified data
                else:
                    # Handle iterable formats (SetOrdered objects, lists, etc.)
                    for path in added_items:
                        path_str = str(path)
                        # Extract field name using regex from path string
                        import re
                        m = re.search(r"root\['([^']+)'\]", path_str)
                        if m:
                            key = m.group(1)  # Use regex-extracted field name
                        else:
                            # Fallback: manually parse path string if regex fails
                            key = path_str.replace("root['", "").replace("']", "").strip()
                        added[key] = normalized_modified.get(key)  # Retrieve value from normalized data
                processed_diff['dictionary_item_added'] = added
            else:
                processed_diff['dictionary_item_added'] = added_items  # Already in dict format

        # Handle removed items - process different DeepDiff output formats
        if 'dictionary_item_removed' in diff_dict:
            removed_items = diff_dict['dictionary_item_removed']
            # Similar parsing logic as added items for consistency
            if not isinstance(removed_items, dict):
                # For string or iterable formats, pass through as-is (handled by display functions)
                processed_diff['dictionary_item_removed'] = removed_items
            else:
                # Parse dict format to extract field names and old values
                parsed_removed = {}
                import re
                for full_path, _ in removed_items.items():
                    # Extract field name from DeepDiff path using regex
                    m = re.search(r"root\['([^']+)'\]", full_path)
                    field = m.group(1) if m else full_path  # Use regex match or fallback to full path
                    # Extract the old value (t1) from the path string for display purposes
                    t1_match = re.search(r't1:"([^"]+)"', full_path)
                    old_val = _try_parse_simple_literal(t1_match.group(1)) if t1_match else None
                    parsed_removed[field] = old_val  # Store with cleaned field name
                processed_diff['dictionary_item_removed'] = parsed_removed

        # Handle type changes - typically already in consistent dict format
        if 'type_changes' in diff_dict:
            processed_diff['type_changes'] = diff_dict['type_changes']  # Direct assignment for dict format

        # Handle iterable item additions/removals - typically in consistent format
        if 'iterable_item_added' in diff_dict:
            processed_diff['iterable_item_added'] = diff_dict['iterable_item_added']  # List changes added
        if 'iterable_item_removed' in diff_dict:
            processed_diff['iterable_item_removed'] = diff_dict['iterable_item_removed']  # List changes removed

        return processed_diff

    except Exception as e:
        logger.error(f"Error calculating diff: {e}", exc_info=True)
        return {}


def has_changes(diff: Dict[str, Any]) -> bool:
    """
    Check if there are any changes in the diff.

    Args:
        diff: Diff dictionary from calculate_diff

    Returns:
        True if there are changes, False otherwise
    """
    if not diff:
        return False

    # Check for any change types
    change_types = [
        'values_changed',
        'dictionary_item_added',
        'dictionary_item_removed',
        'iterable_item_added',
        'iterable_item_removed',
        'type_changes'
    ]

    return any(change_type in diff and diff[change_type] for change_type in change_types)


def format_diff_for_display(diff: Dict[str, Any], original_data: Optional[Dict[str, Any]] = None, modified_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Format diff output for display in Streamlit.

    Args:
        diff: Diff dictionary from calculate_diff
        original_data: Original data dictionary for context
        modified_data: Modified data dictionary for context

    Returns:
        Formatted string for display
    """
    if not has_changes(diff):
        return "✅ **No changes detected**"

    formatted_lines: List[str] = []
    formatted_lines.append("## 📝 **Changes Summary**\n")

    # Process different types of changes
    def _iter_deepdiff_section(section):
        """
        Yield (path, value) pairs for DeepDiff sections that can be:
        - dict-like (has .items())
        - iterable (list/set/SetOrdered)
        - stringified SetOrdered(...) (from audit JSON)
        - single path string
        """
        if section is None:
            return

        # dict-like
        if hasattr(section, "items"):
            for k, v in section.items():
                yield k, v
            return

        # string cases
        if isinstance(section, str):
            s = section.strip()

            # Handle "SetOrdered([...])" strings by extracting each "<root[...]>..."
            if "SetOrdered([" in s:
                import re
                # This finds each "<root['...'] t1:..., t2:...>" chunk
                items = re.findall(r"<root\[[^\]]+\][^>]*>", s)
                if items:
                    for item in items:
                        # Preserve the raw DeepDiff entry so downstream formatting can
                        # recover both the field name and the before/after values.
                        yield item, None
                    return

            # Fallback: yield the whole string as a single path
            yield s, None
            return

        # generic iterable
        try:
            for item in section:
                # DeepDiff tree can give tuples (path, value) sometimes; normalize
                if isinstance(item, tuple) and len(item) == 2:
                    yield item[0], item[1]
                else:
                    yield str(item), None
        except TypeError:
            # last resort
            yield str(section), None

    if 'values_changed' in diff:
        formatted_lines.append("### 🔄 **Modified Fields**")
        for path, change in _iter_deepdiff_section(diff.get('values_changed')):
            if change is None:
                # parse old/new from string representation if possible
                s = str(path)
                field_name = _clean_path(path)
                t_match = re.search(r"t1:([^,>]+),\s*t2:([^>]+)", s)
                if t_match:
                    old_raw = t_match.group(1).strip().strip('"').strip()
                    new_raw = t_match.group(2).strip().strip('"').strip()
                    raw_old_value = _try_parse_simple_literal(old_raw)
                    raw_new_value = _try_parse_simple_literal(new_raw)
                    old_value = _format_value_for_field(raw_old_value, field_name)
                    new_value = _format_value_for_field(raw_new_value, field_name)
                else:
                    old_value = _format_value_for_field(None, field_name)
                    new_value = _format_value_for_field(None, field_name)
            else:
                field_name = _clean_path(path)
                raw_old_value = change.get('old_value')
                raw_new_value = change.get('new_value')
                old_value = _format_value_for_field(raw_old_value, field_name)
                new_value = _format_value_for_field(raw_new_value, field_name)

            # Show all changes except when both old and new are exactly the same
            if str(old_value) != str(new_value):
                formatted_lines.append(f"**{field_name}:**")
                formatted_lines.append(f"  - ❌ **Before:** `{old_value}`")
                formatted_lines.append(f"  - ✅ **After:** `{new_value}`")
            formatted_lines.append("")

    if 'dictionary_item_added' in diff:
        formatted_lines.append("### ➕ **Added Fields**")
        added_obj = diff.get('dictionary_item_added')

        if added_obj and hasattr(added_obj, "items"):
            for path, value in added_obj.items():
                field_name = _clean_path(path)
                actual_value = modified_data.get(field_name) if modified_data else value
                formatted_value = _format_value_for_field(actual_value, field_name)
                formatted_lines.append(f"**{field_name}:**")
                formatted_lines.append(f"  - ❌ **Before:** `None`")
                formatted_lines.append(f"  - ✅ **After:** `{formatted_value}`")
                formatted_lines.append("")  # Add line break between fields
        else:
            for path, _ in _iter_deepdiff_section(added_obj):
                field_name = _clean_path(str(path))
                actual_value = _extract_value_from_data(str(path), modified_data) if modified_data else None
                formatted_lines.append(f"**{field_name}:**")
                formatted_lines.append("  - ❌ **Before:** `None`")
                formatted_lines.append(f"  - ✅ **After:** `{_format_value_for_field(actual_value, field_name)}`")
                formatted_lines.append("")  # Add line break between fields

        formatted_lines.append("")

    if 'dictionary_item_removed' in diff:
        formatted_lines.append("### ➖ **Removed Fields**")
        removed_obj = diff.get('dictionary_item_removed')
        if removed_obj and hasattr(removed_obj, "items"):
            for path, value in removed_obj.items():
                field_name = _clean_path(path)
                formatted_value = _format_value_for_field(value, field_name)
                formatted_lines.append(f"**{field_name}:** `{formatted_value}`")
        else:
            for path, _ in _iter_deepdiff_section(removed_obj):
                field_name = _clean_path(str(path))
                formatted_lines.append(f"**{field_name}:** `[Removed]`")
        formatted_lines.append("")

    # Handle array changes with simple before/after display
    array_changes = {}
    
    # Collect array field names that have changes
    if 'iterable_item_added' in diff:
        added_sec = diff.get('iterable_item_added')
        if isinstance(added_sec, dict):
            for path in added_sec.keys():
                field_name = _clean_path(path)
                if field_name not in array_changes:
                    array_changes[field_name] = True
        elif isinstance(added_sec, str):
            # Handle string format from serialized diffs
            # Extract field names from paths like "<root['Serial Numbers'][0]"
            field_matches = re.findall(r"root\['([^']+)'\]", added_sec)
            for field_name in set(field_matches):
                if field_name not in array_changes:
                    array_changes[field_name] = True
        elif added_sec is not None and hasattr(added_sec, '__iter__'):
            # Handle list/set format
            for item in added_sec:
                path_str = str(item)
                field_name = _clean_path(path_str)
                if field_name not in array_changes:
                    array_changes[field_name] = True
    
    if 'iterable_item_removed' in diff:
        removed_sec = diff.get('iterable_item_removed')
        if isinstance(removed_sec, dict):
            for path in removed_sec.keys():
                field_name = _clean_path(path)
                if field_name not in array_changes:
                    array_changes[field_name] = True
        elif isinstance(removed_sec, str):
            # Handle string format from serialized diffs
            field_matches = re.findall(r"root\['([^']+)'\]", removed_sec)
            for field_name in set(field_matches):
                if field_name not in array_changes:
                    array_changes[field_name] = True
        elif removed_sec is not None and hasattr(removed_sec, '__iter__'):
            # Handle list/set format
            for item in removed_sec:
                path_str = str(item)
                field_name = _clean_path(path_str)
                if field_name not in array_changes:
                    array_changes[field_name] = True
    
    # Display array changes with simple before/after format
    if array_changes:
        formatted_lines.append("### 📋 **Array Changes**")
        source_original: Dict[str, Any] = original_data if isinstance(original_data, dict) else {}
        source_modified: Dict[str, Any] = modified_data if isinstance(modified_data, dict) else {}
        for field_name in array_changes.keys():
            # Get before and after values from original and modified data
            before_value = source_original.get(field_name, [])
            after_value = source_modified.get(field_name, [])
            
            # Format as simple lists
            before_str = ', '.join([str(v) for v in before_value]) if before_value else '(empty)'
            after_str = ', '.join([str(v) for v in after_value]) if after_value else '(empty)'
            
            formatted_lines.append(f"**{field_name}:**")
            formatted_lines.append(f"  - ❌ **Before:** `[{before_str}]`")
            formatted_lines.append(f"  - ✅ **After:** `[{after_str}]`")
        formatted_lines.append("")

    if 'type_changes' in diff:
        formatted_lines.append("### 🔀 **Type Changes**")
        section = diff.get('type_changes')

        for path, change in _iter_deepdiff_section(section):
            # path may be a DeepDiff path string like "root['Purchase Order number'] ..."
            s = str(path)
            field_name = _clean_path(s)

            # Try to extract old/new from object or from string repr
            old_value = None
            new_value = None
            old_type = 'unknown'
            new_type = 'unknown'

            if change is not None and isinstance(change, dict):
                # DeepDiff sometimes gives a dict with old_value/new_value and types
                raw_old_value = change.get('old_value')
                raw_new_value = change.get('new_value')
                old_value = _format_value_for_field(raw_old_value, field_name)
                new_value = _format_value_for_field(raw_new_value, field_name)
                if 'old_type' in change:
                    old_type = getattr(change['old_type'], '__name__', str(change['old_type']))
                if 'new_type' in change:
                    new_type = getattr(change['new_type'], '__name__', str(change['new_type']))
            else:
                # Parse from the string version like:
                # "<root['Purchase Order number'] t1:1781037, t2:\"1781037DA\">"
                t_match = re.search(r"t1:([^,>]+),\s*t2:([^>]+)", s)
                if t_match:
                    old_raw = t_match.group(1).strip().strip('"').strip()
                    new_raw = t_match.group(2).strip().strip('"').strip()

                    # Reuse the helper used elsewhere to coerce simple literals
                    raw_old_value = _try_parse_simple_literal(old_raw)
                    raw_new_value = _try_parse_simple_literal(new_raw)
                    old_value = _format_value_for_field(raw_old_value, field_name)
                    new_value = _format_value_for_field(raw_new_value, field_name)
                    old_type = type(raw_old_value).__name__ if raw_old_value is not None else 'unknown'
                    new_type = type(raw_new_value).__name__ if raw_new_value is not None else 'unknown'

            formatted_lines.append(f"**{field_name}:**")
            formatted_lines.append(f"  - ❌ **Before:** `{old_value}` ({old_type})")
            formatted_lines.append(f"  - ✅ **After:** `{new_value}` ({new_type})")
            formatted_lines.append("")

    return "\n".join(formatted_lines)


def format_diff_for_streamlit(diff: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Format diff for Streamlit components (tables, metrics, etc.).

    Args:
        diff: Diff dictionary from calculate_diff

    Returns:
        List of change dictionaries for Streamlit display
    """
    if not has_changes(diff):
        return []

    changes: List[Dict[str, Any]] = []

    def _iter_section(section):
        """Yield (path, value) tuples from DeepDiff section shapes."""
        if section is None:
            return
        if hasattr(section, "items"):
            for k, v in section.items():
                yield k, v
            return
        if isinstance(section, str):
            yield section, None
            return
        try:
            for item in section:
                yield str(item), None
        except TypeError:
            yield str(section), None

    # Process value changes
    if 'values_changed' in diff:
        for path, change in _iter_section(diff.get('values_changed')):
            if change is None:
                # parse simple t1/t2 from string
                s = str(path)
                field = _clean_path(path)
                t_match = re.search(r"t1:([^,>]+),\s*t2:([^>]+)", s)
                if t_match:
                    old_raw = t_match.group(1).strip().strip('"').strip()
                    new_raw = t_match.group(2).strip().strip('"').strip()
                    old_val = _format_value(_try_parse_simple_literal(old_raw))
                    new_val = _format_value(_try_parse_simple_literal(new_raw))
                else:
                    old_val = "None"
                    new_val = "None"
                changes.append({
                    'type': 'Modified',
                    'field': field,
                    'old_value': old_val,
                    'new_value': new_val,
                    'icon': '🔄'
                })
            else:
                changes.append({
                    'type': 'Modified',
                    'field': _clean_path(path),
                    'old_value': _format_value(change.get('old_value')),
                    'new_value': _format_value(change.get('new_value')),
                    'icon': '🔄'
                })

    # Process added items
    if 'dictionary_item_added' in diff:
        added = diff.get('dictionary_item_added')
        if isinstance(added, dict):
            for path, value in added.items():
                changes.append({
                    'type': 'Added',
                    'field': _clean_path(path),
                    'old_value': '',
                    'new_value': _format_value(value),
                    'icon': '➕'
                })
        else:
            for path, _ in _iter_section(added):
                field = _clean_path(path)
                changes.append({
                    'type': 'Added',
                    'field': field,
                    'old_value': '',
                    'new_value': '[Added]',
                    'icon': '➕'
                })

    # Process removed items
    if 'dictionary_item_removed' in diff:
        rem = diff.get('dictionary_item_removed')
        if isinstance(rem, dict):
            for path, value in rem.items():
                changes.append({
                    'type': 'Removed',
                    'field': _clean_path(path),
                    'old_value': _format_value(value),
                    'new_value': '',
                    'icon': '➖'
                })
        else:
            for path, _ in _iter_section(rem):
                field = _clean_path(path)
                changes.append({
                    'type': 'Removed',
                    'field': field,
                    'old_value': '[Removed]',
                    'new_value': '',
                    'icon': '➖'
                })

    # Process type changes
    if 'type_changes' in diff:
        tc = diff.get('type_changes')
        if tc is not None and hasattr(tc, "items"):
            iterator = tc.items()
        else:
            iterator = _iter_section(tc)
        for path, change in iterator:
            old_type_name = getattr(change.get('old_type'), '__name__', 'unknown') if change else 'unknown'
            new_type_name = getattr(change.get('new_type'), '__name__', 'unknown') if change else 'unknown'
            old_value = _format_value(change.get('old_value')) if change else "None"
            new_value = _format_value(change.get('new_value')) if change else "None"
            changes.append({
                'type': 'Type Changed',
                'field': _clean_path(path),
                'old_value': f"{old_value} ({old_type_name})",
                'new_value': f"{new_value} ({new_type_name})",
                'icon': '🔀'
            })

    # Process iterable item additions
    if 'iterable_item_added' in diff:
        added_sec = diff.get('iterable_item_added')
        if isinstance(added_sec, dict):
            for path, items in added_sec.items():
                field_name = _clean_path(path)
                if isinstance(items, dict):
                    for index, value in items.items():
                        changes.append({
                            'type': 'Added',
                            'field': f"{field_name}[{index}]",
                            'old_value': '',
                            'new_value': _format_value(value),
                            'icon': '➕'
                        })
                else:
                    changes.append({
                        'type': 'Added',
                        'field': field_name,
                        'old_value': '',
                        'new_value': _format_value(items),
                        'icon': '➕'
                    })
        else:
            for path, _ in _iter_section(added_sec):
                field_name = _clean_path(str(path))
                changes.append({
                    'type': 'Added',
                    'field': field_name,
                    'old_value': '',
                    'new_value': '[Added]',
                    'icon': '➕'
                })

    # Process iterable item removals
    if 'iterable_item_removed' in diff:
        removed_sec = diff.get('iterable_item_removed')
        if isinstance(removed_sec, dict):
            for path, items in removed_sec.items():
                field_name = _clean_path(path)
                if isinstance(items, dict):
                    for index, value in items.items():
                        changes.append({
                            'type': 'Removed',
                            'field': f"{field_name}[{index}]",
                            'old_value': _format_value(value),
                            'new_value': '',
                            'icon': '➖'
                        })
                else:
                    changes.append({
                        'type': 'Removed',
                        'field': field_name,
                        'old_value': _format_value(items),
                        'new_value': '',
                        'icon': '➖'
                    })
        else:
            for path, _ in _iter_section(removed_sec):
                field_name = _clean_path(str(path))
                changes.append({
                    'type': 'Removed',
                    'field': field_name,
                    'old_value': '[Removed]',
                    'new_value': '',
                    'icon': '➖'
                })

    return changes


def get_change_summary(diff: Dict[str, Any]) -> Dict[str, int]:
    """
    Get a summary of changes by type.

    Args:
        diff: Diff dictionary from calculate_diff

    Returns:
        Dictionary with change counts by type
    """
    summary = {
        'modified': 0,
        'added': 0,
        'removed': 0,
        'type_changed': 0,
        'total': 0
    }

    if 'values_changed' in diff:
        summary['modified'] = len(diff['values_changed'])

    if 'dictionary_item_added' in diff:
        added_items = diff['dictionary_item_added']
        if isinstance(added_items, str):
            # Handle serialized SetOrdered format
            if added_items.startswith('SetOrdered([') and added_items.endswith('])'):
                import re
                path_matches = re.findall(r'"([^"]+)"', added_items)
                summary['added'] = len(path_matches)
            else:
                summary['added'] = 1
        else:
            summary['added'] = len(added_items) if hasattr(added_items, '__len__') else 0

    if 'dictionary_item_removed' in diff:
        removed_items = diff['dictionary_item_removed']
        summary['removed'] = len(removed_items) if hasattr(removed_items, '__len__') else 0
    
    # BUGFIX: Count array/iterable changes
    if 'iterable_item_added' in diff:
        iterable_added = diff['iterable_item_added']
        if isinstance(iterable_added, str):
            # Handle serialized format
            import re
            # Count occurrences of root paths
            path_matches = re.findall(r'<root\[', iterable_added)
            summary['added'] += len(path_matches)
        elif hasattr(iterable_added, '__len__'):
            summary['added'] += len(iterable_added)
        else:
            summary['added'] += 1
    
    if 'iterable_item_removed' in diff:
        iterable_removed = diff['iterable_item_removed']
        if isinstance(iterable_removed, str):
            # Handle serialized format
            import re
            path_matches = re.findall(r'<root\[', iterable_removed)
            summary['removed'] += len(path_matches)
        elif hasattr(iterable_removed, '__len__'):
            summary['removed'] += len(iterable_removed)
        else:
            summary['removed'] += 1

    if 'type_changes' in diff:
        summary['type_changed'] = len(diff['type_changes'])

    summary['total'] = sum([
        summary['modified'],
        summary['added'],
        summary['removed'],
        summary['type_changed']
    ])

    return summary


def create_audit_diff_entry(original: Dict[str, Any], modified: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a diff entry suitable for audit logging.

    Args:
        original: Original data
        modified: Modified data

    Returns:
        Audit diff entry
    """
    # Calculate differences
    diff = calculate_diff(original, modified)
    summary = get_change_summary(diff)

    # Sort dictionaries for consistent comparison
    def sort_dict_recursive(d: Dict[str, Any]) -> Dict[str, Any]:
        """Sort dictionary recursively."""
        if not isinstance(d, dict):
            return d
        return {k: sort_dict_recursive(v) if isinstance(v, dict) else v
                for k, v in sorted(d.items())}

    sorted_original = sort_dict_recursive(original)
    sorted_modified = sort_dict_recursive(modified)

    # Create audit entry
    audit_entry = {
        'has_changes': has_changes(diff),
        'change_summary': summary,
        'detailed_diff': diff,
        'original_data': sorted_original,
        'modified_data': sorted_modified
    }

    return audit_entry


def compare_json_files(file1_path: str, file2_path: str) -> Dict[str, Any]:
    """
    Compare two JSON files and return diff.

    Args:
        file1_path: Path to first JSON file
        file2_path: Path to second JSON file

    Returns:
        Diff dictionary
    """
    try:
        with open(file1_path, 'r', encoding='utf-8') as f1:
            data1 = json.load(f1)

        with open(file2_path, 'r', encoding='utf-8') as f2:
            data2 = json.load(f2)

        return calculate_diff(data1, data2)

    except Exception as e:
        logger.error(f"Error comparing JSON files: {e}")
        return {}


_PATH_TOKEN_PATTERN = re.compile(r"\['([^']+)'\]|\.([A-Za-z0-9_]+)|\[(\d+)\]|^([A-Za-z0-9_]+)")


def _parse_deepdiff_path_tokens(path: Any) -> List[Any]:
    """Parse a DeepDiff path into individual components (keys and indices)."""
    if hasattr(path, "path"):
        path_str = path.path()
    else:
        path_str = str(path)

    path_str = path_str.strip()

    # DeepDiff sometimes wraps the path with additional metadata like
    # "<root['field'] t1:..., t2:...>". Extract just the path portion.
    if path_str.startswith("<") and "root" in path_str:
        start = path_str.find("root")
        if start != -1:
            # Stop at the first space (before t1/t2 metadata) or closing angle bracket
            end = path_str.find(" ", start)
            if end == -1:
                end = path_str.find(">", start)
            path_str = path_str[start:end] if end != -1 else path_str[start:]

    # Focus on the actual root path if additional wrappers precede it (e.g., SetOrdered strings)
    root_index = path_str.find("root")
    if root_index > 0:
        path_str = path_str[root_index:]

    # Normalize our custom arrow separator back to dot notation for parsing
    path_str = path_str.replace(" → ", ".")

    tokens: List[Any] = []
    for match in _PATH_TOKEN_PATTERN.findall(path_str):
        key, dot_key, index, start_key = match
        if key:
            tokens.append(key)
        elif dot_key:
            if dot_key != "root":
                tokens.append(dot_key)
        elif index:
            try:
                tokens.append(int(index))
            except ValueError:
                tokens.append(index)
        elif start_key and start_key != "root":
            tokens.append(start_key)

    return tokens


def _clean_path(path: Any) -> str:
    """
    Clean up DeepDiff path for display.

    Args:
        path: Raw path from DeepDiff

    Returns:
        Cleaned path string
    """
    # Handle the ugly format directly first
    path_str = str(path)
    if "root['" in path_str and "t1:" in path_str:
        # Extract full path from ugly format like "<root['line_items'][0]['description'] t1:..., t2:...>"
        import re
        # Extract everything between root and the first space (before t1:)
        path_match = re.search(r"root(\[.*?\])(?:\s|>)", path_str)
        if path_match:
            # Parse the extracted path to get proper formatting
            extracted_path = "root" + path_match.group(1)
            tokens = _parse_deepdiff_path_tokens(extracted_path)
            if tokens:
                display_parts: List[str] = []
                for token in tokens:
                    if isinstance(token, int):
                        if display_parts:
                            display_parts[-1] += f"[{token}]"
                        else:
                            display_parts.append(f"[{token}]")
                    else:
                        display_parts.append(str(token))
                return " → ".join(display_parts) if display_parts else "root"
        # Fallback to simple field extraction if complex parsing fails
        field_match = re.search(r"root\['([^']+)'\]", path_str)
        if field_match:
            return field_match.group(1)
    
    tokens = _parse_deepdiff_path_tokens(path)

    if tokens:
        display_parts: List[str] = []
        for token in tokens:
            if isinstance(token, int):
                if display_parts:
                    display_parts[-1] += f"[{token}]"
                else:
                    display_parts.append(f"[{token}]")
            else:
                display_parts.append(str(token))
        return " → ".join(display_parts) if display_parts else "root"

    # Fallback to string conversion for unusual paths that couldn't be parsed
    path_str = path.path() if hasattr(path, "path") else str(path)
    path_str = path_str.replace("root", "", 1).lstrip(".").strip()
    if " → " in path_str:
        return path_str
    if "." in path_str:
        parts = [part for part in path_str.split(".") if part]
        if parts:
            return " → ".join(parts)
    return path_str or "root"


def _format_value(value: Any, max_length: int = 100) -> str:
    """
    Format a value for display, truncating if necessary.

    Args:
        value: Value to format
        max_length: Maximum length for display

    Returns:
        Formatted string
    """
    if value is None:
        return "None"  # Changed from "null" to "None" to match Python's None display

    if isinstance(value, str):
        if len(value) > max_length:
            return f"{value[:max_length-3]}..."
        return value

    if isinstance(value, (dict, list)):
        json_str = json.dumps(value, ensure_ascii=False)
        if len(json_str) > max_length:
            return f"{json_str[:max_length-3]}..."
        return json_str

    return str(value)


def _try_parse_simple_literal(s: str) -> Any:
    """
    Try to parse a simple literal from a DeepDiff string snippet (numbers, booleans, null/None).
    Fallbacks to returning the original string.
    """
    if s is None:
        return None
    s = s.strip()
    # booleans
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    # null / none
    if s.lower() in ("null", "none"):
        return None
    # numeric int/float
    try:
        if "." in s:
            return float(s)
        return int(s)
    except Exception:
        # strip quotes
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        return s


def highlight_changes_in_json(original: Dict[str, Any], modified: Dict[str, Any]) -> Tuple[str, str]:
    """
    Create highlighted JSON strings showing changes.

    Args:
        original: Original data
        modified: Modified data

    Returns:
        Tuple of (highlighted_original, highlighted_modified)
    """
    diff = calculate_diff(original, modified)

    # For now, return pretty-printed JSON
    # In a full implementation, this could add HTML highlighting
    original_json = json.dumps(original, indent=2, ensure_ascii=False)
    modified_json = json.dumps(modified, indent=2, ensure_ascii=False)

    return original_json, modified_json


def get_field_changes(diff: Dict[str, Any], field_name: str) -> Optional[Dict[str, Any]]:
    """
    Get changes for a specific field.

    Args:
        diff: Diff dictionary
        field_name: Name of the field to check

    Returns:
        Change information for the field or None if no changes
    """
    # Check in values_changed
    if 'values_changed' in diff:
        vc = diff.get('values_changed')
        if isinstance(vc, dict):
            for path, change in vc.items():
                if _clean_path(path) == field_name:
                    return {'type': 'modified', 'old_value': change.get('old_value'), 'new_value': change.get('new_value')}

    # Check in dictionary_item_added
    if 'dictionary_item_added' in diff:
        added_items = diff.get('dictionary_item_added')
        if isinstance(added_items, dict):
            for path, value in added_items.items():
                if _clean_path(path) == field_name:
                    return {'type': 'added', 'old_value': None, 'new_value': value}
        else:
            try:
                for path in (added_items or []):
                    if _clean_path(str(path)) == field_name:
                        return {'type': 'added', 'old_value': None, 'new_value': '[Added]'}
            except TypeError:
                pass

    # Check in dictionary_item_removed
    if 'dictionary_item_removed' in diff:
        removed_items = diff['dictionary_item_removed']
        if hasattr(removed_items, 'items'):
            for path, value in removed_items.items():
                if _clean_path(path) == field_name:
                    return {
                        'type': 'removed',
                        'old_value': value,
                        'new_value': None
                    }
        else:
            for path in removed_items:
                if _clean_path(path) == field_name:
                    return {
                        'type': 'removed',
                        'old_value': '[Removed]',
                        'new_value': None
                    }

    return None


def create_change_badge(change_type: str) -> str:
    """
    Create a colored badge for change type.

    Args:
        change_type: Type of change (modified, added, removed, etc.)

    Returns:
        Markdown badge string
    """
    badges = {
        'modified': '🔄 **Modified**',
        'added': '➕ **Added**',
        'removed': '➖ **Removed**',
        'type_changed': '🔀 **Type Changed**'
    }

    return badges.get(change_type, f'📝 **{change_type.title()}**')


def validate_diff_data(original: Any, modified: Any) -> bool:
    """
    Validate that data can be diffed.

    Args:
        original: Original data
        modified: Modified data

    Returns:
        True if data can be diffed, False otherwise
    """
    try:
        # Try to serialize both to JSON to ensure they're serializable
        json.dumps(original, default=str)
        json.dumps(modified, default=str)
        return True
    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        return False


def _extract_value_from_data(path: str, data: Dict[str, Any]) -> Any:
    """
    Extract value from data using a DeepDiff path.

    Args:
        path: DeepDiff path (e.g., "root['Currency']")
        data: Data dictionary to extract from

    Returns:
        The value if found, None otherwise
    """
    try:
        tokens = _parse_deepdiff_path_tokens(path)

        # If we couldn't parse any tokens, fall back to direct lookups using
        # the raw path or cleaned representation.
        if not tokens:
            if isinstance(path, str) and path in data:
                return data.get(path)

            cleaned = _clean_path(path)
            if cleaned in data:
                return data.get(cleaned)

            return None

        current: Any = data
        for token in tokens:
            if isinstance(token, int):
                if isinstance(current, list) and 0 <= token < len(current):
                    current = current[token]
                else:
                    return None
            else:
                if isinstance(current, dict):
                    current = current.get(token)
                else:
                    return None

        return current

    except Exception as e:
        logger.debug(f"Could not extract value from path {path}: {e}")
        return None

    return None

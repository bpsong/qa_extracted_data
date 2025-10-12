from pathlib import Path
from textwrap import dedent
import re

path = Path("utils/diff_utils.py")
text = path.read_text(encoding="utf-8")

if "_MONEY_NAME_TOKENS" not in text:
    anchor = "logger = logging.getLogger(__name__)\n\n\n"
    if anchor in text:
        addition = dedent(
            """
# Heuristic tokens for money-like fields (case-insensitive)
_MONEY_NAME_TOKENS = {
    \"amount\", \"amt\", \"price\", \"cost\", \"subtotal\", \"sub total\",
    \"tax\", \"gst\", \"vat\", \"total\", \"grand total\", \"grand_total\",
    \"balance\", \"paid\", \"due\", \"payment\", \"charge\", \"fee\"
}


def _is_money_field(field_name: str) -> bool:
    \"\"\"Return True if the field name suggests a money-like number.\"\"\"
    if not field_name:
        return False
    name = field_name.strip().lower()
    return any(tok in name for tok in _MONEY_NAME_TOKENS)


def _format_value_for_field(value: Any, field_name: str) -> str:
    \"\"\"
    Field-aware formatter:
    - If the field name looks money-like and value is float/int -> format to 2dp.
    - Else fallback to _format_value (generic pretty printer).
    \"\"\"
    try:
        if isinstance(value, (int, float)) and _is_money_field(field_name):
            return f\"{float(value):.2f}\"
    except Exception:
        pass
    return _format_value(value)
"""
        )
        text = text.replace(anchor, anchor + addition + "\n")
    else:
        raise RuntimeError("Anchor not found for insertion")

values_block = (
    "    if 'values_changed' in diff:\n"
    "        formatted_lines.append(\"### ?? **Modified Fields**\")\n"
    "        for path, change in _iter_deepdiff_section(diff.get('values_changed')):\n"
    "            if change is None:\n"
    "                s = str(path)\n"
    "                import re\n"
    "                m = re.search(r\"\\['([^']+)\\']\", s)\n"
    "                field_name = m.group(1) if m else s\n"
    "                t_match = re.search(r\"t1:([^,>]+),\\s*t2:([^>]+)\", s)\n"
    "                if t_match:\n"
    "                    old_raw = t_match.group(1).strip().strip('\\\"').strip()\n"
    "                    new_raw = t_match.group(2).strip().strip('\\\"').strip()\n"
    "                    old_parsed = _try_parse_simple_literal(old_raw)\n"
    "                    new_parsed = _try_parse_simple_literal(new_raw)\n"
    "                    old_value = _format_value_for_field(old_parsed, field_name)\n"
    "                    new_value = _format_value_for_field(new_parsed, field_name)\n"
    "                else:\n"
    "                    old_value = _format_value_for_field(None, field_name)\n"
    "                    new_value = _format_value_for_field(None, field_name)\n"
    "            else:\n"
    "                field_name = _clean_path(path)\n"
    "                old_value = _format_value_for_field(change.get('old_value'), field_name)\n"
    "                new_value = _format_value_for_field(change.get('new_value'), field_name)\n"
    "\n"
    "            formatted_lines.append(f\"**{field_name}:**\")\n"
    "            formatted_lines.append(f\"  - ? **Before:** `{old_value}`\")\n"
    "            formatted_lines.append(f\"  - ? **After:** `{new_value}`\")\n"
    "            formatted_lines.append(\"\")\n"
)

added_block = (
    "    if 'dictionary_item_added' in diff:\n"
    "        formatted_lines.append(\"### ? **Added Fields**\")\n"
    "        added_obj = diff.get('dictionary_item_added')\n"
    "\n"
    "        if added_obj and hasattr(added_obj, \"items\"):\n"
    "            for path, value in added_obj.items():\n"
    "                field_name = _clean_path(path)\n"
    "                formatted_value = _format_value_for_field(value, field_name)\n"
    "                formatted_lines.append(f\"**{field_name}:**\")\n"
    "                formatted_lines.append(\"  - ? **Before:** `None`\")\n"
    "                formatted_lines.append(f\"  - ? **After:** `{formatted_value}`\")\n"
    "                formatted_lines.append(\"\")\n"
    "        else:\n"
    "            for path, _ in _iter_deepdiff_section(added_obj):\n"
    "                field_name = _clean_path(str(path))\n"
    "                actual_value = _extract_value_from_data(str(path), modified_data) if modified_data else None\n"
    "                formatted_lines.append(f\"**{field_name}:**\")\n"
    "                formatted_lines.append(\"  - ? **Before:** `None`\")\n"
    "                formatted_lines.append(f\"  - ? **After:** `{_format_value_for_field(actual_value, field_name)}`\")\n"
    "                formatted_lines.append(\"\")\n"
    "\n"
    "        formatted_lines.append(\"\")\n"
)

removed_block = (
    "    if 'dictionary_item_removed' in diff:\n"
    "        formatted_lines.append(\"### ? **Removed Fields**\")\n"
    "        removed_obj = diff.get('dictionary_item_removed')\n"
    "        if removed_obj and hasattr(removed_obj, \"items\"):\n"
    "            for path, value in removed_obj.items():\n"
    "                field_name = _clean_path(path)\n"
    "                formatted_value = _format_value_for_field(value, field_name)\n"
    "                formatted_lines.append(f\"**{field_name}:** `{formatted_value}`\")\n"
    "        else:\n"
    "            for path, _ in _iter_deepdiff_section(removed_obj):\n"
    "                field_name = _clean_path(str(path))\n"
    "                formatted_lines.append(f\"**{field_name}:** `[Removed]`\")\n"
    "        formatted_lines.append(\"\")\n"
    "\n"
)

type_block = (
    "    if 'type_changes' in diff:\n"
    "        formatted_lines.append(\"### ?? **Type Changes**\")\n"
    "        section = diff.get('type_changes')\n"
    "\n"
    "        for path, change in _iter_deepdiff_section(section):\n"
    "            field_name = _clean_path(str(path))\n"
    "            old_value = None\n"
    "            new_value = None\n"
    "            old_type = 'unknown'\n"
    "            new_type = 'unknown'\n"
    "\n"
    "            if change is not None and isinstance(change, dict):\n"
    "                old_value = _format_value_for_field(change.get('old_value'), field_name)\n"
    "                new_value = _format_value_for_field(change.get('new_value'), field_name)\n"
    "                old_type = getattr(change.get('old_type'), '__name__', 'unknown')\n"
    "                new_type = getattr(change.get('new_type'), '__name__', 'unknown')\n"
    "            else:\n"
    "                s = str(path)\n"
    "                import re\n"
    "                t_match = re.search(r\"t1:([^,>]+),\\s*t2:([^>]+)\", s)\n"
    "                if t_match:\n"
    "                    old_raw = t_match.group(1).strip().strip('\\\"').strip()\n"
    "                    new_raw = t_match.group(2).strip().strip('\\\"').strip()\n"
    "                    old_parsed = _try_parse_simple_literal(old_raw)\n"
    "                    new_parsed = _try_parse_simple_literal(new_raw)\n"
    "                    old_value = _format_value_for_field(old_parsed, field_name)\n"
    "                    new_value = _format_value_for_field(new_parsed, field_name)\n"
    "                    old_type = type(old_parsed).__name__ if old_parsed is not None else 'unknown'\n"
    "                    new_type = type(new_parsed).__name__ if new_parsed is not None else 'unknown'\n"
    "                else:\n"
    "                    old_value = _format_value_for_field(None, field_name)\n"
    "                    new_value = _format_value_for_field(None, field_name)\n"
    "\n"
    "            formatted_lines.append(f\"**{field_name}:**\")\n"
    "            formatted_lines.append(f\"  - ? **Before:** `{old_value}` ({old_type})\")\n"
    "            formatted_lines.append(f\"  - ? **After:** `{new_value}` ({new_type})\")\n"
    "            formatted_lines.append(\"\")\n"
)

values_pattern = r"    if 'values_changed' in diff:\n(?:.*\n)*?(?=    if 'dictionary_item_added' in diff:)"
text, count = re.subn(values_pattern, lambda m: values_block, text, count=1, flags=re.DOTALL)
if count != 1:
    raise RuntimeError("Failed to update values_changed block")

added_pattern = r"    if 'dictionary_item_added' in diff:\n(?:.*\n)*?(?=    if 'dictionary_item_removed' in diff:)"
text, count = re.subn(added_pattern, lambda m: added_block, text, count=1, flags=re.DOTALL)
if count != 1:
    raise RuntimeError("Failed to update dictionary_item_added block")

removed_pattern = r"    if 'dictionary_item_removed' in diff:\n(?:.*\n)*?(?=    if 'iterable_item_added' in diff:)"
text, count = re.subn(removed_pattern, lambda m: removed_block, text, count=1, flags=re.DOTALL)
if count != 1:
    raise RuntimeError("Failed to update dictionary_item_removed block")

type_pattern = r"    if 'type_changes' in diff:\n(?:.*\n)*?(?=" + re.escape('    return "\\n".join(formatted_lines)\n') + r")"
text, count = re.subn(type_pattern, lambda m: type_block, text, count=1, flags=re.DOTALL)
if count != 1:
    raise RuntimeError("Failed to update type_changes block")

path.write_text(text, encoding="utf-8")

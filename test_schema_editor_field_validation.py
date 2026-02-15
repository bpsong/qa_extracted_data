from utils.schema_editor_view import validate_field, _validate_single_field_name


def test_array_without_items_fails_validation():
    errors = validate_field("missing_items", {"type": "array"})
    assert any("must have 'items'" in error for error in errors)


def test_object_array_requires_properties():
    field_config = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {},
        },
    }

    errors = validate_field("line_items", field_config)

    assert any("property" in error.lower() for error in errors)


def test_scalar_array_cannot_mix_object_metadata():
    field_config = {
        "type": "array",
        "items": {
            "type": "boolean",
            "properties": {"unexpected": {"type": "string"}},
            "choices": ["yes", "no"],
        },
    }

    errors = validate_field("flags", field_config)

    assert any("properties" in error for error in errors)
    assert any("choices" in error for error in errors)


def test_validate_single_field_name_helper():
    assert _validate_single_field_name("") == ["Field names must be non-empty strings"]
    assert _validate_single_field_name("   ") == ["Field names cannot be empty or only whitespace"]
    assert _validate_single_field_name(123) == ["Field names must be non-empty strings"]
    assert _validate_single_field_name("x" * 101)[0].startswith("Field name")
    assert _validate_single_field_name("valid_name") == []

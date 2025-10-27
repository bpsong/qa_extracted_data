from utils.array_field_manager import ArrayFieldManager


def test_sanitize_scalar_items_strips_object_metadata():
    items_config = {
        "type": "object",
        "properties": {"legacy": {"type": "string"}},
        "choices": ["yes", "no"],
        "min_length": 3,
        "default": True,
    }

    sanitized = ArrayFieldManager._sanitize_scalar_items(items_config, "boolean")

    assert sanitized["type"] == "boolean"
    assert sanitized.get("default") is True
    assert "properties" not in sanitized
    assert "choices" not in sanitized
    assert "min_length" not in sanitized


def test_sanitize_object_items_removes_scalar_keys():
    items_config = {
        "type": "string",
        "choices": ["A", "B"],
        "default": "A",
        "min_value": 1,
    }

    sanitized = ArrayFieldManager._sanitize_object_items(items_config)

    assert sanitized["type"] == "object"
    assert "choices" not in sanitized
    assert "default" not in sanitized
    assert "min_value" not in sanitized
    assert sanitized.get("properties") == {}


def test_validate_array_config_flags_incompatible_scalar_constraints():
    field_config = {
        "type": "array",
        "items": {
            "type": "boolean",
            "choices": ["yes"],
            "properties": {"should_not": "exist"},
        },
    }

    errors = ArrayFieldManager.validate_array_config(field_config)

    assert any("choices" in error for error in errors)
    assert any("properties" in error for error in errors)

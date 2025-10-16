"""
Submission handler for JSON QA webapp.
Handles form validation, data submission, and workflow completion.
"""

import streamlit as st
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging
import re

from .session_manager import SessionManager
from .model_builder import validate_model_data
from .file_utils import save_corrected_json, release_file, append_audit_log
from .diff_utils import create_audit_diff_entry, has_changes, calculate_diff
from utils.ui_feedback import Notify

# Configure logging
logger = logging.getLogger(__name__)

def _sanitize_for_json(obj: Any, parent_key: str = None) -> Any:
    """
    Recursively sanitize an object for JSON serialization.
    Converts date, datetime to ISO format strings and Decimal to float.
    Preserves floats for money fields even if they're whole numbers (e.g., 862.00 stays as 862.0).
    """
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v, k) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(item, parent_key) for item in obj]
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, float):
        # Fix floating point precision issues (e.g., 242.98000000000002 → 242.98)
        # Round to 10 decimal places to remove tiny floating point errors
        rounded = round(obj, 10)
        
        # Check if this is a money field - if so, always keep as float
        if parent_key and _is_money_field_name(parent_key):
            return rounded  # Keep as float even if it's 862.0
        
        # For non-money fields, convert whole numbers to integers
        if rounded == int(rounded):
            return int(rounded)
        return rounded
    else:
        return obj


def _is_money_field_name(field_name: str) -> bool:
    """Check if a field name suggests it's a money field."""
    if not field_name:
        return False
    name = field_name.lower()
    money_tokens = ['amount', 'amt', 'price', 'cost', 'subtotal', 'tax', 'gst', 'vat', 'total']
    return any(token in name for token in money_tokens)


class SubmissionHandler:
    """Handles the submission workflow for corrected JSON data."""
    
    @staticmethod
    def build_corrected_payload(form_values: dict, schema_fields: set, base_meta: dict) -> dict:
        """Build final payload restricted to schema_fields and include schema_version from session."""
        # Start with base meta if provided
        payload = base_meta.copy() if base_meta else {}
        # If schema_fields is falsy, include all form values to avoid data loss
        if not schema_fields:
            payload.update(form_values or {})
        else:
            # Restrict to allowed fields only
            payload.update({k: v for k, v in (form_values or {}).items() if k in schema_fields})
        # Attach schema_version if present in session
        if 'schema_version' in st.session_state:
            payload['schema_version'] = st.session_state['schema_version']
        return payload
    
    @staticmethod
    def validate_and_submit(
        filename: str,
        form_data: Dict[str, Any],
        original_data: Dict[str, Any],
        schema: Dict[str, Any],
        model_class: Optional[Any] = None,
        user: str = "unknown"
    ) -> Tuple[bool, List[str]]:
        """
        Validate and submit corrected data.
        
        Args:
            filename: Name of the file being processed
            form_data: Corrected form data
            original_data: Original JSON data
            schema: Schema definition
            model_class: Pydantic model class for validation
            user: Username for audit logging
            
        Returns:
            Tuple of (success: bool, errors: List[str])
        """
        try:
            # Step 1: Validate form data
            validation_errors = SubmissionHandler._validate_submission_data(
                form_data, schema, model_class
            )
            
            if validation_errors:
                logger.warning(f"Validation failed for {filename}: {len(validation_errors)} errors")
                return False, validation_errors
            
            # ---- Remove all code that deletes fields not in original_data or that treats any field specially ----
            # The form_data should be submitted as-is, including all fields present in the form, regardless of original_data.
            # This ensures that new fields added by the schema and filled by the user are included in the submission and audit.
            
            # Step 2: Check for changes
            diff = calculate_diff(original_data, form_data)
            if not has_changes(diff):
                logger.info(f"No changes detected for {filename}")
                # Still proceed with submission to mark as reviewed
            
            # Insert default schema values for fields missing in form_data
            for field_name, field_config in schema.get('fields', {}).items():
                if form_data.get(field_name) in [None, '']:
                    if 'default' in field_config:
                        form_data[field_name] = field_config['default']
                        logger.debug(f"Default value for {field_name} set to {field_config['default']}")

            # Step 3: Sanitize form data for JSON serialization
            # Ensure we only save schema fields plus schema_version (if present)
            sanitized_data = _sanitize_for_json(form_data)
            
            # Step 4: Save corrected data
            if not save_corrected_json(filename, sanitized_data):
                error_msg = f"Failed to save corrected data for {filename}"
                logger.error(error_msg)
                return False, [error_msg]
            
            # Step 5: Create and log audit entry (use sanitized data for clean audit logs)
            deprecated = st.session_state.get("deprecated_fields_current_doc", [])
            schema_version = st.session_state.get("schema_version")
            audit_success = SubmissionHandler._create_audit_entry(
                filename, original_data, sanitized_data, user, diff, deprecated, schema_version
            )
            
            if not audit_success:
                logger.warning(f"Audit logging failed for {filename}")
                # Don't fail submission for audit logging issues
            
            # Step 6: Release file lock
            if not release_file(filename):
                logger.warning(f"Failed to release lock for {filename}")
                # Don't fail submission for lock release issues
            
            logger.info(f"Successfully submitted {filename} by {user}")
            return True, []
            
        except Exception as e:
            error_msg = f"Submission error for {filename}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, [error_msg]
    
    @staticmethod
    def _validate_submission_data(
        form_data: Dict[str, Any],
        schema: Dict[str, Any],
        model_class: Optional[Any] = None,
        use_comprehensive: bool = True
    ) -> List[str]:
        """Validate form data before submission."""
        field_errors = {}  # Dict to group errors by field
        
        try:
            if use_comprehensive:
                # Use comprehensive validation with detailed error reporting
                comprehensive_result = SubmissionHandler.comprehensive_validate_data(form_data, schema)
                
                # Convert comprehensive errors to simple string format for backward compatibility
                for error in comprehensive_result["errors"]:
                    field_name = error.get("field_path", "general")
                    # Extract base field name (remove array indices and property paths)
                    base_field = field_name.split('[')[0].split('.')[0]
                    
                    if base_field not in field_errors:
                        field_errors[base_field] = []
                    field_errors[base_field].append(error["message"])
            else:
                # Use legacy validation
                schema_errors = SubmissionHandler._validate_against_schema(form_data, schema)
                for error in schema_errors:
                    # Extract field name from error message (assuming format like "Field 'name' error")
                    field_name = SubmissionHandler._extract_field_from_error(error)
                    if field_name not in field_errors:
                        field_errors[field_name] = []
                    field_errors[field_name].append(error)
            
            # Pydantic model validation (if available)
            if model_class:
                model_errors = validate_model_data(form_data, model_class)
                for error in model_errors:
                    field_name = SubmissionHandler._extract_field_from_error(error)
                    if field_name not in field_errors:
                        field_errors[field_name] = []
                    field_errors[field_name].append(error)
            
            # Business logic validation
            business_errors = SubmissionHandler._validate_business_rules(form_data, schema)
            for error in business_errors:
                # Business rules may not reference specific fields; add as general
                if 'general' not in field_errors:
                    field_errors['general'] = []
                field_errors['general'].append(error)
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            field_errors['system'] = [f"Validation system error: {str(e)}"]
        
        # Flatten to list, deduplicating per field
        all_errors = []
        for field, errs in field_errors.items():
            unique_errs = list(set(errs))  # Deduplicate errors for the field
            all_errors.extend(unique_errs)
        
        return all_errors

    @staticmethod
    def _extract_field_from_error(error: str) -> str:
        """Extract field name from error message."""
        import re
        
        # First, try quoted field names
        match = re.search(r"'([^']+)'", error)
        if match:
            return match.group(1)
        
        # Then, try unquoted field names before ':' (common in model errors)
        match = re.match(r'^([A-Za-z0-9\s&\-]+?):\s', error)
        if match:
            return match.group(1).strip()
        
        # Fallback to general
        return 'general'
    
    @staticmethod
    def _validate_against_schema(form_data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Validate data against schema definition."""
        errors = []
        fields = schema.get('fields', {})
        
        for field_name, field_config in fields.items():
            value = form_data.get(field_name)
            field_errors = SubmissionHandler._validate_field(field_name, value, field_config)
            errors.extend(field_errors)
        
        return errors
    
    @staticmethod
    def _validate_field(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[str]:
        """Validate a single field value against its configuration."""
        errors = []
        
        # Check required fields
        if field_config.get('required', False):
            if value is None or (isinstance(value, str) and value.strip() == ''):
                label = field_config.get('label', field_name)
                errors.append(f"'{label}' is required")
                return errors  # Skip other validations if required field is missing
        
        # Skip validation for empty optional fields (but not for required validation)
        if value is None:
            return errors
        
        # For strings, only skip if it's empty AND not required AND no min_length constraint
        if isinstance(value, str) and value.strip() == '':
            if not field_config.get('required', False) and field_config.get('min_length') is None:
                return errors
        
        field_type = field_config.get('type', 'string')
        
        # Type-specific validation
        if field_type == 'string':
            errors.extend(SubmissionHandler._validate_string_field(field_name, value, field_config))
        
        elif field_type in ['number', 'integer', 'float']:
            errors.extend(SubmissionHandler._validate_numeric_field(field_name, value, field_config))
        
        elif field_type == 'boolean':
            if not isinstance(value, bool):
                label = field_config.get('label', field_name)
                errors.append(f"'{label}' must be true or false")
        
        elif field_type == 'enum':
            errors.extend(SubmissionHandler._validate_enum_field(field_name, value, field_config))
        
        elif field_type == 'date':
            errors.extend(SubmissionHandler._validate_date_field(field_name, value, field_config))
        
        elif field_type == 'array':
            errors.extend(SubmissionHandler._validate_array_field(field_name, value, field_config))
        
        elif field_type == 'object':
            errors.extend(SubmissionHandler._validate_object_field(field_name, value, field_config))
        
        return errors
    
    @staticmethod
    def _validate_string_field(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[str]:
        """Validate string field."""
        errors = []
        label = field_config.get('label', field_name)
        
        if not isinstance(value, str):
            errors.append(f"'{label}' must be text")
            return errors
        
        # Length validation
        min_length = field_config.get('min_length')
        max_length = field_config.get('max_length')
        
        if min_length is not None and len(value) < min_length:
            errors.append(f"'{label}' must be at least {min_length} characters long")
        
        if max_length is not None and len(value) > max_length:
            errors.append(f"'{label}' must be at most {max_length} characters long")
        
        # Pattern validation
        pattern = field_config.get('pattern')
        if pattern:
            try:
                if not re.match(pattern, value):
                    errors.append(f"'{label}' format is invalid")
            except re.error:
                logger.error(f"Invalid regex pattern for field {field_name}: {pattern}")
        
        return errors
    
    @staticmethod
    def _validate_scalar_item(item_path: str, value: Any, items_config: Dict[str, Any]) -> List[str]:
        """Validate individual scalar array item with enhanced error reporting"""
        errors = []
        item_type = items_config.get("type", "string")
        
        # Type validation
        if item_type == "string":
            if not isinstance(value, str):
                errors.append(f"{item_path}: must be a string")
                return errors
            
            # String constraints
            min_length = items_config.get("min_length")
            if min_length is not None and len(value) < min_length:
                errors.append(f"{item_path}: must be at least {min_length} characters long")
            
            max_length = items_config.get("max_length")
            if max_length is not None and len(value) > max_length:
                errors.append(f"{item_path}: must be no more than {max_length} characters long")
            
            pattern = items_config.get("pattern")
            if pattern and value:
                try:
                    if not re.match(pattern, value):
                        errors.append(f"{item_path}: must match pattern {pattern}")
                except re.error:
                    logger.error(f"Invalid regex pattern for item {item_path}: {pattern}")
        
        elif item_type in ["number", "integer"]:
            try:
                numeric_value = float(value) if item_type == "number" else int(value)
            except (ValueError, TypeError):
                errors.append(f"{item_path}: must be a valid {item_type}")
                return errors
            
            min_value = items_config.get("min_value")
            if min_value is not None and numeric_value < min_value:
                errors.append(f"{item_path}: must be at least {min_value}")
            
            max_value = items_config.get("max_value")
            if max_value is not None and numeric_value > max_value:
                errors.append(f"{item_path}: must be no more than {max_value}")
        
        elif item_type == "boolean":
            if not isinstance(value, bool):
                errors.append(f"{item_path}: must be a boolean")
        
        elif item_type == "date":
            if isinstance(value, str):
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    errors.append(f"{item_path}: must be a valid date in YYYY-MM-DD format")
            elif not isinstance(value, date):
                errors.append(f"{item_path}: must be a valid date")
        
        elif item_type == "enum":
            choices = items_config.get("choices", [])
            if value not in choices:
                choices_str = ', '.join(str(c) for c in choices)
                errors.append(f"{item_path}: must be one of: {choices_str}")
        
        return errors
    
    @staticmethod
    def _validate_numeric_field(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[str]:
        """Validate numeric field."""
        errors = []
        label = field_config.get('label', field_name)
        field_type = field_config.get('type', 'number')
        
        # Type checking
        if field_type == 'integer':
            if not isinstance(value, int):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    errors.append(f"'{label}' must be a whole number")
                    return errors
        else:
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    errors.append(f"'{label}' must be a number")
                    return errors
        
        # Range validation
        min_value = field_config.get('min_value')
        max_value = field_config.get('max_value')
        
        if min_value is not None and value < min_value:
            errors.append(f"'{label}' must be at least {min_value}")
        
        if max_value is not None and value > max_value:
            errors.append(f"'{label}' must be at most {max_value}")
        
        return errors
    
    @staticmethod
    def _validate_enum_field(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[str]:
        """Validate enum field."""
        errors = []
        label = field_config.get('label', field_name)
        choices = field_config.get('choices', [])
        
        if value not in choices:
            choices_str = ', '.join(str(c) for c in choices)
            errors.append(f"'{label}' must be one of: {choices_str}")
        
        return errors
    
    @staticmethod
    def _validate_date_field(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[str]:
        """Validate date field."""
        errors = []
        label = field_config.get('label', field_name)
        
        if value is None:
            return errors
        
        # Check for various date-like objects
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                errors.append(f"'{label}' must be a valid date")
        else:
            # Check if it has date-like attributes (works for both date and datetime)
            if not (hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day')):
                errors.append(f"'{label}' must be a valid date")
        
        return errors
    
    @staticmethod
    def _validate_array_field(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[str]:
        """Validate array field with enhanced item validation."""
        errors = []
        label = field_config.get('label', field_name)
        
        if not isinstance(value, list):
            errors.append(f"'{label}' must be a list")
            return errors
        
        # Validate array items if item schema is provided
        items_config = field_config.get('items')
        if items_config:
            items_type = items_config.get('type')
            
            for i, item in enumerate(value):
                item_path = f"{field_name}[{i}]"
                
                if items_type == "object":
                    # Validate object items
                    properties = items_config.get("properties", {})
                    if not isinstance(item, dict):
                        errors.append(f"{item_path}: must be an object")
                        continue
                    
                    # Validate object properties
                    for prop_name, prop_config in properties.items():
                        prop_path = f"{item_path}.{prop_name}"
                        prop_value = item.get(prop_name)
                        prop_errors = SubmissionHandler._validate_field(prop_path, prop_value, prop_config)
                        errors.extend(prop_errors)
                else:
                    # Validate scalar items using enhanced validation
                    item_errors = SubmissionHandler._validate_scalar_item(item_path, item, items_config)
                    errors.extend(item_errors)
        
        return errors
    
    @staticmethod
    def _validate_object_field(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[str]:
        """Validate object field."""
        errors = []
        label = field_config.get('label', field_name)
        
        if not isinstance(value, dict):
            errors.append(f"'{label}' must be an object")
            return errors
        
        # Validate object properties if schema is provided
        properties = field_config.get('properties', {})
        for prop_name, prop_config in properties.items():
            prop_value = value.get(prop_name)
            prop_errors = SubmissionHandler._validate_field(f"{field_name}.{prop_name}", prop_value, prop_config)
            errors.extend(prop_errors)
        
        return errors
    
    @staticmethod
    def _validate_business_rules(form_data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Apply business logic validation rules."""
        errors = []
        
        try:
            # Example business rules - customize based on your needs
            
            # Invoice-specific validations
            if 'invoice_amount' in form_data and 'subtotal' in form_data:
                invoice_amount = form_data.get('invoice_amount')
                subtotal = form_data.get('subtotal')
                
                if isinstance(invoice_amount, (int, float)) and isinstance(subtotal, (int, float)):
                    if invoice_amount < subtotal:
                        errors.append("Invoice amount cannot be less than subtotal")
            
            # Date consistency checks
            if 'invoice_date' in form_data and 'due_date' in form_data:
                invoice_date = form_data.get('invoice_date')
                due_date = form_data.get('due_date')
                
                if invoice_date and due_date:
                    try:
                        if isinstance(invoice_date, str):
                            invoice_dt = datetime.fromisoformat(invoice_date.replace('Z', '+00:00'))
                        else:
                            invoice_dt = datetime.combine(invoice_date, datetime.min.time())
                        
                        if isinstance(due_date, str):
                            due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        else:
                            due_dt = datetime.combine(due_date, datetime.min.time())
                        
                        if due_dt < invoice_dt:
                            errors.append("Due date cannot be before invoice date")
                    
                    except (ValueError, AttributeError):
                        # Date parsing errors are handled by field validation
                        pass
            
            # Tax calculation validation
            if all(k in form_data for k in ['subtotal', 'tax_amount', 'invoice_amount']):
                subtotal = form_data.get('subtotal')
                tax_amount = form_data.get('tax_amount')
                invoice_amount = form_data.get('invoice_amount')
                
                # Ensure values are present (not None) before attempting conversion.
                if subtotal is None or tax_amount is None or invoice_amount is None:
                    # Let field-level validation handle missing values; skip numeric rule here.
                    subtotal_num = tax_amount_num = invoice_amount_num = None
                else:
                    # Convert to floats safely — guard against non-numeric values.
                    try:
                        subtotal_num = float(subtotal)
                        tax_amount_num = float(tax_amount)
                        invoice_amount_num = float(invoice_amount)
                    except (TypeError, ValueError):
                        # Non-numeric values should be caught by field validation elsewhere; skip this rule here.
                        subtotal_num = tax_amount_num = invoice_amount_num = None
                
                if subtotal_num is not None and tax_amount_num is not None and invoice_amount_num is not None:
                    expected_total = subtotal_num + tax_amount_num
                    # Allow small rounding differences
                    if abs(invoice_amount_num - expected_total) > 0.01:
                        errors.append(f"Invoice amount ({invoice_amount_num}) should equal subtotal + tax ({expected_total})")
        
        except Exception as e:
            logger.error(f"Business rule validation error: {e}")
            errors.append("Business rule validation failed")
        
        return errors
    
    @staticmethod
    def _validate_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate a single field with comprehensive error reporting"""
        errors = []
        field_type = field_config.get("type")
        required = field_config.get("required", False)
        label = field_config.get('label', field_name)
        
        # Check required fields
        if required and (value is None or value == "" or (isinstance(value, list) and len(value) == 0)):
            errors.append({
                "field_path": field_name,
                "error_type": "Required Field",
                "message": f"'{label}' is required but is missing or empty",
                "suggestion": f"Provide a value for {label}"
            })
            return errors  # Don't continue validation if required field is missing
        
        # Skip validation if field is optional and empty
        if not required and (value is None or value == ""):
            return errors
        
        # Type-specific validation
        if field_type == "array":
            array_errors = SubmissionHandler._validate_array_field_comprehensive(field_name, value, field_config)
            errors.extend(array_errors)
        elif field_type == "string":
            string_errors = SubmissionHandler._validate_string_field_comprehensive(field_name, value, field_config)
            errors.extend(string_errors)
        elif field_type in ["number", "integer"]:
            numeric_errors = SubmissionHandler._validate_numeric_field_comprehensive(field_name, value, field_config)
            errors.extend(numeric_errors)
        elif field_type == "boolean":
            boolean_errors = SubmissionHandler._validate_boolean_field_comprehensive(field_name, value, field_config)
            errors.extend(boolean_errors)
        elif field_type == "date":
            date_errors = SubmissionHandler._validate_date_field_comprehensive(field_name, value, field_config)
            errors.extend(date_errors)
        elif field_type == "enum":
            enum_errors = SubmissionHandler._validate_enum_field_comprehensive(field_name, value, field_config)
            errors.extend(enum_errors)
        
        return errors
    
    @staticmethod
    def _validate_array_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Comprehensive validation for array fields"""
        errors = []
        label = field_config.get('label', field_name)
        
        # Check if value is actually an array
        if not isinstance(value, list):
            errors.append({
                "field_path": field_name,
                "error_type": "Type Error",
                "message": f"'{label}' must be an array, got {type(value).__name__}",
                "suggestion": "Ensure the field contains a JSON array (e.g., [\"item1\", \"item2\"])"
            })
            return errors
        
        items_config = field_config.get("items", {})
        items_type = items_config.get("type")
        
        # Validate each item in the array
        for i, item in enumerate(value):
            item_path = f"{field_name}[{i}]"
            
            if items_type == "object":
                # Validate object items
                properties = items_config.get("properties", {})
                if not isinstance(item, dict):
                    errors.append({
                        "field_path": item_path,
                        "error_type": "Type Error",
                        "message": f"Array item at {item_path} must be an object, got {type(item).__name__}",
                        "suggestion": "Ensure array items are JSON objects with properties"
                    })
                    continue
                
                # Validate object properties
                for prop_name, prop_config in properties.items():
                    prop_path = f"{item_path}.{prop_name}"
                    prop_value = item.get(prop_name)
                    prop_errors = SubmissionHandler._validate_field_comprehensive(prop_path, prop_value, prop_config)
                    errors.extend(prop_errors)
            else:
                # Validate scalar items
                item_errors = SubmissionHandler._validate_scalar_item_comprehensive(item_path, item, items_config)
                errors.extend(item_errors)
        
        return errors
    
    @staticmethod
    def _validate_scalar_item_comprehensive(item_path: str, value: Any, items_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Comprehensive validation for scalar array items"""
        errors = []
        item_type = items_config.get("type", "string")
        
        # Type validation with detailed messages
        if item_type == "string":
            if not isinstance(value, str):
                errors.append({
                    "field_path": item_path,
                    "error_type": "Type Error",
                    "message": f"Item at {item_path} must be a string, got {type(value).__name__}",
                    "suggestion": "Ensure the value is enclosed in quotes"
                })
                return errors
            
            # String constraints
            min_length = items_config.get("min_length")
            if min_length is not None and len(value) < min_length:
                errors.append({
                    "field_path": item_path,
                    "error_type": "Length Constraint",
                    "message": f"Item at {item_path} must be at least {min_length} characters long, got {len(value)}",
                    "suggestion": f"Add more characters to reach minimum length of {min_length}"
                })
            
            max_length = items_config.get("max_length")
            if max_length is not None and len(value) > max_length:
                errors.append({
                    "field_path": item_path,
                    "error_type": "Length Constraint",
                    "message": f"Item at {item_path} must be no more than {max_length} characters long, got {len(value)}",
                    "suggestion": f"Shorten the text to {max_length} characters or less"
                })
            
            pattern = items_config.get("pattern")
            if pattern and value:
                try:
                    if not re.match(pattern, value):
                        errors.append({
                            "field_path": item_path,
                            "error_type": "Pattern Constraint",
                            "message": f"Item at {item_path} must match pattern '{pattern}', got '{value}'",
                            "suggestion": f"Ensure the value follows the required pattern: {pattern}"
                        })
                except re.error:
                    logger.error(f"Invalid regex pattern for item {item_path}: {pattern}")
        
        elif item_type in ["number", "integer"]:
            try:
                numeric_value = float(value) if item_type == "number" else int(value)
            except (ValueError, TypeError):
                errors.append({
                    "field_path": item_path,
                    "error_type": "Type Error",
                    "message": f"Item at {item_path} must be a valid {item_type}, got '{value}'",
                    "suggestion": f"Provide a numeric value (e.g., 42 for integer, 42.5 for number)"
                })
                return errors
            
            min_value = items_config.get("min_value")
            if min_value is not None and numeric_value < min_value:
                errors.append({
                    "field_path": item_path,
                    "error_type": "Range Constraint",
                    "message": f"Item at {item_path} must be at least {min_value}, got {numeric_value}",
                    "suggestion": f"Use a value of {min_value} or higher"
                })
            
            max_value = items_config.get("max_value")
            if max_value is not None and numeric_value > max_value:
                errors.append({
                    "field_path": item_path,
                    "error_type": "Range Constraint",
                    "message": f"Item at {item_path} must be no more than {max_value}, got {numeric_value}",
                    "suggestion": f"Use a value of {max_value} or lower"
                })
        
        elif item_type == "boolean":
            if not isinstance(value, bool):
                errors.append({
                    "field_path": item_path,
                    "error_type": "Type Error",
                    "message": f"Item at {item_path} must be a boolean, got {type(value).__name__}",
                    "suggestion": "Use true or false (without quotes)"
                })
        
        elif item_type == "date":
            if isinstance(value, str):
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    errors.append({
                        "field_path": item_path,
                        "error_type": "Format Error",
                        "message": f"Item at {item_path} must be a valid date in YYYY-MM-DD format, got '{value}'",
                        "suggestion": "Use format like '2024-01-15'"
                    })
            elif not isinstance(value, date):
                errors.append({
                    "field_path": item_path,
                    "error_type": "Type Error",
                    "message": f"Item at {item_path} must be a valid date, got {type(value).__name__}",
                    "suggestion": "Use date format YYYY-MM-DD in quotes"
                })
        
        elif item_type == "enum":
            choices = items_config.get("choices", [])
            if value not in choices:
                choices_str = ', '.join(str(c) for c in choices)
                errors.append({
                    "field_path": item_path,
                    "error_type": "Enum Constraint",
                    "message": f"Item at {item_path} must be one of: {choices_str}, got '{value}'",
                    "suggestion": f"Choose from the available options: {choices_str}"
                })
        
        return errors
    
    @staticmethod
    def _validate_string_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Comprehensive validation for string fields"""
        errors = []
        label = field_config.get('label', field_name)
        
        if not isinstance(value, str):
            errors.append({
                "field_path": field_name,
                "error_type": "Type Error",
                "message": f"'{label}' must be a string, got {type(value).__name__}",
                "suggestion": "Enclose the value in quotes"
            })
            return errors
        
        # Apply same string validation as scalar items
        string_errors = SubmissionHandler._validate_scalar_item_comprehensive(field_name, value, field_config)
        return string_errors
    
    @staticmethod
    def _validate_numeric_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Comprehensive validation for numeric fields"""
        errors = []
        label = field_config.get('label', field_name)
        field_type = field_config.get('type', 'number')
        
        try:
            numeric_value = float(value) if field_type == "number" else int(value)
        except (ValueError, TypeError):
            errors.append({
                "field_path": field_name,
                "error_type": "Type Error",
                "message": f"'{label}' must be a valid {field_type}, got '{value}'",
                "suggestion": f"Provide a numeric value (e.g., 42 for integer, 42.5 for number)"
            })
            return errors
        
        # Apply same numeric validation as scalar items
        numeric_errors = SubmissionHandler._validate_scalar_item_comprehensive(field_name, numeric_value, field_config)
        return numeric_errors
    
    @staticmethod
    def _validate_boolean_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Comprehensive validation for boolean fields"""
        errors = []
        label = field_config.get('label', field_name)
        
        if not isinstance(value, bool):
            errors.append({
                "field_path": field_name,
                "error_type": "Type Error",
                "message": f"'{label}' must be a boolean, got {type(value).__name__}",
                "suggestion": "Use true or false (without quotes)"
            })
        
        return errors
    
    @staticmethod
    def _validate_date_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Comprehensive validation for date fields"""
        errors = []
        label = field_config.get('label', field_name)
        
        if isinstance(value, str):
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                errors.append({
                    "field_path": field_name,
                    "error_type": "Format Error",
                    "message": f"'{label}' must be a valid date in YYYY-MM-DD format, got '{value}'",
                    "suggestion": "Use format like '2024-01-15'"
                })
        elif not isinstance(value, date):
            errors.append({
                "field_path": field_name,
                "error_type": "Type Error",
                "message": f"'{label}' must be a valid date, got {type(value).__name__}",
                "suggestion": "Use date format YYYY-MM-DD in quotes"
            })
        
        return errors
    
    @staticmethod
    def _validate_enum_field_comprehensive(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Comprehensive validation for enum fields"""
        errors = []
        label = field_config.get('label', field_name)
        choices = field_config.get('choices', [])
        
        if value not in choices:
            choices_str = ', '.join(str(c) for c in choices)
            errors.append({
                "field_path": field_name,
                "error_type": "Enum Constraint",
                "message": f"'{label}' must be one of: {choices_str}, got '{value}'",
                "suggestion": f"Choose from the available options: {choices_str}"
            })
        
        return errors
    
    @staticmethod
    def comprehensive_validate_data(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive validation of data against schema with detailed error reporting
        
        Returns:
            Dict with 'is_valid' boolean and 'errors' list with detailed error information
        """
        errors = []
        fields = schema.get("fields", {})
        
        # Validate each field in the schema
        for field_name, field_config in fields.items():
            field_errors = SubmissionHandler._validate_field_comprehensive(field_name, data.get(field_name), field_config)
            errors.extend(field_errors)
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    @staticmethod
    def _create_audit_entry(
        filename: str,
        original_data: Dict[str, Any],
        form_data: Dict[str, Any],
        user: str,
        diff: Dict[str, Any],
        deprecated_fields_ignored: Optional[List[str]] = None,
        schema_version: Optional[Any] = None
    ) -> bool:
        """Create and save audit entry. Includes deprecated fields and schema version if provided."""
        try:
            audit_entry = create_audit_diff_entry(original_data, form_data)
            audit_entry.update({
                'filename': filename,
                'timestamp': datetime.now().isoformat(),
                'user': user,
                'action': 'corrected',
                'submission_method': 'manual_review'
            })
            # Add runtime metadata about deprecated/ignored fields and schema version
            if deprecated_fields_ignored:
                audit_entry['deprecated_fields_ignored'] = deprecated_fields_ignored
            if schema_version is not None:
                audit_entry['schema_version'] = schema_version
            
            return append_audit_log(audit_entry)
        
        except Exception as e:
            logger.error(f"Failed to create audit entry: {e}")
            return False
    
    @staticmethod
    def handle_streamlit_submission() -> bool:
        """Handle submission from Streamlit interface."""
        try:
            import json
            from .form_generator import FormGenerator
            
            # Get filename and user from session
            filename = SessionManager.get_current_file()
            user = SessionManager.get_current_user()
            schema = SessionManager.get_schema()
            
            # Get the form data using the same approach as FormGenerator
            if not schema:
                logger.error("No schema available for form data collection")
                Notify.error("Schema not available")
                return False
            
            # Get current form data as base
            current_data = SessionManager.get_form_data() or {}
            
            # Collect all form field values from session state
            form_data = {}
            for field_name, field_config in schema.get('fields', {}).items():
                field_key = f"field_{field_name}"
                array_key = f"array_{field_name}"
                json_array_key = f"json_array_{field_name}"
                json_object_key = f"json_object_{field_name}"

                # Get value from session state, prioritizing field_ prefixed keys
                if field_key in st.session_state:
                    value = st.session_state[field_key]
                    if value is not None:  # Only set if value is not None
                        form_data[field_name] = value
                        logger.debug(f"Collected field {field_name} = {form_data[field_name]}")
                        if field_name == 'Currency':
                            logger.info(f"Currency field collected: {value}")
                    continue

                # Handle array fields
                if field_config.get('type') == 'array':
                    if array_key in st.session_state:
                        form_data[field_name] = st.session_state[array_key]
                        logger.debug(f"Collected array value {field_name}: {form_data[field_name]}")
                    elif json_array_key in st.session_state:
                        try:
                            value = st.session_state[json_array_key]
                            if isinstance(value, str):
                                form_data[field_name] = json.loads(value)
                            else:
                                form_data[field_name] = value
                            logger.debug(f"Collected JSON array value {field_name}: {form_data[field_name]}")
                        except Exception as e:
                            logger.warning(f"Error processing array field {field_name}: {e}")
                
                # Handle object fields
                elif field_config.get('type') == 'object':
                    object_key = f"json_object_{field_name}"
                    if object_key in st.session_state:
                        try:
                            value = st.session_state[object_key]
                            if isinstance(value, str):
                                form_data[field_name] = json.loads(value)
                            else:
                                form_data[field_name] = value
                        except Exception as e:
                            logger.warning(f"Error processing object field {field_name}: {e}")
            
            # Log collected form data
            logger.debug(f"Collected form data for submission: {form_data}")
            
            # Update session state with collected form data
            SessionManager.set_form_data(form_data)
            
            # Process any fields that might be in session_state but weren't caught by the schema iteration
            for key in st.session_state:
                if key.startswith('field_'):
                    field_name = key[6:]  # Remove 'field_' prefix
                    if field_name not in form_data and st.session_state[key] is not None:
                        form_data[field_name] = st.session_state[key]
                        logger.debug(f"Added additional field {field_name} = {form_data[field_name]}")
            
            # Build final payload restricted to schema fields and include schema_version
            schema_fields = st.session_state.get("schema_fields", set())
            deprecated = st.session_state.get("deprecated_fields_current_doc", [])
            final_payload = SubmissionHandler.build_corrected_payload(SessionManager.get_form_data(), schema_fields, {})
            # Persist final payload into session so UI reflects what will be saved
            SessionManager.set_form_data(final_payload)
            form_data = final_payload

            # Special handling for Currency field to ensure it's not null when changed
            if "field_Currency" in st.session_state and st.session_state["field_Currency"] is not None:
                form_data["Currency"] = st.session_state["field_Currency"]
                logger.debug(f"Setting Currency field value: {form_data['Currency']}")

            # Set default values from schema if not present in form_data
            for field_name, field_config in schema.get('fields', {}).items():
                if field_name not in form_data and 'default' in field_config:
                    form_data[field_name] = field_config['default']
                    logger.debug(f"Setting default value for {field_name}: {field_config['default']}")

            # Final check to ensure Currency is not null if it exists in session state
            if "field_Currency" in st.session_state and st.session_state["field_Currency"]:
                form_data["Currency"] = st.session_state["field_Currency"]

            original_data = SessionManager.get_original_data()
            schema = SessionManager.get_schema()
            model_class = SessionManager.get_model_class()
            
            if not all([filename, form_data, original_data, schema]):
                st.error("❌ Missing required data for submission")
                return False

            # Persist merged form_data into session so UI reflects latest edits
            SessionManager.set_form_data(form_data)

            # Run validation check first (as if "Validate Data" button was clicked)
            validation_errors = SubmissionHandler._validate_submission_data(form_data, schema, model_class)
            if validation_errors:
                # Throw error message and do not proceed to submit
                logger.info(f"Submission blocked - validation errors for {filename}: {validation_errors}")
                SessionManager.set_validation_errors(validation_errors)
                error_details = "; ".join(validation_errors)
                Notify.error(f"Validation failed: {error_details}. Please fix errors before submitting.")
                return False
            else:
                # Clear any previous validation errors
                SessionManager.clear_validation_errors()
                Notify.success("✅ Validation passed. Proceeding with save...")

            # Proceed to save since validation passed
            assert filename is not None and isinstance(filename, str)
            success, errors = SubmissionHandler.validate_and_submit(
                filename, form_data, original_data, schema, model_class, user
            )
            
            if success:
                # Clear session state
                SessionManager._clear_file_state()
                SessionManager.set_current_page('queue')
                
                Notify.success("Saved changes")
                st.balloons()
                return True
            else:
                # Rare: errors from save step
                SessionManager.set_validation_errors(errors)
                error_details = "; ".join(errors)
                Notify.error(f"Save failed: {error_details}")
                return False

        except Exception as e:
            error_msg = f"Submission error: {str(e)}"
            Notify.error(f"Save failed: {error_msg}")
            logger.error(error_msg, exc_info=True)
            return False
    
    @staticmethod
    def handle_cancel_submission() -> bool:
        """Handle cancellation of editing session."""
        try:
            filename = SessionManager.get_current_file()
            
            # Check for unsaved changes
            if SessionManager.has_unsaved_changes():
                st.warning("⚠️ You have unsaved changes that will be lost!")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Discard Changes", type="secondary"):
                        return SubmissionHandler._confirm_cancel()
                with col2:
                    st.info("Click 'Discard Changes' to confirm")
                return False
            else:
                return SubmissionHandler._confirm_cancel()
        
        except Exception as e:
            st.error(f"Error cancelling: {str(e)}")
            logger.error(f"Error cancelling: {e}", exc_info=True)
            return False
    
    @staticmethod
    def _confirm_cancel() -> bool:
        """Confirm cancellation and cleanup."""
        try:
            filename = SessionManager.get_current_file()
            
            if filename:
                release_file(filename)
            
            # Clear session state
            SessionManager._clear_file_state()
            SessionManager.set_current_page('queue')
            
            st.info("✅ Editing cancelled, file released")
            return True
        
        except Exception as e:
            st.error(f"Error confirming cancel: {str(e)}")
            logger.error(f"Error confirming cancel: {e}", exc_info=True)
            return False


# Convenience functions
def validate_and_submit_data(
    filename: str,
    form_data: Dict[str, Any],
    original_data: Dict[str, Any],
    schema: Dict[str, Any],
    model_class: Optional[Any] = None,
    user: str = "unknown"
) -> Tuple[bool, List[str]]:
    """Convenience function for validation and submission."""
    return SubmissionHandler.validate_and_submit(
        filename, form_data, original_data, schema, model_class, user
    )


def handle_streamlit_submission() -> bool:
    """Convenience function for Streamlit submission handling."""
    return SubmissionHandler.handle_streamlit_submission()


def handle_cancel_submission() -> bool:
    """Convenience function for Streamlit cancellation handling."""
    return SubmissionHandler.handle_cancel_submission()
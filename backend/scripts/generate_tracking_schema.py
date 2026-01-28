#!/usr/bin/env python3
"""
Generate frontend tracking schema from backend Pydantic models.

This script extracts stage data schemas from tracking_routes.py and generates
a JavaScript file for the frontend with field metadata for form rendering.

Exports:
- STAGE_FIELDS: Per-stage field schemas for form rendering
- METADATA_FIELDS: Job metadata fields (salary, location, general_note)

Usage:
    python scripts/generate_tracking_schema.py

Output:
    ../frontend/src/types/trackingSchema.js
"""

import ast
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Output path
OUTPUT_PATH = BACKEND_DIR.parent / "frontend" / "src" / "types" / "trackingSchema.js"


def extract_pydantic_fields(source_code: str, class_name: str) -> dict:
    """Extract field definitions from a Pydantic model class."""
    tree = ast.parse(source_code)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields = {}
            for item in node.body:
                # Look for annotated assignments (field: Type = default)
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    field_info = parse_field_annotation(item.annotation, item.value)
                    if field_info:
                        fields[field_name] = field_info
            return fields
    return {}


def parse_field_annotation(annotation, default_value) -> dict | None:
    """Parse a field annotation to extract type info."""
    # Handle Optional[X] -> extract X
    type_str = ast.unparse(annotation) if annotation else ""

    # Determine field type
    if "datetime" in type_str:
        field_type = "datetime"
    elif "Literal[" in type_str:
        # Extract literal options
        options = extract_literal_options(type_str)
        field_type = "select"
    else:
        field_type = "text"

    result = {"type": field_type}

    # Extract options for Literal types
    if field_type == "select":
        result["options"] = extract_literal_options(type_str)

    # Extract default value
    if default_value:
        default = extract_default_value(default_value)
        if default is not None:
            result["default"] = default

    return result


def extract_literal_options(type_str: str) -> list:
    """Extract options from Literal["a", "b", "c"] or Literal['a', 'b'] type string."""
    import re
    match = re.search(r'Literal\[(.*?)\]', type_str)
    if match:
        content = match.group(1)
        # Extract quoted strings (both single and double quotes)
        return re.findall(r'["\']([^"\']*)["\']', content)
    return []


def extract_default_value(node):
    """Extract default value from AST node."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Str):  # Python 3.7 compatibility
        return node.s
    return None


def get_stage_schemas() -> dict:
    """Import and extract stage schemas from tracking_routes.py."""
    tracking_routes_path = BACKEND_DIR / "api" / "tracking_routes.py"
    source_code = tracking_routes_path.read_text()

    # Find STAGE_SCHEMAS dict
    tree = ast.parse(source_code)
    stage_names = []

    for node in ast.walk(tree):
        # Handle regular assignment: STAGE_SCHEMAS = {...}
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "STAGE_SCHEMAS":
                    if isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant):
                                stage_names.append(key.value)
        # Handle annotated assignment: STAGE_SCHEMAS: dict[...] = {...}
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "STAGE_SCHEMAS":
                if isinstance(node.value, ast.Dict):
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant):
                            stage_names.append(key.value)

    # Extract field definitions for each stage
    schemas = {}
    for stage_name in stage_names:
        class_name = f"{stage_name.capitalize()}Data"
        fields = extract_pydantic_fields(source_code, class_name)
        if fields:
            schemas[stage_name] = fields

    return schemas


def get_tracking_notes_schema() -> dict:
    """Extract TrackingNotes schema."""
    tracking_routes_path = BACKEND_DIR / "api" / "tracking_routes.py"
    source_code = tracking_routes_path.read_text()
    return extract_pydantic_fields(source_code, "TrackingNotes")


def generate_label(field_name: str) -> str:
    """Generate a human-readable label from field name."""
    label_map = {
        "datetime": "Date & Time",
        "type": "Type",
        "referrer_name": "Referrer Name",
        "referrer_content": "Referral Details",
        "note": "Note",
        "with_person": "With",
        "round": "Round",
        "interviewers": "Interviewers",
        "contacts_provided": "Contacts Provided",
        "amount": "Amount",
        "decision": "Decision",
        "salary": "Salary",
        "location": "Location",
        "general_note": "General Note",
    }
    return label_map.get(field_name, field_name.replace("_", " ").title())


def generate_js_output(stage_schemas: dict, notes_schema: dict) -> str:
    """Generate JavaScript module content."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "/**",
        " * Auto-generated tracking schema for frontend form rendering.",
        f" * Generated: {timestamp}",
        " * Source: backend/api/tracking_routes.py",
        " *",
        " * DO NOT EDIT MANUALLY - run `jcodegen` to regenerate.",
        " */",
        "",
        "// Stage field schemas for form rendering",
        "export const STAGE_FIELDS = {",
    ]

    for stage_name, fields in stage_schemas.items():
        lines.append(f"  {stage_name}: {{")
        for field_name, field_info in fields.items():
            label = generate_label(field_name)
            field_type = field_info["type"]

            field_def = [f"type: '{field_type}'", f"label: '{label}'"]

            if "options" in field_info:
                options_str = repr(field_info["options"])
                field_def.append(f"options: {options_str}")

            if "default" in field_info and field_info["default"] is not None:
                default_val = repr(field_info["default"])
                field_def.append(f"default: {default_val}")

            # Add conditional visibility for referral fields
            if field_name in ("referrer_name", "referrer_content"):
                field_def.append("showIf: (data) => data.type === 'referral'")

            lines.append(f"    {field_name}: {{ {', '.join(field_def)} }},")
        lines.append("  },")

    lines.append("};")
    lines.append("")

    # Add metadata fields
    lines.append("// Job metadata fields (always editable)")
    lines.append("export const METADATA_FIELDS = {")

    # Filter out 'stages' from notes schema
    metadata_fields = {k: v for k, v in notes_schema.items() if k != "stages"}
    for field_name, field_info in metadata_fields.items():
        label = generate_label(field_name)
        field_type = field_info["type"]
        lines.append(f"  {field_name}: {{ type: '{field_type}', label: '{label}' }},")

    lines.append("};")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    print("Generating frontend tracking schema...")

    # Extract schemas
    stage_schemas = get_stage_schemas()
    notes_schema = get_tracking_notes_schema()

    if not stage_schemas:
        print("  ERROR: Could not extract stage schemas")
        return 1

    print(f"  Found {len(stage_schemas)} stage schemas: {list(stage_schemas.keys())}")

    # Generate output
    js_content = generate_js_output(stage_schemas, notes_schema)

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Check if file changed
    if OUTPUT_PATH.exists():
        existing_content = OUTPUT_PATH.read_text()
        # Compare without timestamp line
        def strip_timestamp(s):
            lines = s.split("\n")
            return "\n".join(l for l in lines if not l.startswith(" * Generated:"))

        if strip_timestamp(existing_content) == strip_timestamp(js_content):
            print(f"  {OUTPUT_PATH} (unchanged)")
            return 0

    # Write output
    OUTPUT_PATH.write_text(js_content)
    print(f"  {OUTPUT_PATH} (updated)")
    return 1  # Return 1 to indicate file was modified


if __name__ == "__main__":
    sys.exit(main())

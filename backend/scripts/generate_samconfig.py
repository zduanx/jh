#!/usr/bin/env python3
"""
Generate samconfig.toml from .sam-config and .env.local

This script parses:
- .sam-config: Stack name, region, capabilities
- .env.local: Production values from VARIABLE_NAME_PROD_VALUE comments

Outputs:
- samconfig.toml: SAM CLI deployment configuration
"""

import os
import re
import sys
from pathlib import Path


def parse_env_file(filepath):
    """Parse key=value file, ignoring comments and empty lines."""
    config = {}
    if not os.path.exists(filepath):
        return config

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

    return config


def parse_env_local_prod_values(filepath):
    """
    Parse .env.local to extract production values and parameter names.

    Returns a dict with structure:
    {
        'GoogleClientId': 'production_value',
        'JWTSecretKey': 'production_value',
        ...
    }

    Keys are the CloudFormation parameter names, values are the PROD_VALUE
    """
    # First pass: collect all metadata for each variable
    var_metadata = {}
    current_var = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()

            # Match environment variable definition
            if '=' in line and not line.startswith('#'):
                var_name = line.split('=', 1)[0].strip()
                if var_name.isupper():
                    current_var = var_name
                    if current_var not in var_metadata:
                        var_metadata[current_var] = {}

            # Match metadata comments
            if line.startswith('#') and current_var:
                # Extract PROD_VALUE
                match = re.match(r'#\s*([A-Z_]+)_PROD_VALUE\s*=\s*(.+)', line)
                if match and match.group(1) == current_var:
                    var_metadata[current_var]['PROD_VALUE'] = match.group(2).strip()
                    continue

                # Extract PARAM_NAME
                match = re.match(r'#\s*([A-Z_]+)_PARAM_NAME\s*=\s*(.+)', line)
                if match and match.group(1) == current_var:
                    var_metadata[current_var]['PARAM_NAME'] = match.group(2).strip()
                    continue

    # Second pass: build prod_values dict with CloudFormation parameter names
    prod_values = {}
    for var_name, metadata in var_metadata.items():
        if 'PARAM_NAME' in metadata and 'PROD_VALUE' in metadata:
            param_name = metadata['PARAM_NAME']
            prod_value = metadata['PROD_VALUE']
            prod_values[param_name] = prod_value

    return prod_values


def escape_toml_value(value):
    """Escape special characters for TOML string values."""
    # Escape backslashes and quotes
    value = value.replace('\\', '\\\\')
    value = value.replace('"', '\\"')
    return value


def generate_samconfig_toml(sam_config, prod_values):
    """Generate samconfig.toml content."""

    # Extract configuration
    stack_name = sam_config.get('CFN_STACK_NAME', 'jh-backend-stack')
    region = sam_config.get('CFN_REGION', 'us-east-1')
    capabilities = sam_config.get('CFN_CAPABILITIES', 'CAPABILITY_IAM')

    # Build parameter_overrides string
    # Format: Key1=\"Value1\" Key2=\"Value2\" ...
    param_parts = []
    for param_name in sorted(prod_values.keys()):
        value = escape_toml_value(prod_values[param_name])
        param_parts.append(f'{param_name}=\\"{value}\\"')

    parameter_overrides = ' '.join(param_parts)

    # Generate TOML
    toml_lines = [
        "version = 0.1",
        "[default]",
        "[default.deploy]",
        "[default.deploy.parameters]",
        f'stack_name = "{stack_name}"',
        "resolve_s3 = true",
        f'region = "{region}"',
        f'capabilities = "{capabilities}"',
        f'parameter_overrides = "{parameter_overrides}"',
        "confirm_changeset = false",
        ""
    ]

    return '\n'.join(toml_lines)


def main():
    # Get paths
    backend_dir = Path(__file__).parent.parent
    sam_config_path = backend_dir / '.sam-config'
    env_local_path = backend_dir / '.env.local'
    samconfig_path = backend_dir / 'samconfig.toml'

    # Parse configuration files
    sam_config = parse_env_file(sam_config_path)
    prod_values = parse_env_local_prod_values(env_local_path)

    # Generate samconfig.toml content
    new_content = generate_samconfig_toml(sam_config, prod_values)

    # Check if file exists and compare content
    if samconfig_path.exists():
        with open(samconfig_path, 'r') as f:
            existing_content = f.read()

        if existing_content == new_content:
            print("✓ samconfig.toml (no changes)")
            sys.exit(0)  # No changes
        else:
            # Write the new content
            with open(samconfig_path, 'w') as f:
                f.write(new_content)
            print("⚠ samconfig.toml modified")
            sys.exit(1)  # Modified
    else:
        # Write the new content
        with open(samconfig_path, 'w') as f:
            f.write(new_content)
        print("⚠ samconfig.toml created (new file)")
        sys.exit(2)  # New file


if __name__ == '__main__':
    main()

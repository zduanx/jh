#!/usr/bin/env python3
"""
Generate template.yaml from .sam-config and .env.local

This script parses:
- .sam-config: Deployment metadata (stack name, Lambda config, API config, static env vars)
- .env.local: Environment variable metadata (PARAM_NAME, DESCRIPTION, NO_ECHO, DEFAULT)

Outputs:
- template.yaml: AWS SAM CloudFormation template
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


def parse_env_local_comments(filepath):
    """
    Parse .env.local to extract environment variable metadata from comments.

    Returns a dict with structure:
    {
        'GOOGLE_CLIENT_ID': {
            'PROD_VALUE': 'xxx',
            'PARAM_NAME': 'GoogleClientId',
            'DESCRIPTION': 'Google OAuth Client ID',
            'NO_ECHO': 'false',
            'DEFAULT': 'optional_default_value'
        },
        ...
    }
    """
    env_metadata = {}
    current_var = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()

            # Match environment variable definition
            if '=' in line and not line.startswith('#'):
                var_name = line.split('=', 1)[0].strip()
                # Skip non-uppercase vars or ones that don't look like env vars
                if var_name.isupper() and '_' in var_name or var_name in ['ALGORITHM']:
                    current_var = var_name
                    if current_var not in env_metadata:
                        env_metadata[current_var] = {}

            # Match metadata comments
            if line.startswith('#') and current_var:
                # Extract VARIABLE_NAME_METADATA=value patterns
                match = re.match(r'#\s*([A-Z_]+)_PROD_VALUE\s*=\s*(.+)', line)
                if match and match.group(1) == current_var:
                    env_metadata[current_var]['PROD_VALUE'] = match.group(2).strip()
                    continue

                match = re.match(r'#\s*([A-Z_]+)_PARAM_NAME\s*=\s*(.+)', line)
                if match and match.group(1) == current_var:
                    env_metadata[current_var]['PARAM_NAME'] = match.group(2).strip()
                    continue

                match = re.match(r'#\s*([A-Z_]+)_DESCRIPTION\s*=\s*(.+)', line)
                if match and match.group(1) == current_var:
                    env_metadata[current_var]['DESCRIPTION'] = match.group(2).strip()
                    continue

                match = re.match(r'#\s*([A-Z_]+)_NO_ECHO\s*=\s*(.+)', line)
                if match and match.group(1) == current_var:
                    env_metadata[current_var]['NO_ECHO'] = match.group(2).strip()
                    continue

                match = re.match(r'#\s*([A-Z_]+)_DEFAULT\s*=\s*(.+)', line)
                if match and match.group(1) == current_var:
                    env_metadata[current_var]['DEFAULT'] = match.group(2).strip()
                    continue

    return env_metadata


def generate_template_yaml(sam_config, env_metadata, static_env_vars):
    """Generate template.yaml content."""

    # Extract configuration
    function_name = sam_config.get('LAMBDA_FUNCTION_NAME', 'JobHuntTrackerAPI')
    function_desc = sam_config.get('LAMBDA_FUNCTION_DESCRIPTION', 'FastAPI backend for Job Hunt Tracker')
    handler = sam_config.get('LAMBDA_HANDLER', 'main.handler')
    timeout = sam_config.get('LAMBDA_TIMEOUT', '30')
    memory = sam_config.get('LAMBDA_MEMORY', '512')
    runtime = sam_config.get('LAMBDA_RUNTIME', 'python3.13')
    code_uri = sam_config.get('LAMBDA_CODE_URI', '.')
    api_stage = sam_config.get('API_STAGE_NAME', 'prod')
    cors_origins = sam_config.get('API_CORS_ALLOW_ORIGINS', 'http://localhost:3000,https://zduan-job.vercel.app')

    # Split CORS origins for YAML list
    cors_origin_list = [f'"{origin.strip()}"' for origin in cors_origins.split(',')]

    # Start building YAML
    yaml_lines = [
        "AWSTemplateFormatVersion: '2010-09-09'",
        "Transform: AWS::Serverless-2016-10-31",
        f"Description: {function_desc}",
        "",
        "Globals:",
        "  Function:",
        f"    Timeout: {timeout}",
        f"    MemorySize: {memory}",
        f"    Runtime: {runtime}",
        "    Environment:",
        "      Variables:",
    ]

    # Add environment variables (parameterized ones reference !Ref, static ones are hardcoded)
    env_var_lines = []

    # Add parameterized environment variables
    for var_name, metadata in sorted(env_metadata.items()):
        if 'PARAM_NAME' in metadata:
            param_name = metadata['PARAM_NAME']
            env_var_lines.append(f"        {var_name}: !Ref {param_name}")

    # Add static environment variables
    for key, value in sorted(static_env_vars.items()):
        if key.startswith('ENV_VAR_'):
            var_name = key.replace('ENV_VAR_', '')
            env_var_lines.append(f"        {var_name}: {value}")

    yaml_lines.extend(env_var_lines)
    yaml_lines.append("")

    # Add Parameters section
    yaml_lines.append("Parameters:")

    for var_name, metadata in sorted(env_metadata.items()):
        if 'PARAM_NAME' not in metadata:
            continue

        param_name = metadata['PARAM_NAME']
        description = metadata.get('DESCRIPTION', f'{var_name} value')
        no_echo = metadata.get('NO_ECHO', 'false')
        default = metadata.get('DEFAULT')

        yaml_lines.append(f"  {param_name}:")
        yaml_lines.append("    Type: String")
        yaml_lines.append(f"    Description: {description}")
        yaml_lines.append(f"    NoEcho: {no_echo}")
        if default:
            yaml_lines.append(f'    Default: "{default}"')
        yaml_lines.append("")

    # Add Resources section
    yaml_lines.extend([
        "Resources:",
        f"  {function_name}:",
        "    Type: AWS::Serverless::Function",
        "    Properties:",
        f"      FunctionName: {function_name}",
        f"      CodeUri: {code_uri}",
        f"      Handler: {handler}",
        f"      Description: {function_desc}",
        "      Events:",
        "        HttpApiEvent:",
        "          Type: HttpApi",
        "          Properties:",
        "            Path: /{proxy+}",
        "            Method: ANY",
        "            ApiId: !Ref HttpApi",
        "        RootEvent:",
        "          Type: HttpApi",
        "          Properties:",
        "            Path: /",
        "            Method: ANY",
        "            ApiId: !Ref HttpApi",
        "",
        "  HttpApi:",
        "    Type: AWS::Serverless::HttpApi",
        "    Properties:",
        f"      StageName: {api_stage}",
        "      CorsConfiguration:",
        "        AllowOrigins:",
    ])

    # Add CORS origins
    for origin in cors_origin_list:
        yaml_lines.append(f"          - {origin}")

    yaml_lines.extend([
        "        AllowHeaders:",
        '          - "*"',
        "        AllowMethods:",
        "          - GET",
        "          - POST",
        "          - PUT",
        "          - DELETE",
        "          - OPTIONS",
        "        AllowCredentials: true",
        "",
        "Outputs:",
        "  ApiUrl:",
        "    Description: API Gateway endpoint URL",
        '    Value: !Sub "https://${HttpApi}.execute-api.${AWS::Region}.amazonaws.com/' + api_stage + '"',
        "",
        "  FunctionName:",
        "    Description: Lambda function name",
        f"    Value: !Ref {function_name}",
        "",
        "  FunctionArn:",
        "    Description: Lambda function ARN",
        f"    Value: !GetAtt {function_name}.Arn",
        ""
    ])

    return '\n'.join(yaml_lines)


def main():
    # Get paths
    backend_dir = Path(__file__).parent.parent
    sam_config_path = backend_dir / '.sam-config'
    env_local_path = backend_dir / '.env.local'
    template_path = backend_dir / 'template.yaml'

    # Parse configuration files
    sam_config = parse_env_file(sam_config_path)
    env_metadata = parse_env_local_comments(env_local_path)

    # Extract static env vars from sam_config
    static_env_vars = {k: v for k, v in sam_config.items() if k.startswith('ENV_VAR_')}

    # Generate template.yaml content
    new_content = generate_template_yaml(sam_config, env_metadata, static_env_vars)

    # Check if file exists and compare content
    if template_path.exists():
        with open(template_path, 'r') as f:
            existing_content = f.read()

        if existing_content == new_content:
            print("✓ template.yaml (no changes)")
            sys.exit(0)  # No changes
        else:
            # Write the new content
            with open(template_path, 'w') as f:
                f.write(new_content)
            print("⚠ template.yaml modified")
            sys.exit(1)  # Modified
    else:
        # Write the new content
        with open(template_path, 'w') as f:
            f.write(new_content)
        print("⚠ template.yaml created (new file)")
        sys.exit(2)  # New file


if __name__ == '__main__':
    main()

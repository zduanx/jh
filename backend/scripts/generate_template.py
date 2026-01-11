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

    # Extract API Lambda configuration
    function_name = sam_config.get('LAMBDA_FUNCTION_NAME', 'JobHuntTrackerAPI')
    function_desc = sam_config.get('LAMBDA_FUNCTION_DESCRIPTION', 'FastAPI backend for Job Hunt Tracker')
    handler = sam_config.get('LAMBDA_HANDLER', 'main.handler')
    timeout = sam_config.get('LAMBDA_TIMEOUT', '30')
    memory = sam_config.get('LAMBDA_MEMORY', '512')
    runtime = sam_config.get('LAMBDA_RUNTIME', 'python3.13')
    code_uri = sam_config.get('LAMBDA_CODE_URI', '.')
    api_stage = sam_config.get('API_STAGE_NAME', 'prod')
    cors_origins = sam_config.get('API_CORS_ALLOW_ORIGINS', 'http://localhost:3000,https://zduan-job.vercel.app')

    # Extract Worker Lambda configuration
    worker_name = sam_config.get('WORKER_FUNCTION_NAME', 'IngestionWorker')
    worker_desc = sam_config.get('WORKER_FUNCTION_DESCRIPTION', 'Async worker for job ingestion')
    worker_handler = sam_config.get('WORKER_HANDLER', 'workers.ingestion_worker.handler')
    worker_timeout = sam_config.get('WORKER_TIMEOUT', '900')
    worker_memory = sam_config.get('WORKER_MEMORY', '512')

    # Extract Crawler Worker configuration (Phase 2J)
    crawler_name = sam_config.get('CRAWLER_FUNCTION_NAME', 'CrawlerWorker')
    crawler_desc = sam_config.get('CRAWLER_FUNCTION_DESCRIPTION', 'SQS-triggered crawler worker')
    crawler_handler = sam_config.get('CRAWLER_HANDLER', 'workers.crawler_worker.handler')
    crawler_timeout = sam_config.get('CRAWLER_TIMEOUT', '60')
    crawler_memory = sam_config.get('CRAWLER_MEMORY', '512')

    # Extract Extractor Worker configuration (Phase 2K)
    extractor_name = sam_config.get('EXTRACTOR_FUNCTION_NAME', 'ExtractorWorker')
    extractor_desc = sam_config.get('EXTRACTOR_FUNCTION_DESCRIPTION', 'SQS-triggered extractor worker')
    extractor_handler = sam_config.get('EXTRACTOR_HANDLER', 'workers.extractor_worker.handler')
    extractor_timeout = sam_config.get('EXTRACTOR_TIMEOUT', '30')
    extractor_memory = sam_config.get('EXTRACTOR_MEMORY', '256')
    extractor_reserved_concurrency = sam_config.get('EXTRACTOR_RESERVED_CONCURRENCY', '5')

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
        "",
        "  # ==========================================================================",
        "  # API Lambda - HTTP endpoints via API Gateway",
        "  # ==========================================================================",
        f"  {function_name}:",
        "    Type: AWS::Serverless::Function",
        "    Properties:",
        f"      FunctionName: {function_name}",
        f"      CodeUri: {code_uri}",
        f"      Handler: {handler}",
        f"      Description: {function_desc}",
        "      Policies:",
        "        - LambdaInvokePolicy:",
        f"            FunctionName: !Ref {worker_name}",
        "      Environment:",
        "        Variables:",
        f"          WORKER_FUNCTION_NAME: !Ref {worker_name}",
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
        "  # ==========================================================================",
        "  # Worker Lambda - Async invoke for long-running ingestion (15 min timeout)",
        "  # ==========================================================================",
        f"  {worker_name}:",
        "    Type: AWS::Serverless::Function",
        "    Properties:",
        f"      FunctionName: {worker_name}",
        f"      CodeUri: {code_uri}",
        f"      Handler: {worker_handler}",
        f"      Description: {worker_desc}",
        f"      Timeout: {worker_timeout}",
        f"      MemorySize: {worker_memory}",
        "      # No Events - invoked async by API Lambda, not by HTTP",
        "      Policies:",
        "        - SQSSendMessagePolicy:",
        "            QueueName: !GetAtt CrawlerQueue.QueueName",
        "      Environment:",
        "        Variables:",
        "          CRAWLER_QUEUE_URL: !Ref CrawlerQueue",
        "",
        "  # ==========================================================================",
        "  # SQS FIFO Queue - Per-company rate limiting via MessageGroupId",
        "  # ==========================================================================",
        "  CrawlerQueue:",
        "    Type: AWS::SQS::Queue",
        "    Properties:",
        "      QueueName: CrawlerQueue.fifo",
        "      FifoQueue: true",
        "      ContentBasedDeduplication: true",
        "      VisibilityTimeout: 120",
        "      MessageRetentionPeriod: 86400",
        "",
        "  # ==========================================================================",
        "  # Crawler Worker Lambda - SQS-triggered, processes one message at a time",
        "  # ==========================================================================",
        f"  {crawler_name}:",
        "    Type: AWS::Serverless::Function",
        "    Properties:",
        f"      FunctionName: {crawler_name}",
        f"      CodeUri: {code_uri}",
        f"      Handler: {crawler_handler}",
        f"      Description: {crawler_desc}",
        f"      Timeout: {crawler_timeout}",
        f"      MemorySize: {crawler_memory}",
        "      Policies:",
        "        - S3CrudPolicy:",
        "            BucketName: !Ref RawContentBucket",
        "        - SQSSendMessagePolicy:",
        "            QueueName: !GetAtt ExtractorQueue.QueueName",
        "      Environment:",
        "        Variables:",
        "          RAW_CONTENT_BUCKET: !Ref RawContentBucket",
        "          EXTRACTOR_QUEUE_URL: !Ref ExtractorQueue",
        "      Events:",
        "        SQSEvent:",
        "          Type: SQS",
        "          Properties:",
        "            Queue: !GetAtt CrawlerQueue.Arn",
        "            BatchSize: 1",
        "",
        "  # ==========================================================================",
        "  # Extractor Queue - Standard SQS (not FIFO, no rate limiting needed)",
        "  # Phase 2K: Receives messages from CrawlerWorker after S3 save",
        "  # ==========================================================================",
        "  ExtractorQueue:",
        "    Type: AWS::SQS::Queue",
        "    Properties:",
        "      QueueName: ExtractorQueue",
        "      VisibilityTimeout: 60",
        "      MessageRetentionPeriod: 86400",
        "",
        "  # ==========================================================================",
        "  # Extractor Worker Lambda - SQS-triggered, extracts description/requirements",
        "  # Phase 2K: ReservedConcurrentExecutions=5 to limit DB connections",
        "  # ==========================================================================",
        f"  {extractor_name}:",
        "    Type: AWS::Serverless::Function",
        "    Properties:",
        f"      FunctionName: {extractor_name}",
        f"      CodeUri: {code_uri}",
        f"      Handler: {extractor_handler}",
        f"      Description: {extractor_desc}",
        f"      Timeout: {extractor_timeout}",
        f"      MemorySize: {extractor_memory}",
        f"      ReservedConcurrentExecutions: {extractor_reserved_concurrency}",
        "      Policies:",
        "        - S3ReadPolicy:",
        "            BucketName: !Ref RawContentBucket",
        "      Environment:",
        "        Variables:",
        "          RAW_CONTENT_BUCKET: !Ref RawContentBucket",
        "      Events:",
        "        SQSEvent:",
        "          Type: SQS",
        "          Properties:",
        "            Queue: !GetAtt ExtractorQueue.Arn",
        "            BatchSize: 1",
        "",
        "  # ==========================================================================",
        "  # S3 Bucket - Raw HTML storage with 30-day lifecycle",
        "  # ==========================================================================",
        "  RawContentBucket:",
        "    Type: AWS::S3::Bucket",
        "    Properties:",
        '      BucketName: !Sub "jobhunt-raw-content-${AWS::AccountId}"',
        "      LifecycleConfiguration:",
        "        Rules:",
        "          - Id: DeleteAfter30Days",
        "            Status: Enabled",
        "            ExpirationInDays: 30",
        "",
        "  # ==========================================================================",
        "  # API Gateway",
        "  # ==========================================================================",
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
        "    Description: API Lambda function name",
        f"    Value: !Ref {function_name}",
        "",
        "  FunctionArn:",
        "    Description: API Lambda function ARN",
        f"    Value: !GetAtt {function_name}.Arn",
        "",
        "  WorkerFunctionName:",
        "    Description: Worker Lambda function name",
        f"    Value: !Ref {worker_name}",
        "",
        "  WorkerFunctionArn:",
        "    Description: Worker Lambda function ARN",
        f"    Value: !GetAtt {worker_name}.Arn",
        "",
        "  CrawlerQueueUrl:",
        "    Description: Crawler SQS FIFO queue URL",
        "    Value: !Ref CrawlerQueue",
        "",
        "  CrawlerQueueArn:",
        "    Description: Crawler SQS FIFO queue ARN",
        "    Value: !GetAtt CrawlerQueue.Arn",
        "",
        "  CrawlerWorkerName:",
        "    Description: Crawler Lambda function name",
        f"    Value: !Ref {crawler_name}",
        "",
        "  RawContentBucketName:",
        "    Description: S3 bucket for raw HTML content",
        "    Value: !Ref RawContentBucket",
        "",
        "  ExtractorQueueUrl:",
        "    Description: Extractor SQS queue URL",
        "    Value: !Ref ExtractorQueue",
        "",
        "  ExtractorQueueArn:",
        "    Description: Extractor SQS queue ARN",
        "    Value: !GetAtt ExtractorQueue.Arn",
        "",
        "  ExtractorWorkerName:",
        "    Description: Extractor Lambda function name",
        f"    Value: !Ref {extractor_name}",
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

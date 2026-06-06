#!/usr/bin/env python3
"""
Generate chat/samconfig.toml from chat/.sam-config (and chat/.env.local secrets).

Mirrors backend/scripts/generate_samconfig.py, scoped to the chat service.
- .sam-config: stack name, region, capabilities, non-secret params (CORS origins)
- .env.local:  secret param values via _PARAM_NAME / _PROD_VALUE comments
               (Phase 6B Redis URL, Phase 7 API key — none in 6A)

Output:
- chat/samconfig.toml: SAM CLI deploy config for jh-chat-stack (gitignored — may
  contain secrets in later phases).

Exit codes (consumed by jpushchat): 0 = no change, 1 = modified, 2 = created.

DO NOT hand-edit chat/samconfig.toml — edit chat/.sam-config / chat/.env.local
and regenerate.
"""

import os
import re
import sys
from pathlib import Path


def parse_env_file(filepath):
    config = {}
    if not os.path.exists(filepath):
        return config
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def parse_env_local_prod_values(filepath):
    """Map CloudFormation param name -> PROD_VALUE, from .env.local comments."""
    if not os.path.exists(filepath):
        return {}
    meta = {}
    current = None
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                name = line.split("=", 1)[0].strip()
                if name.isupper():
                    current = name
                    meta.setdefault(current, {})
            if line.startswith("#") and current:
                m = re.match(r"#\s*([A-Z_]+)_PROD_VALUE\s*=\s*(.+)", line)
                if m and m.group(1) == current:
                    meta[current]["PROD_VALUE"] = m.group(2).strip()
                m = re.match(r"#\s*([A-Z_]+)_PARAM_NAME\s*=\s*(.+)", line)
                if m and m.group(1) == current:
                    meta[current]["PARAM_NAME"] = m.group(2).strip()
    out = {}
    for _var, md in meta.items():
        if "PARAM_NAME" in md and "PROD_VALUE" in md:
            out[md["PARAM_NAME"]] = md["PROD_VALUE"]
    return out


def escape_toml_value(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def generate_samconfig_toml(cfg, prod_values):
    stack_name = cfg.get("CFN_STACK_NAME", "jh-chat-stack")
    region = cfg.get("CFN_REGION", "us-east-1")
    capabilities = cfg.get("CFN_CAPABILITIES", "CAPABILITY_IAM")

    # Non-secret param from .sam-config: CORS origins (matches template Parameter).
    params = {}
    cors = cfg.get("CHAT_CORS_ALLOW_ORIGINS")
    if cors:
        params["AllowedOrigins"] = cors
    # Secret params from .env.local (later phases).
    params.update(prod_values)

    param_parts = []
    for name in sorted(params.keys()):
        value = escape_toml_value(params[name])
        param_parts.append(f'{name}=\\"{value}\\"')
    parameter_overrides = " ".join(param_parts)

    lines = [
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
        "",
    ]
    return "\n".join(lines)


def main():
    chat_dir = Path(__file__).parent.parent
    cfg = parse_env_file(chat_dir / ".sam-config")
    prod_values = parse_env_local_prod_values(chat_dir / ".env.local")
    new_content = generate_samconfig_toml(cfg, prod_values)

    samconfig_path = chat_dir / "samconfig.toml"
    if samconfig_path.exists():
        if samconfig_path.read_text() == new_content:
            print("✓ chat/samconfig.toml (no changes)")
            sys.exit(0)
        samconfig_path.write_text(new_content)
        print("⚠ chat/samconfig.toml modified")
        sys.exit(1)
    samconfig_path.write_text(new_content)
    print("⚠ chat/samconfig.toml created (new file)")
    sys.exit(2)


if __name__ == "__main__":
    main()

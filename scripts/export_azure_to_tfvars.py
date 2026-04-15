#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required. Install with `pip install PyYAML`.") from exc


def _to_hcl_literal(value, indent: int = 0) -> str:
    space = " " * indent
    if isinstance(value, dict):
        parts = ["{"]
        for key, item in value.items():
            parts.append(f"{space}  {key} = {_to_hcl_literal(item, indent + 2)}")
        parts.append(f"{space}}}")
        return "\n".join(parts)
    if isinstance(value, list):
        if not value:
            return "[]"
        parts = ["["]
        for item in value:
            parts.append(f"{space}  {_to_hcl_literal(item, indent + 2)},")
        parts.append(f"{space}]")
        return "\n".join(parts)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Export configs/azure_cluster.yaml into terraform tfvars format.")
    parser.add_argument("--input", default="configs/azure_cluster.yaml")
    parser.add_argument("--output", default="terraform/terraform.tfvars")
    args = parser.parse_args()

    payload = yaml.safe_load(Path(args.input).read_text())
    resource_groups = payload.get("resource_groups", [])
    hcl = f"resource_groups = {_to_hcl_literal(resource_groups)}\n"
    Path(args.output).write_text(hcl)
    print(json.dumps({"output": args.output, "resource_groups": len(resource_groups)}, indent=2))


if __name__ == "__main__":
    main()


from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lee.cli.commands.workflow_registry import evaluate_layer_health, load_workflow_registry


def main() -> int:
    parser = argparse.ArgumentParser(description="Check workflow layer readiness.")
    parser.add_argument("--layer", required=True, help="workflow layer name")
    parser.add_argument("--project-dir", default=".", help="project root")
    parser.add_argument("--input-path", default=None, help="optional input object path")
    parser.add_argument("--format", choices=["json", "table"], default="json")
    args = parser.parse_args()

    report = evaluate_layer_health(
        load_workflow_registry(),
        layer=args.layer,
        project_root=Path(args.project_dir),
        input_path=args.input_path,
    )
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{report['layer']}: {report['status']}")
        for item in report["summary"]:
            print(f"- {item}")
    return 0 if report["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())

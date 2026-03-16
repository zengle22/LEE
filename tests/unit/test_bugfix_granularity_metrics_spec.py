from pathlib import Path

import yaml


def test_bugfix_granularity_metrics_spec_defines_formula_and_reporting_window():
    spec_path = Path("spec-global/departments/dev/governance/bugfix-granularity-metrics-spec.yaml")
    assert spec_path.exists(), "Bugfix granularity metrics spec not found"

    with open(spec_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["status"] == "frozen"
    assert data["formula"]["metric_id"] == "bugfix_granularity_compliance_rate"
    assert data["formula"]["target"] == ">= 0.95"
    assert data["cadence"]["aggregation_window"] == "weekly"
    assert "top_failure_reasons" in data["report_format"]["required_fields"]

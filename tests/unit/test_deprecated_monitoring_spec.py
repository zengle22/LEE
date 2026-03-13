from pathlib import Path

import yaml


def test_deprecated_monitoring_spec_declares_metrics_and_alerts():
    spec_path = Path("spec-global/departments/dev/governance/deprecated-monitoring-spec.yaml")
    assert spec_path.exists(), "Deprecated monitoring spec not found"

    with open(spec_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    metric_ids = [item["id"] for item in data["metrics"]]
    assert metric_ids == ["reference_count", "workflow_instance_count", "last_seen_at"]
    assert data["alerts"]["workflow_instance_threshold"] == 0
    assert data["alerts"]["report_frequency"] == "weekly"

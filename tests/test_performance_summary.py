import json

from robo_automation.performance import PytestPerformanceMonitor


def test_merge_worker_summaries_uses_configured_summary_limit(tmp_path):
    worker_summary = {
        "worker": "gw0",
        "timing_count": 2,
        "slow_count": 2,
        "threshold_ms": 100,
        "slow_threshold_ms": 500,
        "summary_limit": 2,
        "by_operation": [],
        "slowest_operations": [
            {"action": "first", "duration_ms": 900},
            {"action": "second", "duration_ms": 800},
            {"action": "third", "duration_ms": 700},
        ],
    }
    (tmp_path / "gw0-summary.json").write_text(
        json.dumps(worker_summary), encoding="utf-8"
    )

    output = PytestPerformanceMonitor.merge_worker_summaries(tmp_path, summary_limit=1)

    assert output == tmp_path / "performance-summary.json"
    merged = json.loads(output.read_text(encoding="utf-8"))
    # Worker summaries may request a larger retained set than the controller default.
    assert len(merged["slowest_operations"]) == 2
    assert [item["action"] for item in merged["slowest_operations"]] == [
        "first",
        "second",
    ]

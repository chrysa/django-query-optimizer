"""Tests for SARIFReporter."""

from __future__ import annotations

import json

from django_query_optimizer.recommendations.base import ORMRecommendation, Severity
from django_query_optimizer.reporting.sarif import (
    SARIF_SCHEMA,
    SARIF_VERSION,
    TOOL_NAME,
    SARIFReporter,
    _rule_description,
    _rule_name,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────


def _rec(
    issue_type: str = "slow_query",
    severity: Severity = Severity.HIGH,
    message: str = "took 200 ms",
    suggestion: str = "add index",
    python_file: str = "",
    python_line: int = 0,
) -> ORMRecommendation:
    return ORMRecommendation(
        issue_type=issue_type,
        severity=severity,
        message=message,
        suggestion=suggestion,
        python_file=python_file,
        python_line=python_line,
    )


# ── _rule_name ────────────────────────────────────────────────────────────────


class TestRuleName:
    def test_single_word(self) -> None:
        assert _rule_name("query") == "Query"

    def test_two_words(self) -> None:
        assert _rule_name("slow_query") == "SlowQuery"

    def test_three_words(self) -> None:
        assert _rule_name("n_plus_1") == "NPlus1"

    def test_missing_select_related(self) -> None:
        assert _rule_name("missing_select_related") == "MissingSelectRelated"


# ── _rule_description ─────────────────────────────────────────────────────────


class TestRuleDescription:
    def test_known_slow_query(self) -> None:
        desc = _rule_description("slow_query")
        assert "threshold" in desc.lower()

    def test_known_n_plus_1(self) -> None:
        desc = _rule_description("n_plus_1")
        assert "n+1" in desc.lower() or "n plus" in desc.lower() or "N+1" in desc

    def test_unknown_rule_contains_id(self) -> None:
        desc = _rule_description("custom_rule_xyz")
        assert "custom_rule_xyz" in desc


# ── SARIFReporter.as_dict ─────────────────────────────────────────────────────


class TestSARIFReporterStructure:
    def test_schema_field(self) -> None:
        report = SARIFReporter([]).as_dict()
        assert report["$schema"] == SARIF_SCHEMA

    def test_version_field(self) -> None:
        report = SARIFReporter([]).as_dict()
        assert report["version"] == SARIF_VERSION

    def test_runs_is_list_with_one_entry(self) -> None:
        report = SARIFReporter([]).as_dict()
        assert isinstance(report["runs"], list)
        assert len(report["runs"]) == 1

    def test_tool_name(self) -> None:
        run = SARIFReporter([]).as_dict()["runs"][0]
        assert run["tool"]["driver"]["name"] == TOOL_NAME

    def test_tool_version_set(self) -> None:
        run = SARIFReporter([]).as_dict()["runs"][0]
        assert run["tool"]["driver"]["version"]

    def test_empty_recommendations_no_results(self) -> None:
        report = SARIFReporter([]).as_dict()
        assert report["runs"][0]["results"] == []

    def test_empty_recommendations_no_rules(self) -> None:
        report = SARIFReporter([]).as_dict()
        assert report["runs"][0]["tool"]["driver"]["rules"] == []


class TestSARIFReporterRules:
    def test_one_rule_per_unique_issue_type(self) -> None:
        recs = [_rec("slow_query"), _rec("slow_query"), _rec("n_plus_1")]
        rules = SARIFReporter(recs).as_dict()["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = {r["id"] for r in rules}
        assert rule_ids == {"slow_query", "n_plus_1"}

    def test_rules_sorted_alphabetically(self) -> None:
        recs = [_rec("slow_query"), _rec("n_plus_1")]
        rules = SARIFReporter(recs).as_dict()["runs"][0]["tool"]["driver"]["rules"]
        ids = [r["id"] for r in rules]
        assert ids == sorted(ids)

    def test_rule_has_id_name_description(self) -> None:
        recs = [_rec("slow_query")]
        rule = SARIFReporter(recs).as_dict()["runs"][0]["tool"]["driver"]["rules"][0]
        assert "id" in rule
        assert "name" in rule
        assert "shortDescription" in rule
        assert "text" in rule["shortDescription"]


class TestSARIFReporterResults:
    def test_one_result_per_recommendation(self) -> None:
        recs = [_rec(), _rec("n_plus_1", Severity.CRITICAL)]
        results = SARIFReporter(recs).as_dict()["runs"][0]["results"]
        assert len(results) == 2

    def test_result_rule_id(self) -> None:
        recs = [_rec("duplicate_query")]
        result = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]
        assert result["ruleId"] == "duplicate_query"

    def test_critical_maps_to_error(self) -> None:
        recs = [_rec(severity=Severity.CRITICAL)]
        result = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]
        assert result["level"] == "error"

    def test_high_maps_to_error(self) -> None:
        recs = [_rec(severity=Severity.HIGH)]
        result = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]
        assert result["level"] == "error"

    def test_medium_maps_to_warning(self) -> None:
        recs = [_rec(severity=Severity.MEDIUM)]
        result = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]
        assert result["level"] == "warning"

    def test_low_maps_to_note(self) -> None:
        recs = [_rec(severity=Severity.LOW)]
        result = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]
        assert result["level"] == "note"

    def test_info_maps_to_note(self) -> None:
        recs = [_rec(severity=Severity.INFO)]
        result = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]
        assert result["level"] == "note"

    def test_message_contains_message_and_suggestion(self) -> None:
        recs = [_rec(message="took 200 ms", suggestion="add index")]
        result = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]
        text = result["message"]["text"]
        assert "took 200 ms" in text
        assert "add index" in text

    def test_no_location_when_no_python_file(self) -> None:
        recs = [_rec(python_file="")]
        result = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]
        assert "locations" not in result

    def test_location_present_when_python_file_set(self) -> None:
        recs = [_rec(python_file="views/orders.py")]
        result = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]
        assert "locations" in result

    def test_location_uri(self) -> None:
        recs = [_rec(python_file="views/orders.py")]
        loc = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]["locations"][0]
        assert loc["physicalLocation"]["artifactLocation"]["uri"] == "views/orders.py"

    def test_location_uri_base_id(self) -> None:
        recs = [_rec(python_file="views.py")]
        loc = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]["locations"][0]
        assert loc["physicalLocation"]["artifactLocation"]["uriBaseId"] == "%SRCROOT%"

    def test_no_region_when_line_is_zero(self) -> None:
        recs = [_rec(python_file="views.py", python_line=0)]
        loc = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]["locations"][0]
        assert "region" not in loc["physicalLocation"]

    def test_region_start_line_set(self) -> None:
        recs = [_rec(python_file="views.py", python_line=42)]
        loc = SARIFReporter(recs).as_dict()["runs"][0]["results"][0]["locations"][0]
        assert loc["physicalLocation"]["region"]["startLine"] == 42


# ── SARIFReporter.as_json ──────────────────────────────────────────────────────


class TestSARIFReporterJSON:
    def test_as_json_is_valid_json(self) -> None:
        recs = [_rec()]
        output = SARIFReporter(recs).as_json()
        parsed = json.loads(output)
        assert parsed["version"] == SARIF_VERSION

    def test_as_json_default_indent_2(self) -> None:
        recs = [_rec()]
        output = SARIFReporter(recs).as_json()
        # Indented JSON has newlines
        assert "\n" in output

    def test_as_json_custom_indent(self) -> None:
        recs = [_rec()]
        output_4 = SARIFReporter(recs).as_json(indent=4)
        output_2 = SARIFReporter(recs).as_json(indent=2)
        assert len(output_4) > len(output_2)

    def test_as_json_empty_produces_valid_sarif(self) -> None:
        output = SARIFReporter([]).as_json()
        parsed = json.loads(output)
        assert parsed["runs"][0]["results"] == []

"""SARIF 2.1.0 report generator.

Converts a list of :class:`~django_query_optimizer.recommendations.ORMRecommendation`
objects into a SARIF 2.1.0 JSON document that can be uploaded to GitHub Code
Scanning via the ``github/codeql-action/upload-sarif`` action.

Example::

    from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer
    from django_query_optimizer.reporting.sarif import SARIFReporter

    analyzer = QueryAnalyzer(collector.queries)
    reporter = SARIFReporter(analyzer.analyze())

    with open("query-results.sarif", "w") as fh:
        fh.write(reporter.as_json())

Constants
---------
``SARIF_SCHEMA``
    URL of the SARIF 2.1.0 JSON schema.
``TOOL_NAME``
    Identifier written to the ``tool.driver.name`` field.
``SARIF_VERSION``
    SARIF specification version — always ``"2.1.0"``.
"""

from __future__ import annotations

import json
from typing import Any, Final

from django_query_optimizer._internal.version import __version__
from django_query_optimizer.recommendations.base import ORMRecommendation, Severity

SARIF_SCHEMA: Final[str] = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
)
SARIF_VERSION: Final[str] = "2.1.0"
TOOL_NAME: Final[str] = "django-query-optimizer"

_SEVERITY_TO_LEVEL: Final[dict[Severity, str]] = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}

_RULE_DESCRIPTIONS: Final[dict[str, str]] = {
    "slow_query": "Query execution time exceeds the configured threshold.",
    "duplicate_query": "Identical SQL is executed multiple times.",
    "n_plus_1": "A query pattern causes N+1 database round-trips.",
    "missing_select_related": "Foreign-key traversal should use select_related().",
}


def _rule_name(rule_id: str) -> str:
    """Convert a snake_case rule id to PascalCase for the SARIF rule name."""
    return "".join(part.capitalize() for part in rule_id.split("_"))


def _rule_description(rule_id: str) -> str:
    return _RULE_DESCRIPTIONS.get(rule_id, f"ORM issue detected: {rule_id}.")


class SARIFReporter:
    """Generate a SARIF 2.1.0 report from a list of ORM recommendations.

    Parameters
    ----------
    recommendations:
        The list returned by
        :meth:`~django_query_optimizer.analyzers.QueryAnalyzer.analyze`.

    Example::

        reporter = SARIFReporter(analyzer.analyze())
        with open("results.sarif", "w") as fh:
            fh.write(reporter.as_json())
    """

    def __init__(self, recommendations: list[ORMRecommendation]) -> None:
        self._recs = recommendations

    def as_dict(self) -> dict[str, Any]:
        """Return the SARIF report as a Python dict."""
        rule_ids = sorted({r.issue_type for r in self._recs})
        return {
            "$schema": SARIF_SCHEMA,
            "version": SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": TOOL_NAME,
                            "version": __version__,
                            "rules": [self._make_rule(rid) for rid in rule_ids],
                        }
                    },
                    "results": [self._make_result(rec) for rec in self._recs],
                }
            ],
        }

    def as_json(self, indent: int = 2) -> str:
        """Return the SARIF report as a formatted JSON string."""
        return json.dumps(self.as_dict(), indent=indent)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _make_rule(self, rule_id: str) -> dict[str, Any]:
        return {
            "id": rule_id,
            "name": _rule_name(rule_id),
            "shortDescription": {"text": _rule_description(rule_id)},
        }

    def _make_result(self, rec: ORMRecommendation) -> dict[str, Any]:
        result: dict[str, Any] = {
            "ruleId": rec.issue_type,
            "level": _SEVERITY_TO_LEVEL[rec.severity],
            "message": {"text": f"{rec.message} — {rec.suggestion}"},
        }
        if rec.python_file:
            physical: dict[str, Any] = {
                "artifactLocation": {
                    "uri": rec.python_file,
                    "uriBaseId": "%SRCROOT%",
                },
            }
            if rec.python_line:
                physical["region"] = {"startLine": rec.python_line}
            result["locations"] = [{"physicalLocation": physical}]
        return result

from __future__ import annotations

from typing import Dict, Iterable, List


class CoverageAuditor:
    """Audit acceptance coverage against provided evidence refs."""

    @staticmethod
    def build_trace_matrix(
        acceptance_ids: Iterable[str],
        evidence_map: Dict[str, List[str]],
    ) -> List[Dict[str, object]]:
        matrix: List[Dict[str, object]] = []
        for acceptance_id in acceptance_ids:
            refs = evidence_map.get(acceptance_id, [])
            matrix.append(
                {
                    "acceptance_id": acceptance_id,
                    "covered": bool(refs),
                    "evidence_refs": refs,
                }
            )
        return matrix

    @staticmethod
    def find_gaps(trace_matrix: Iterable[Dict[str, object]]) -> List[str]:
        return [
            str(entry["acceptance_id"])
            for entry in trace_matrix
            if not entry.get("covered")
        ]

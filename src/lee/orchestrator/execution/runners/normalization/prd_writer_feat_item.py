from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .prd_writer_feat_common import (
    build_acceptance_checks,
    clean_text,
    normalize_acceptance_criteria,
    normalize_dependency_ids,
    normalize_input_contract,
    normalize_input_entries,
    normalize_lifecycle_status,
    normalize_priority,
    normalize_string_list,
    normalize_user_story_item,
)


def normalize_feat_item(
    *,
    feat_item: Any,
    actual_epic_ref: Optional[str],
) -> Any:
    if not isinstance(feat_item, dict):
        return feat_item

    normalized_feat = dict(feat_item)
    ssot = normalized_feat.get("ssot")
    normalized_ssot = dict(ssot) if isinstance(ssot, dict) else {}

    feat_id = clean_text(normalized_feat.get("feat_id") or normalized_feat.get("id"))
    if not feat_id:
        seed_text = (
            clean_text(normalized_feat.get("title"))
            or clean_text(normalized_feat.get("goal"))
            or clean_text(normalized_feat.get("name"))
        )
        seed_slug = re.sub(r"[^A-Za-z0-9]+", "-", seed_text).strip("-").lower()
        feat_id = f"feat-{seed_slug}" if seed_slug else (f"{actual_epic_ref}-feat" if actual_epic_ref else "FEAT-AUTO")
    if feat_id:
        normalized_feat["feat_id"] = feat_id

    title = clean_text(normalized_feat.get("title")) or feat_id or "Untitled FEAT"
    goal = clean_text(normalized_feat.get("goal") or normalized_feat.get("description")) or title
    normalized_feat["title"] = title
    normalized_feat["goal"] = goal
    normalized_feat["user_value"] = (
        clean_text(normalized_feat.get("user_value"))
        or clean_text(
            normalized_feat.get("business_context", {}).get("problem")
            if isinstance(normalized_feat.get("business_context"), dict)
            else ""
        )
        or clean_text(normalized_feat.get("description"))
        or title
    )
    scope_boundary = normalized_feat.get("scope_boundary")
    if not isinstance(scope_boundary, dict):
        scope_boundary = {}

    normalized_feat["inputs"] = (
        normalize_input_entries(
            normalized_feat.get("inputs") or normalized_feat.get("input") or scope_boundary.get("in_scope"),
            fallback=[
                normalized_feat.get("source_refs", [f"{actual_epic_ref}#scope"])[0]
                if isinstance(normalized_feat.get("source_refs"), list) and normalized_feat.get("source_refs")
                else (f"{actual_epic_ref}#scope" if actual_epic_ref else title)
            ],
        )[:5]
    )
    normalized_feat["input_contract"] = normalize_input_contract(
        normalized_feat.get("input_contract"),
        inputs=normalized_feat.get("inputs") or [],
        source_refs=normalized_feat.get("source_refs") if isinstance(normalized_feat.get("source_refs"), list) else [],
        epic_ref=actual_epic_ref
        or clean_text(normalized_feat.get("epic_ref"))
        or clean_text(normalized_ssot.get("parent")),
    )
    normalized_feat["processing"] = normalize_string_list(
        normalized_feat.get("processing"),
        fallback=[clean_text(normalized_feat.get("description")) or f"Deliver {title} capability"],
    )[:5]
    normalized_feat["outputs"] = normalize_string_list(
        normalized_feat.get("outputs")
        or normalized_feat.get("output")
        or normalized_feat.get("acceptance_boundary"),
        fallback=[f"{title} FEAT specification"],
    )[:5]
    normalized_feat["acceptance_criteria"] = normalize_acceptance_criteria(
        normalized_feat.get("acceptance_criteria") or normalized_feat.get("acceptance_boundaries"),
        title=title,
        goal=goal,
    )[:5]
    normalized_feat["dependencies"] = normalize_dependency_ids(normalized_feat.get("dependencies"))[:10]
    normalized_feat["non_goals"] = normalize_string_list(
        normalized_feat.get("non_goals") or scope_boundary.get("out_of_scope"),
    )[:10]
    normalized_feat["priority"] = normalize_priority(normalized_feat.get("priority"))
    normalized_feat["delivery_slice"] = (
        clean_text(normalized_feat.get("delivery_slice"))
        or clean_text(normalized_feat.get("parent_workflow"))
        or clean_text(normalized_feat.get("category"))
        or "core"
    )
    normalized_feat["lifecycle_status"] = normalize_lifecycle_status(
        normalized_feat.get("lifecycle_status") or normalized_feat.get("status")
    )
    source_refs = normalized_feat.get("source_refs")
    if isinstance(source_refs, list):
        normalized_feat["source_refs"] = normalize_string_list(source_refs)[:5]

    if normalized_feat.get("feat_id"):
        normalized_ssot.setdefault("identity_kind", "ssot")
        normalized_ssot.setdefault("ssot_type", "FEAT")
        normalized_ssot.setdefault(
            "parent",
            actual_epic_ref
            or clean_text(normalized_feat.get("epic_ref"))
            or clean_text(normalized_ssot.get("parent")),
        )
        normalized_ssot.setdefault(
            "derived_from",
            actual_epic_ref
            or clean_text(normalized_feat.get("epic_ref"))
            or clean_text(normalized_ssot.get("derived_from"))
            or clean_text(normalized_ssot.get("parent")),
        )
    if normalized_ssot:
        normalized_feat["ssot"] = normalized_ssot

    derived = normalized_feat.get("derived_object_expectations")
    normalized_derived = dict(derived) if isinstance(derived, dict) else {}
    normalized_derived.setdefault("task_required", True)
    normalized_derived.setdefault("testset_required", True)
    normalized_derived.setdefault("testset_owner", "qa")
    normalized_derived.setdefault("qa_seed_required", True)
    normalized_feat["derived_object_expectations"] = normalized_derived

    testability_seed = normalized_feat.get("testability_seed")
    normalized_testability = dict(testability_seed) if isinstance(testability_seed, dict) else {}
    normalized_testability.setdefault("risk_notes", normalized_feat.get("non_goals") or [])
    normalized_testability.setdefault("integration_points", normalized_feat.get("dependencies") or [])
    normalized_testability.setdefault("priority_hint", normalized_feat.get("priority"))
    normalized_feat["testability_seed"] = normalized_testability

    raw_user_stories = normalized_feat.get("user_stories")
    normalized_user_stories: List[Dict[str, str]] = []
    if isinstance(raw_user_stories, list):
        for story in raw_user_stories:
            normalized_story = normalize_user_story_item(story)
            if normalized_story:
                normalized_user_stories.append(normalized_story)
    normalized_feat["user_stories"] = normalized_user_stories[:3]
    normalized_feat["acceptance_checks"] = build_acceptance_checks(
        normalized_feat,
        normalized_feat.get("acceptance_criteria") or [],
    )
    return normalized_feat

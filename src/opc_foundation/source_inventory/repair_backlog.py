"""Repair backlog models and utilities for foundation source inventory.

Worktree: feature/m3c-5b0-source-repair-backlog
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass(frozen=True)
class RepairBacklogItem:
    """Single source entry in the repair backlog."""

    source_id: str
    category: str
    status: str
    scheduling_allowed: bool
    score: int | None = None
    primary_issue: str | None = None
    recommended_action: str | None = None
    priority: str | None = None
    next_stage: str | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepairBacklogItem:
        return cls(
            source_id=data["source_id"],
            category=data["category"],
            status=data["status"],
            scheduling_allowed=data["scheduling_allowed"],
            score=data.get("score"),
            primary_issue=data.get("primary_issue"),
            recommended_action=data.get("recommended_action"),
            priority=data.get("priority"),
            next_stage=data.get("next_stage"),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class RepairBacklog:
    """Complete repair backlog with metadata and items."""

    version: int
    scope: dict[str, Any]
    policy: dict[str, bool]
    categories: dict[str, dict[str, Any]]
    items: tuple[RepairBacklogItem, ...]

    def by_category(self, category: str) -> tuple[RepairBacklogItem, ...]:
        return tuple(item for item in self.items if item.category == category)

    def by_priority(self, priority: str) -> tuple[RepairBacklogItem, ...]:
        return tuple(item for item in self.items if item.priority == priority)

    def by_next_stage(self, stage: str) -> tuple[RepairBacklogItem, ...]:
        return tuple(item for item in self.items if item.next_stage == stage)


def load_repair_backlog_config(path: str | pathlib.Path) -> RepairBacklog:
    """Load a repair backlog YAML config into a RepairBacklog instance.

    Args:
        path: Filesystem path to the YAML config file.

    Returns:
        Parsed RepairBacklog.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the file is not valid YAML.
        KeyError: If required top-level keys are missing.
    """
    path = pathlib.Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    if raw is None:
        raise ValueError("YAML file is empty or invalid.")

    items = tuple(
        RepairBacklogItem.from_dict(entry) for entry in raw.get("sources", [])
    )

    return RepairBacklog(
        version=int(raw["version"]),
        scope=dict(raw.get("scope", {})),
        policy=dict(raw.get("policy", {})),
        categories=dict(raw.get("categories", {})),
        items=items,
    )


def validate_repair_backlog(backlog: RepairBacklog) -> list[str]:
    """Validate a RepairBacklog and return a list of error messages.

    Checks:
      - version must be 1
      - scope keys must be present
      - policy flags must be present and true
      - Every non-ready source must have scheduling_allowed=false
      - Every item must have a source_id, category, and status
      - scheduled_observation items must have scheduling_allowed=true
      - No proxy URLs, secrets, or local absolute paths in notes

    Args:
        backlog: The backlog to validate.

    Returns:
        List of human-readable validation error strings. Empty list if valid.
    """
    errors: list[str] = []

    if backlog.version != 1:
        errors.append(f"Expected version 1, got {backlog.version}")

    required_scope = {
        "source_inventory_count",
        "active_trial_v2_content_ready_count",
        "production_enabled",
        "affects_trial_v2_scheduling",
    }
    missing_scope = required_scope - set(backlog.scope.keys())
    if missing_scope:
        errors.append(f"Missing scope keys: {sorted(missing_scope)}")

    required_policy = {
        "do_not_modify_trial_v1",
        "do_not_modify_trial_v2_allowlist",
        "no_browser_runtime_in_this_stage",
        "no_source_repair_in_this_stage",
    }
    missing_policy = required_policy - set(backlog.policy.keys())
    if missing_policy:
        errors.append(f"Missing policy keys: {sorted(missing_policy)}")
    else:
        for key in required_policy:
            if backlog.policy.get(key) is not True:
                errors.append(f"Policy flag '{key}' must be true")

    known_categories = set(backlog.categories.keys())

    for item in backlog.items:
        if not item.source_id:
            errors.append("Found item with missing source_id")
        if not item.category:
            errors.append(f"Item {item.source_id}: missing category")
        if item.category not in known_categories:
            errors.append(
                f"Item {item.source_id}: unknown category '{item.category}'"
            )
        if not item.status:
            errors.append(f"Item {item.source_id}: missing status")

        if item.category == "scheduled_observation" and not item.scheduling_allowed:
            errors.append(
                f"Item {item.source_id}: scheduled_observation must allow scheduling"
            )

        if item.status == "non_ready" and item.scheduling_allowed:
            errors.append(
                f"Item {item.source_id}: non_ready source must NOT allow scheduling"
            )

        if item.status == "not_audited" and item.scheduling_allowed:
            errors.append(
                f"Item {item.source_id}: not_audited source must NOT allow scheduling"
            )

        notes = (item.notes or "").lower()
        if "http://" in notes or "https://" in notes:
            # Only flag if it looks like a proxy or internal URL
            if "proxy" in notes or "localhost" in notes or "127.0.0.1" in notes:
                errors.append(
                    f"Item {item.source_id}: notes contain suspicious URL"
                )
        if "/users/" in notes or "/home/" in notes:
            errors.append(
                f"Item {item.source_id}: notes contain local absolute path"
            )

    return errors


def summarize_repair_backlog(backlog: RepairBacklog) -> dict[str, Any]:
    """Summarize a RepairBacklog into counts by category, priority, and status.

    Args:
        backlog: The backlog to summarize.

    Returns:
        Nested dict with summary counts.
    """
    category_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    next_stage_counts: dict[str, int] = {}
    scheduling_blocked_count = 0
    scheduling_allowed_count = 0
    total_scored = 0
    total_score = 0

    for item in backlog.items:
        category_counts[item.category] = category_counts.get(item.category, 0) + 1

        if item.priority:
            priority_counts[item.priority] = priority_counts.get(item.priority, 0) + 1

        status_counts[item.status] = status_counts.get(item.status, 0) + 1

        if item.next_stage:
            next_stage_counts[item.next_stage] = (
                next_stage_counts.get(item.next_stage, 0) + 1
            )

        if item.scheduling_allowed:
            scheduling_allowed_count += 1
        else:
            scheduling_blocked_count += 1

        if item.score is not None:
            total_scored += 1
            total_score += item.score

    summary: dict[str, Any] = {
        "version": backlog.version,
        "total_items": len(backlog.items),
        "scope": backlog.scope,
        "by_category": category_counts,
        "by_priority": priority_counts,
        "by_status": status_counts,
        "by_next_stage": next_stage_counts,
        "scheduling": {
            "allowed": scheduling_allowed_count,
            "blocked": scheduling_blocked_count,
        },
    }

    if total_scored > 0:
        summary["average_score"] = round(total_score / total_scored, 2)
        summary["scored_items"] = total_scored

    return summary

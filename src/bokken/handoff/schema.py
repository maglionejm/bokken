"""Structured-output schema for handoff spec generation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScenarioDraft(BaseModel):
    name: str
    when: str
    then: str


class RequirementDraft(BaseModel):
    name: str
    statement: str
    scenarios: list[ScenarioDraft] = Field(default_factory=list)
    assumption_indexes: list[int] = Field(default_factory=list)


class CapabilityDraft(BaseModel):
    name: str
    purpose: str
    requirements: list[RequirementDraft] = Field(min_length=1)


class TaskGroupDraft(BaseModel):
    name: str
    tasks: list[str] = Field(min_length=1)


class SpecPackage(BaseModel):
    why: str
    what_changes: list[str] = Field(min_length=1)
    capabilities: list[CapabilityDraft] = Field(min_length=1)
    design_context: str = ""
    design_decisions: list[str] = Field(default_factory=list)
    task_groups: list[TaskGroupDraft] = Field(default_factory=list)

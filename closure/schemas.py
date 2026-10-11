"""Pydantic output contracts for each agent (what the frontend consumes)."""
from typing import Literal
from pydantic import BaseModel, Field

Posture = Literal["normal", "delayed_arrival", "early_dismissal", "telework", "closure"]


class RankedHazard(BaseModel):
    alert_id: str = Field(description="Exact alert id from get_active_alerts")
    event: str
    rank: int = Field(description="1 = most important to this facility")
    threat_level: Literal["life_safety_immediate", "significant", "minor", "informational"]
    time_horizon: Literal["active_now", "within_operating_window", "later", "not_relevant"]
    affects_facility: bool
    affects_commutes: bool
    verified_facts: list[str] = Field(description="Only facts stated in NWS fields (event, severity, urgency, certainty, times, area)")
    agent_interpretation: list[str] = Field(description="Your own inferences, clearly separate from verified facts")


class HazardAssessment(BaseModel):
    summary: str
    immediate_life_safety_threat: bool
    multiple_simultaneous_hazards: bool
    ranked_hazards: list[RankedHazard]
    deprioritized: list[str] = Field(description="Alerts judged minor, with the reason")
    data_gaps: list[str]


class ImpactGroup(BaseModel):
    group: str
    count: int
    implication: str


class EmployeeImpactAssessment(BaseModel):
    headline: str
    scenario_type: Literal["facility_and_commute_affected", "facility_ok_commute_blocked",
                           "facility_affected_commute_ok", "low_impact", "no_hazard"]
    workforce_total: int
    high_risk_count: int
    elevated_risk_count: int
    high_or_elevated_pct: float
    groups: list[ImpactGroup]
    most_exposed_communities: list[str]
    essential_coverage_concerns: list[str]
    accessibility_concerns: list[str]
    telework_assessment: str
    data_limitations: list[str]


class Tradeoff(BaseModel):
    option: Posture
    pros: list[str]
    cons: list[str]


class SecondOpinion(BaseModel):
    verdict: Literal["agree", "agree_with_caveats", "disagree"]
    deterministic_posture: Posture
    recommended_posture: Posture
    reasoning: str = Field(description="Concise paragraph a manager could repeat to explain the call")
    key_factors: list[str]
    overlooked_risks: list[str]
    conflicting_evidence: list[str]
    tradeoffs: list[Tradeoff]
    uncertainty: list[str]
    missing_data: list[str]
    what_would_change: list[str]


class GroupPlan(BaseModel):
    group_id: str = Field(description="Must be a group_id returned by get_recipient_groups")
    why_included: str
    instruction: str
    channels: list[str]


class ExcludedGroup(BaseModel):
    group_id: str
    why_excluded: str


class Email(BaseModel):
    subject: str
    body: str


class SpecificInstruction(BaseModel):
    applies_to: str
    instruction: str


class NotificationPlan(BaseModel):
    group_plans: list[GroupPlan]
    excluded: list[ExcludedGroup]
    email: Email
    employee_specific_instructions: list[SpecificInstruction]
    channel_recommendation: str
    audit_explanation: str = Field(description="Audit-ready explanation of the decision, its evidence and any override")
    follow_up_actions: list[str]

"""Built-in specialist templates for workspace sessions."""

from __future__ import annotations

from typing import Dict, List, Optional

DESIGN_STUDIO_DELIVERABLE_INSTRUCTION = (
    "Use sections titled Candidate Directions, Comparison, Recommended Direction, "
    "Selected Direction, Rationale, Component Map, Handoff Notes, State Notes, "
    "Platform Constraints, and Open Questions. "
    "Keep section headings exact so the app can render a structured design handoff."
)

SESSION_TEMPLATES: Dict[str, Dict[str, object]] = {
    "design_web_app_studio": {
        "id": "design_web_app_studio",
        "session_type": "design_studio",
        "label": "Web App Design Studio",
        "description": "Explores web product directions with strong IA, hierarchy, and implementation realism.",
        "default_framework": "standard",
        "council_lenses": ["Product designer", "UX strategist", "Frontend engineer", "Accessibility reviewer", "Product manager"],
        "evaluation_criteria": ["Task clarity", "Hierarchy", "Information architecture", "Platform fit", "Accessibility", "Implementation realism"],
        "synthesis_instruction": "Generate distinct web directions, compare them directly, then recommend one direction with concrete implementation notes.",
        "deliverable_format": "Design Studio handoff",
        "deliverable_instruction": DESIGN_STUDIO_DELIVERABLE_INSTRUCTION,
    },
    "design_ios_app_studio": {
        "id": "design_ios_app_studio",
        "session_type": "design_studio",
        "label": "iOS Design Studio",
        "description": "Explores native-feeling iOS directions with strong platform fit and touch ergonomics.",
        "default_framework": "standard",
        "council_lenses": ["iOS designer", "Interaction designer", "SwiftUI engineer", "Accessibility reviewer", "Product manager"],
        "evaluation_criteria": ["Task clarity", "Navigation", "Platform fit", "Touch ergonomics", "Accessibility", "Implementation realism"],
        "synthesis_instruction": "Generate distinct iOS directions, call out native platform tradeoffs, and recommend one direction with implementation-minded notes.",
        "deliverable_format": "Design Studio handoff",
        "deliverable_instruction": DESIGN_STUDIO_DELIVERABLE_INSTRUCTION,
    },
    "design_cross_platform_studio": {
        "id": "design_cross_platform_studio",
        "session_type": "design_studio",
        "label": "Cross-Platform Design Studio",
        "description": "Compares web and iOS directions while keeping shared product intent and platform-specific constraints explicit.",
        "default_framework": "heterogeneous",
        "council_lenses": ["Product designer", "iOS designer", "Frontend engineer", "Accessibility reviewer", "Product manager"],
        "evaluation_criteria": ["Task clarity", "Hierarchy", "Platform fit", "Cross-platform consistency", "Accessibility", "Implementation realism"],
        "synthesis_instruction": "Compare directions across platforms, keep real structural differences visible, and end with one recommended direction plus platform-specific handoff notes.",
        "deliverable_format": "Design Studio handoff",
        "deliverable_instruction": DESIGN_STUDIO_DELIVERABLE_INSTRUCTION,
    },
    "visual_ux_review": {
        "id": "visual_ux_review",
        "session_type": "visual_review",
        "label": "UX Review Council",
        "description": "Balances usability, clarity, product intent, and design execution.",
        "default_framework": "standard",
        "council_lenses": ["UX reviewer", "Visual designer", "Accessibility reviewer", "Product manager", "Brand reviewer"],
        "evaluation_criteria": ["Hierarchy", "Clarity", "Affordances", "Accessibility", "Consistency", "Task flow"],
        "synthesis_instruction": "Prioritize the most consequential issues, explain the user impact, and suggest practical design fixes.",
        "deliverable_format": "Design critique output",
        "deliverable_instruction": "Use sections titled Summary, What's Working, Issues by Priority, and Recommended Fixes.",
    },
    "visual_accessibility_review": {
        "id": "visual_accessibility_review",
        "session_type": "visual_review",
        "label": "Accessibility Review Council",
        "description": "Focuses the council on legibility, contrast, semantics, and interaction clarity.",
        "default_framework": "standard",
        "council_lenses": ["Accessibility reviewer", "UX reviewer", "QA reviewer", "Product manager"],
        "evaluation_criteria": ["Contrast", "Legibility", "Focus order", "Touch targets", "State visibility", "Error prevention"],
        "synthesis_instruction": "Call out accessibility defects first, note severity, and separate blockers from polish issues.",
        "deliverable_format": "UX fixes list",
        "deliverable_instruction": "Use sections titled Accessibility Risks, High-Priority Fixes, and Follow-up Improvements.",
    },
    "visual_pm_review": {
        "id": "visual_pm_review",
        "session_type": "visual_review",
        "label": "PM Readout Council",
        "description": "Evaluates whether the screen communicates product intent and user value clearly.",
        "default_framework": "ensemble",
        "council_lenses": ["Product manager", "UX reviewer", "Brand reviewer", "Growth reviewer"],
        "evaluation_criteria": ["Intent clarity", "Decision friction", "Value communication", "Trust", "CTA strength"],
        "synthesis_instruction": "Summarize the top product risks, expected user confusion, and the highest-leverage next design changes.",
        "deliverable_format": "UX fixes list",
        "deliverable_instruction": "Use sections titled Product Readout, Top UX Fixes, and Suggested Experiments.",
    },
    "code_senior_review": {
        "id": "code_senior_review",
        "session_type": "code_review",
        "label": "Senior Engineer Council",
        "description": "Default multi-perspective code review focused on correctness and maintainability.",
        "default_framework": "standard",
        "council_lenses": ["Senior engineer", "Maintainer", "QA reviewer", "Architect"],
        "evaluation_criteria": ["Correctness", "Regression risk", "Maintainability", "Tests", "Clarity"],
        "synthesis_instruction": "Return a findings-first review, ordered by severity, with clear file and line references when available.",
        "deliverable_format": "PR review summary",
        "deliverable_instruction": "Use sections titled Findings, Open Questions, and Recommended Next Steps. Put findings first.",
    },
    "code_security_review": {
        "id": "code_security_review",
        "session_type": "code_review",
        "label": "Security Review Council",
        "description": "Biases the council toward attack surface, trust boundaries, and unsafe defaults.",
        "default_framework": "standard",
        "council_lenses": ["Security reviewer", "Senior engineer", "Maintainer"],
        "evaluation_criteria": ["Input validation", "Auth and authz", "Secrets handling", "Trust boundaries", "Abuse cases"],
        "synthesis_instruction": "Highlight exploitable or trust-boundary issues first, then note lower-severity hardening gaps.",
        "deliverable_format": "Bug triage summary",
        "deliverable_instruction": "Use sections titled Security Findings, Severity Triage, and Remediation Notes.",
    },
    "code_performance_review": {
        "id": "code_performance_review",
        "session_type": "code_review",
        "label": "Performance Review Council",
        "description": "Looks for algorithmic inefficiency, query/path hot spots, and wasteful work.",
        "default_framework": "debate",
        "council_lenses": ["Performance reviewer", "Senior engineer", "Architect"],
        "evaluation_criteria": ["Time complexity", "I/O cost", "Memory pressure", "Latency risk", "Scalability"],
        "synthesis_instruction": "Prioritize issues by expected runtime impact and call out the concrete path or workload that triggers them.",
        "deliverable_format": "Patch plan or implementation handoff",
        "deliverable_instruction": "Use sections titled Performance Risks, Patch Plan, and Validation Steps.",
    },
    "code_architecture_review": {
        "id": "code_architecture_review",
        "session_type": "code_review",
        "label": "Architecture Review Council",
        "description": "Focuses on module boundaries, layering, and long-term structure.",
        "default_framework": "heterogeneous",
        "council_lenses": ["Architect", "Senior engineer", "DX reviewer", "Maintainer"],
        "evaluation_criteria": ["Separation of concerns", "Dependency direction", "Extensibility", "Cohesion", "Operational clarity"],
        "synthesis_instruction": "Separate immediate bugs from architectural debt and propose the smallest structural changes with high payoff.",
        "deliverable_format": "Refactor roadmap",
        "deliverable_instruction": "Use sections titled Immediate Risks, Structural Debt, and Refactor Roadmap.",
    },
}


def get_session_template(template_id: Optional[str], session_type: Optional[str] = None) -> Optional[Dict[str, object]]:
    if not isinstance(template_id, str) or not template_id.strip():
        return None
    template = SESSION_TEMPLATES.get(template_id.strip())
    if template is None:
        return None
    if session_type and template.get("session_type") != session_type:
        return None
    return template


def normalize_session_template_id(template_id: Optional[str], session_type: Optional[str] = None) -> Optional[str]:
    template = get_session_template(template_id, session_type=session_type)
    return template.get("id") if template else None


def get_template_label(template_id: Optional[str], session_type: Optional[str] = None) -> Optional[str]:
    template = get_session_template(template_id, session_type=session_type)
    if template is None:
        return None
    label = template.get("label")
    return str(label) if isinstance(label, str) else None


def list_session_templates(session_type: Optional[str] = None) -> List[Dict[str, object]]:
    templates = list(SESSION_TEMPLATES.values())
    if session_type:
        templates = [template for template in templates if template.get("session_type") == session_type]
    return templates


DEFAULT_DELIVERABLES: Dict[str, Dict[str, str]] = {
    "design_studio": {
        "label": "Design Studio handoff",
        "instruction": DESIGN_STUDIO_DELIVERABLE_INSTRUCTION,
    },
    "visual_review": {
        "label": "Design critique output",
        "instruction": "Use sections titled Summary, What's Working, Issues by Priority, and Recommended Fixes.",
    },
    "code_review": {
        "label": "PR review summary",
        "instruction": "Use sections titled Findings, Open Questions, and Recommended Next Steps. Put findings first.",
    },
    "build_spec": {
        "label": "Patch plan or implementation handoff",
        "instruction": "Use sections titled Scope, Proposed Approach, Risks, and Implementation Plan.",
    },
    "research_docs": {
        "label": "Research synthesis",
        "instruction": "Use sections titled Answer, Evidence, and Caveats or Open Questions.",
    },
}


DEFAULT_RUBRICS: Dict[str, Dict[str, object]] = {
    "design_studio": {
        "label": "Design studio rubric",
        "score_range": "1-5",
        "effort_note": "For Effort, 5 means the fix or direction is relatively low effort and 1 means high effort.",
        "confidence_note": "For Confidence, 5 means strong confidence in the response quality.",
        "criteria": [
            {"key": "task_clarity", "label": "Task Clarity"},
            {"key": "hierarchy", "label": "Hierarchy"},
            {"key": "platform_fit", "label": "Platform Fit"},
            {"key": "accessibility", "label": "Accessibility"},
            {"key": "implementation_realism", "label": "Implementation Realism"},
            {"key": "effort", "label": "Effort"},
            {"key": "confidence", "label": "Confidence"},
        ],
    },
    "visual_review": {
        "label": "Visual review rubric",
        "score_range": "1-5",
        "effort_note": "For Effort, 5 means the fix is relatively low effort and 1 means high effort.",
        "confidence_note": "For Confidence, 5 means strong confidence in the response quality.",
        "criteria": [
            {"key": "hierarchy", "label": "Hierarchy"},
            {"key": "clarity", "label": "Clarity"},
            {"key": "accessibility", "label": "Accessibility"},
            {"key": "consistency", "label": "Consistency"},
            {"key": "effort", "label": "Effort"},
            {"key": "confidence", "label": "Confidence"},
        ],
    },
    "code_review": {
        "label": "Code review rubric",
        "score_range": "1-5",
        "effort_note": "For Effort, 5 means the fix is relatively low effort and 1 means high effort.",
        "confidence_note": "For Confidence, 5 means strong confidence in the response quality.",
        "criteria": [
            {"key": "correctness", "label": "Correctness"},
            {"key": "maintainability", "label": "Maintainability"},
            {"key": "security", "label": "Security"},
            {"key": "performance", "label": "Performance"},
            {"key": "testability", "label": "Testability"},
            {"key": "effort", "label": "Effort"},
            {"key": "confidence", "label": "Confidence"},
        ],
    },
}


def _normalize_session_key(session_type: Optional[str]) -> str:
    if not isinstance(session_type, str):
        return ""
    return session_type.strip().lower().replace("-", "_").replace(" ", "_")


def get_deliverable_spec(session_type: Optional[str], template_id: Optional[str] = None) -> Dict[str, str]:
    template = get_session_template(template_id, session_type=session_type)
    if template and template.get("deliverable_format") and template.get("deliverable_instruction"):
        return {
            "label": str(template["deliverable_format"]),
            "instruction": str(template["deliverable_instruction"]),
        }
    return DEFAULT_DELIVERABLES.get(session_type or "", {
        "label": "Final synthesis",
        "instruction": "Use a concise, practical structure with headings and action-oriented conclusions.",
    })


def get_rubric_spec(session_type: Optional[str]) -> Optional[Dict[str, object]]:
    spec = DEFAULT_RUBRICS.get(_normalize_session_key(session_type))
    if spec is None:
        return None

    criteria = spec.get("criteria") or []
    return {
        "label": str(spec.get("label") or "Rubric"),
        "score_range": str(spec.get("score_range") or "1-5"),
        "effort_note": str(spec.get("effort_note") or ""),
        "confidence_note": str(spec.get("confidence_note") or ""),
        "criteria": [
            {
                "key": str(item.get("key") or ""),
                "label": str(item.get("label") or ""),
            }
            for item in criteria
            if isinstance(item, dict) and item.get("key") and item.get("label")
        ],
    }

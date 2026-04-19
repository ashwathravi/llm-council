"""Built-in specialist templates for workspace sessions."""

from __future__ import annotations

from typing import Dict, List, Optional

SESSION_TEMPLATES: Dict[str, Dict[str, object]] = {
    "visual_ux_review": {
        "id": "visual_ux_review",
        "session_type": "visual_review",
        "label": "UX Review Council",
        "description": "Balances usability, clarity, product intent, and design execution.",
        "default_framework": "standard",
        "council_lenses": ["UX reviewer", "Visual designer", "Accessibility reviewer", "Product manager", "Brand reviewer"],
        "evaluation_criteria": ["Hierarchy", "Clarity", "Affordances", "Accessibility", "Consistency", "Task flow"],
        "synthesis_instruction": "Prioritize the most consequential issues, explain the user impact, and suggest practical design fixes.",
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

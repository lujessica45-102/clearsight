"""Four operational sectors with genuinely different decision parameters.

The brief says sectors are not yet defined in the repo, so these are a configurable proposal
(edit this dict to change them). All numeric parameters are PROTOTYPE ASSUMPTIONS, not USDA policy.
"""

SECTORS = {
    "service_center": {
        "label": "Service Centers",
        "description": "Public-facing county offices (e.g. FSA/NRCS/RD style) serving walk-in customers.",
        "public_facing": True,
        "params": {
            "delay_exposed_pct": 10, "telework_exposed_pct": 15, "closure_exposed_pct": 40,
            "prefer_telework_over_closure_telework_share": None,
        },
        "rationale": "Customers arrive unannounced and cannot be pre-warned, so the office acts earlier on facility-area hazards and has no round-the-clock essential minimum.",
        "playbook": {
            "normal": "Open; keep lobby staff aware of active watches.",
            "delayed_arrival": "Open late; post notice on door/phone line; reschedule appointments.",
            "telework": "Move to phones/online services; close lobby to walk-ins; forward office line.",
            "early_dismissal": "Close lobby first, release staff in waves; confirm no customers remain.",
            "closure": "Close to the public; staff stay home; post status on the service-center line and website.",
        },
    },
    "research_lab": {
        "label": "Research Labs & Stations",
        "description": "Labs and research stations with animals, plants, cold storage or experiments that cannot be left unattended.",
        "public_facing": False,
        "params": {
            "delay_exposed_pct": 15, "telework_exposed_pct": 25, "closure_exposed_pct": 60,
            "prefer_telework_over_closure_telework_share": None,
        },
        "rationale": "Essential care staff (animals, greenhouse, freezers) must keep coverage even when the rest of the site is closed, so thresholds are higher and essential staff are planned for separately.",
        "playbook": {
            "normal": "Normal operations; verify backup power and critical-care contact roster.",
            "delayed_arrival": "Non-essential staff arrive late; essential-care staff keep their shift if their route is not in a warning.",
            "telework": "Non-essential staff telework; essential-care staff on-site only if routes are clear, otherwise activate pre-positioned care roster.",
            "early_dismissal": "Complete critical care tasks first, then release non-essential staff; leave a minimal care crew.",
            "closure": "Closed to non-essential staff; essential-care crew stays on a pre-planned shelter/rotation roster; do not order essential staff to drive during an active warning.",
        },
    },
    "field_office": {
        "label": "Field Offices",
        "description": "Field-operations offices (inspection, wildlife, forestry-style) whose staff work outdoors or on the road.",
        "public_facing": False,
        "params": {
            "delay_exposed_pct": 10, "telework_exposed_pct": 20, "closure_exposed_pct": 50,
            "prefer_telework_over_closure_telework_share": None,
        },
        "rationale": "Outdoor/vehicle work is stopped before office work is, and low telework eligibility means exposed staff are more likely to need leave than telework.",
        "playbook": {
            "normal": "Normal operations; review field assignments against active watches.",
            "delayed_arrival": "Hold field deployments until conditions improve; office staff arrive late.",
            "telework": "Stand down all field work; eligible staff telework, others unscheduled leave.",
            "early_dismissal": "Recall field crews to base immediately, then release staff.",
            "closure": "Stand down all field operations; accountability check on field crews; staff stay home.",
        },
    },
    "headquarters": {
        "label": "Headquarters & Administrative",
        "description": "Large administrative/regional headquarters with high telework capability and continuity-of-operations duties.",
        "public_facing": False,
        "params": {
            "delay_exposed_pct": 15, "telework_exposed_pct": 20, "closure_exposed_pct": 50,
            "prefer_telework_over_closure_telework_share": 0.75,
        },
        "rationale": "With most staff able to work remotely, a hazard to commutes usually calls for telework rather than closure; closure is reserved for threats to the building itself.",
        "playbook": {
            "normal": "Normal operations.",
            "delayed_arrival": "Late arrival with telework option for anyone with a hazardous commute.",
            "telework": "Mandatory/unscheduled telework for eligible staff; COOP team on standby.",
            "early_dismissal": "Release staff early with telework from home to finish critical tasks.",
            "closure": "Building closed; COOP/telework continues for critical functions.",
        },
    },
}

POSTURES = ["normal", "delayed_arrival", "early_dismissal", "telework", "closure"]
# Mapping to OPM operating-status language (https://www.opm.gov/policy-data-oversight/snow-dismissal-procedures/)
POSTURE_LABELS = {
    "normal": "Normal operations (OPM: Open)",
    "delayed_arrival": "Delayed arrival (OPM: Open with delayed arrival)",
    "early_dismissal": "Early dismissal (OPM: Immediate/early departure)",
    "telework": "Unscheduled leave / telework (OPM: Open with option for unscheduled leave or unscheduled telework)",
    "closure": "Full closure (OPM: Closed)",
}
# Severity ordering used to compare/escalate postures.
POSTURE_RANK = {"normal": 0, "delayed_arrival": 1, "telework": 2, "early_dismissal": 3, "closure": 4}

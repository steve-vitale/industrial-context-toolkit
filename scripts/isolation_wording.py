"""The fixed wording every isolation or lockout/tagout (LOTO) output uses: the goal's header and the mockup status.

docs/GOAL_ISOLATION_POC.md fixes a header for the isolation boundary candidates proof of concept and forbids
directive wording (steps, valve positions, "isolate at X", zero-energy claims) in every isolation output. The two
existing LOTO design mockups (the OPEN100 `loto_isolation_points.csv` view and the TE 3D-tour LOTO scene) are not
that proof of concept and do not meet its safeguards, but they follow the same wording rules, read from here:

  - FIXED_HEADER is the goal's header, byte for byte (for the proof of concept's outputs once they exist);
  - MOCKUP_STATUS is the mockups' status: "DESIGN MOCKUP FOR A PROOF OF CONCEPT AND TESTING GROUND. NOT A
    PROCEDURE. All results must be verified by a qualified professional." (the owner's condition for any isolation
    output) followed by the fixed header from its third sentence on, byte for byte, so a mockup never borrows the
    proof of concept's name;
  - NOT_POSITIVE is the phrase a control, check or relief valve carries wherever a mockup lists one.

The banned-phrase check over every LOTO output lives in scripts/test_loto_wording.py, so tightening it never changes
a generator's code hash.

Stdlib only.
"""
FIXED_HEADER = (
    "ISOLATION BOUNDARY CANDIDATES. PROOF OF CONCEPT AND TESTING GROUND. THIS IS NOT AN ISOLATION OR LOCKOUT/TAGOUT "
    "PROCEDURE AND MUST NOT BE USED AS ONE. Every point and every path below must be verified by a qualified person "
    "against the as-built plant and the site's energy-control program (for example under OSHA 29 CFR 1910.147). It "
    "is read from drawings, which are not as-built: a point it does not list may exist, and a point it lists may not "
    "isolate. Electrical, pneumatic, hydraulic, stored-pressure, gravity and thermal energy are not assessed.")
_BODY = FIXED_HEADER[FIXED_HEADER.index("THIS IS NOT AN ISOLATION"):]
MOCKUP_STATUS = ("DESIGN MOCKUP FOR A PROOF OF CONCEPT AND TESTING GROUND. NOT A PROCEDURE. All results must be "
                 "verified by a qualified professional. " + _BODY)
NOT_POSITIVE = "not positive isolation"

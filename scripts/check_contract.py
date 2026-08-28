import ast
import pathlib

source = (pathlib.Path(__file__).resolve().parents[1] / "contracts" / "policy_change_gate.py").read_text(encoding="utf-8")
ast.parse(source)

for required in (
    "register_policy", "assess_change", "challenge_change", "resolve_challenge", "finalize_change",
    "only_policy_owner", "active_assessment_must_be_finalized_or_resolved",
    "only_unchallenged_assessments_can_finalize", "TreeMap", "DynArray",
):
    if required not in source:
        raise SystemExit(f"missing required control: {required}")

if 'proposed["source_commitment"] == independent["source_commitment"]' not in source:
    raise SystemExit("validator provenance commitment missing")
if 'observed_snapshot_hashes' not in source:
    raise SystemExit("evidence snapshot retention missing")

print("PolicyChangeGate contract structure check passed")

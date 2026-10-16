import ast
import pathlib

source = (pathlib.Path(__file__).resolve().parents[1] / "contracts" / "policy_change_gate.py").read_text(encoding="utf-8")
ast.parse(source)

for required in (
    "register_policy", "assess_change", "challenge_change", "resolve_challenge", "retry_change", "finalize_change",
    "set_guardians", "approve_change", "get_guardian_status", "get_latest_policy_id", "get_latest_assessment_id", "get_policy_timeline", "get_audit_pack",
    "CHALLENGE_WINDOW_SECONDS", "challenge_window_still_open", "RESOLVED_UPHELD", "RESOLVED_OVERTURNED",
    "observed_snapshot_hashes", "transition_log", "policy_record_hash", "assessment_record_hash", "guardian_approval_threshold_not_met",
    "hashlib.sha256", "guardian_commitment", "GUARDIAN_APPROVED",
):
    if required not in source:
        raise SystemExit(f"missing required control: {required}")

print("PolicyChangeGate audit-pack contract structure check passed")

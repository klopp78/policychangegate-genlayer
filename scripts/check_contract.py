import ast
import pathlib

source = (pathlib.Path(__file__).resolve().parents[1] / "contracts" / "policy_change_gate.py").read_text(encoding="utf-8")
ast.parse(source)

for required in (
    "register_policy", "assess_change", "challenge_change", "resolve_challenge", "retry_change", "finalize_change",
    "get_latest_policy_id", "get_latest_assessment_id", "CHALLENGE_WINDOW_SECONDS",
    "challenge_window_still_open", "RESOLVED_UPHELD", "RESOLVED_OVERTURNED", "observed_snapshot_hashes",
):
    if required not in source:
        raise SystemExit(f"missing required control: {required}")

print("PolicyChangeGate v2 contract structure check passed")

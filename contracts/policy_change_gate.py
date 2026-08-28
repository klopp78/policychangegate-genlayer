# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from datetime import datetime, timezone
import json


CHALLENGE_WINDOW_SECONDS = 86400


class PolicyChangeGate(gl.Contract):
    """Challengeable policy changes with an immutable, consensus-backed lifecycle."""

    policy_count: u64
    assessment_count: u64
    policies: TreeMap[str, str]
    assessments: TreeMap[str, str]
    policy_ids: DynArray[str]
    assessment_ids: DynArray[str]

    def __init__(self):
        self.policy_count = u64(0)
        self.assessment_count = u64(0)

    @gl.public.view
    def get_policy(self, policy_id: str) -> str:
        return self.policies.get(policy_id, "")

    @gl.public.view
    def get_assessment(self, assessment_id: str) -> str:
        return self.assessments.get(assessment_id, "")

    @gl.public.view
    def get_latest_policy_id(self) -> str:
        return "" if int(self.policy_count) == 0 else "pol_" + str(int(self.policy_count))

    @gl.public.view
    def get_latest_assessment_id(self) -> str:
        return "" if int(self.assessment_count) == 0 else "chg_" + str(int(self.assessment_count))

    @gl.public.view
    def list_policy_ids(self) -> str:
        return json.dumps([item for item in self.policy_ids], separators=(",", ":"))

    @gl.public.view
    def list_assessment_ids(self) -> str:
        return json.dumps([item for item in self.assessment_ids], separators=(",", ":"))

    @gl.public.write
    def register_policy(self, policy_url: str, governance_rules: str) -> str:
        policy_url = _canonical_url(policy_url)
        rules = governance_rules.strip()
        if len(rules) < 20:
            raise Exception("governance_rules_too_short")
        self.policy_count = u64(int(self.policy_count) + 1)
        policy_id = "pol_" + str(int(self.policy_count))
        self.policies[policy_id] = _dump({
            "policy_id": policy_id,
            "owner": str(gl.message.sender_address).lower(),
            "baseline_url": policy_url,
            "governance_rules": rules[:800],
            "baseline_commitment": _hash(policy_url + "|" + rules),
            "active_assessment_id": "",
            "version": 1,
            "created_at": _now(),
        })
        self.policy_ids.append(policy_id)
        return policy_id

    @gl.public.write
    def assess_change(self, policy_id: str, candidate_url: str) -> str:
        policy = _load_policy(self, policy_id)
        _require_owner(policy)
        if policy["active_assessment_id"]:
            raise Exception("active_assessment_must_finalize_or_resolve")
        return _create_assessment(self, policy, policy_id, candidate_url, "")

    @gl.public.write
    def challenge_change(self, assessment_id: str, challenge_url: str) -> str:
        assessment = _load_assessment(self, assessment_id)
        if assessment["state"] != "ASSESSED":
            raise Exception("only_open_assessments_can_be_challenged")
        if _now() > int(assessment["challenge_deadline"]):
            raise Exception("challenge_window_closed")
        challenge_url = _canonical_url(challenge_url)
        if challenge_url in (assessment["baseline_url"], assessment["candidate_url"]):
            raise Exception("challenge_requires_independent_evidence")
        assessment.update({
            "state": "CHALLENGED",
            "challenge_url": challenge_url,
            "challenge_commitment": _hash(challenge_url),
            "challenged_by": str(gl.message.sender_address).lower(),
            "challenged_at": _now(),
        })
        self.assessments[assessment_id] = _dump(assessment)
        return assessment_id

    @gl.public.write
    def resolve_challenge(self, assessment_id: str) -> str:
        assessment = _load_assessment(self, assessment_id)
        policy = _load_policy(self, assessment["policy_id"])
        _require_owner(policy)
        if assessment["state"] != "CHALLENGED":
            raise Exception("assessment_is_not_challenged")
        commitment = _source_commitment(policy["baseline_commitment"], assessment["candidate_url"], assessment["challenge_url"])

        def leader_fn():
            return _resolve_with_challenge(assessment, commitment)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                proposed = _parse_resolution(leader_result.calldata)
                independent = _parse_resolution(_resolve_with_challenge(assessment, commitment))
            except Exception:
                return False
            return proposed["resolution"] == independent["resolution"] and proposed["source_commitment"] == independent["source_commitment"]

        resolution = json.loads(gl.vm.run_nondet_unsafe(leader_fn, validator_fn))
        assessment["resolution"] = resolution
        assessment["resolved_at"] = _now()
        if resolution["resolution"] == "UPHOLD":
            assessment["state"] = "RESOLVED_UPHELD"
        else:
            assessment["state"] = "RESOLVED_OVERTURNED"
            policy["active_assessment_id"] = ""
            self.policies[assessment["policy_id"]] = _dump(policy)
        self.assessments[assessment_id] = _dump(assessment)
        return assessment_id

    @gl.public.write
    def retry_change(self, overturned_assessment_id: str, candidate_url: str) -> str:
        overturned = _load_assessment(self, overturned_assessment_id)
        policy = _load_policy(self, overturned["policy_id"])
        _require_owner(policy)
        if overturned["state"] != "RESOLVED_OVERTURNED":
            raise Exception("only_overturned_assessments_can_retry")
        if policy["active_assessment_id"]:
            raise Exception("another_assessment_is_active")
        return _create_assessment(self, policy, overturned["policy_id"], candidate_url, overturned_assessment_id)

    @gl.public.write
    def finalize_change(self, assessment_id: str) -> str:
        assessment = _load_assessment(self, assessment_id)
        policy = _load_policy(self, assessment["policy_id"])
        _require_owner(policy)
        if assessment["state"] not in ("ASSESSED", "RESOLVED_UPHELD"):
            raise Exception("assessment_cannot_finalize")
        if _now() < int(assessment["challenge_deadline"]):
            raise Exception("challenge_window_still_open")
        if assessment["result"]["decision"] not in ("NON_MATERIAL", "MATERIAL_ACCEPTABLE"):
            raise Exception("consensus_did_not_authorize_change")
        policy.update({
            "baseline_url": assessment["candidate_url"],
            "baseline_commitment": assessment["source_commitment"],
            "active_assessment_id": "",
            "version": int(policy["version"]) + 1,
        })
        assessment.update({"state": "FINALIZED", "finalized_at": _now()})
        self.policies[assessment["policy_id"]] = _dump(policy)
        self.assessments[assessment_id] = _dump(assessment)
        return assessment_id


def _create_assessment(contract: PolicyChangeGate, policy: dict, policy_id: str, candidate_url: str, retry_of: str) -> str:
    candidate_url = _canonical_url(candidate_url)
    if candidate_url == policy["baseline_url"]:
        raise Exception("candidate_must_differ_from_baseline")
    commitment = _source_commitment(policy["baseline_commitment"], candidate_url)

    def leader_fn():
        return _evaluate_change(policy, candidate_url, commitment)

    def validator_fn(leader_result) -> bool:
        if not isinstance(leader_result, gl.vm.Return):
            return False
        try:
            proposed = _parse_evaluation(leader_result.calldata)
            independent = _parse_evaluation(_evaluate_change(policy, candidate_url, commitment))
        except Exception:
            return False
        return proposed["decision"] == independent["decision"] and proposed["source_commitment"] == independent["source_commitment"] and abs(int(proposed["risk_score"]) - int(independent["risk_score"])) <= 20

    result = json.loads(gl.vm.run_nondet_unsafe(leader_fn, validator_fn))
    contract.assessment_count = u64(int(contract.assessment_count) + 1)
    assessment_id = "chg_" + str(int(contract.assessment_count))
    now = _now()
    contract.assessments[assessment_id] = _dump({
        "assessment_id": assessment_id,
        "policy_id": policy_id,
        "baseline_url": policy["baseline_url"],
        "candidate_url": candidate_url,
        "created_by": str(gl.message.sender_address).lower(),
        "state": "ASSESSED",
        "created_at": now,
        "challenge_deadline": now + CHALLENGE_WINDOW_SECONDS,
        "result": result,
        "source_commitment": commitment,
        "retry_of": retry_of,
        "challenge_url": "",
        "challenge_commitment": "",
        "resolution": {},
        "accepted_write": {"assessment_id": assessment_id, "sequence": int(contract.assessment_count)},
    })
    policy["active_assessment_id"] = assessment_id
    contract.policies[policy_id] = _dump(policy)
    contract.assessment_ids.append(assessment_id)
    return assessment_id


def _evaluate_change(policy: dict, candidate_url: str, commitment: str) -> str:
    baseline = gl.nondet.web.render(policy["baseline_url"], mode="text")[:6000]
    candidate = gl.nondet.web.render(candidate_url, mode="text")[:6000]
    prompt = f'''Compare a public governance policy baseline and candidate against the stated rules. Rules: {policy["governance_rules"]} Baseline: {baseline} Candidate: {candidate} Return minified JSON with decision (NON_MATERIAL, MATERIAL_ACCEPTABLE, MATERIAL_REJECTED, INSUFFICIENT), risk_score (0-100), summary (under 350 chars), and source_commitment exactly {commitment}.'''
    data = json.loads(gl.nondet.exec_prompt(prompt))
    return _dump({"decision": str(data["decision"]).upper(), "risk_score": max(0, min(100, int(data["risk_score"]))), "summary": str(data["summary"])[:350], "source_commitment": str(data["source_commitment"]), "observed_snapshot_hashes": [_hash(baseline), _hash(candidate)]})


def _resolve_with_challenge(assessment: dict, commitment: str) -> str:
    baseline = gl.nondet.web.render(assessment["baseline_url"], mode="text")[:4000]
    candidate = gl.nondet.web.render(assessment["candidate_url"], mode="text")[:4000]
    challenge = gl.nondet.web.render(assessment["challenge_url"], mode="text")[:4000]
    prompt = f'''Resolve a challenged policy assessment. Baseline: {baseline} Candidate: {candidate} Challenge: {challenge} Return minified JSON with resolution (UPHOLD or OVERTURN) and source_commitment exactly {commitment}.'''
    data = json.loads(gl.nondet.exec_prompt(prompt))
    return _dump({"resolution": str(data["resolution"]).upper(), "source_commitment": str(data["source_commitment"]), "observed_snapshot_hashes": [_hash(baseline), _hash(candidate), _hash(challenge)]})


def _parse_evaluation(raw: str) -> dict:
    data = json.loads(raw)
    if data.get("decision") not in ("NON_MATERIAL", "MATERIAL_ACCEPTABLE", "MATERIAL_REJECTED", "INSUFFICIENT") or int(data.get("risk_score", -1)) < 0 or int(data.get("risk_score", 101)) > 100 or not str(data.get("source_commitment", "")).startswith("h"):
        raise Exception("invalid_evaluation")
    return data


def _parse_resolution(raw: str) -> dict:
    data = json.loads(raw)
    if data.get("resolution") not in ("UPHOLD", "OVERTURN") or not str(data.get("source_commitment", "")).startswith("h"):
        raise Exception("invalid_resolution")
    return data


def _load_policy(contract: PolicyChangeGate, policy_id: str) -> dict:
    raw = contract.policies.get(policy_id, "")
    if not raw:
        raise Exception("policy_not_found")
    return json.loads(raw)


def _load_assessment(contract: PolicyChangeGate, assessment_id: str) -> dict:
    raw = contract.assessments.get(assessment_id, "")
    if not raw:
        raise Exception("assessment_not_found")
    return json.loads(raw)


def _require_owner(policy: dict):
    if str(gl.message.sender_address).lower() != policy["owner"]:
        raise Exception("only_policy_owner")


def _canonical_url(raw: str) -> str:
    value = str(raw).strip()
    if not value.startswith("https://") or len(value) > 500 or "?" in value or "#" in value:
        raise Exception("url_must_be_canonical_https")
    return value.rstrip("/")


def _source_commitment(*parts: str) -> str:
    return _hash("|".join(parts))


def _now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _hash(value: str) -> str:
    acc = 2166136261
    for char in value:
        acc = (acc ^ ord(char)) * 16777619 % 4294967296
    return "h" + hex(acc)[2:].rjust(8, "0")


def _dump(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

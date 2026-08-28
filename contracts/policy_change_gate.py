# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json
import typing


class PolicyChangeGate(gl.Contract):
    """Challengeable, consensus-gated authorization for public policy changes."""

    policy_count: u64
    assessment_count: u64
    policies: TreeMap[str, str]
    assessments: TreeMap[str, str]
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
    def list_assessment_ids(self) -> str:
        return json.dumps([item for item in self.assessment_ids], separators=(",", ":"))

    @gl.public.write
    def register_policy(self, policy_url: str, governance_rules: str) -> str:
        policy_url = _canonical_url(policy_url)
        if len(governance_rules.strip()) < 20:
            raise Exception("governance_rules_too_short")
        self.policy_count = u64(int(self.policy_count) + 1)
        policy_id = "pol_" + str(int(self.policy_count))
        self.policies[policy_id] = json.dumps(
            {
                "policy_id": policy_id,
                "owner": str(gl.message.sender_address).lower(),
                "baseline_url": policy_url,
                "baseline_url_hash": _hash(policy_url),
                "governance_rules": governance_rules.strip()[:800],
                "active_assessment_id": "",
                "version": 1,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return policy_id

    @gl.public.write
    def assess_change(self, policy_id: str, candidate_url: str) -> str:
        policy = _load_policy(self, policy_id)
        _require_owner(policy)
        if len(policy["active_assessment_id"]) > 0:
            raise Exception("active_assessment_must_be_finalized_or_resolved")

        candidate_url = _canonical_url(candidate_url)
        if candidate_url == policy["baseline_url"]:
            raise Exception("candidate_must_differ_from_baseline")
        commitment = _source_commitment(policy["baseline_url"], candidate_url)

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
            return (
                proposed["decision"] == independent["decision"]
                and proposed["source_commitment"] == independent["source_commitment"]
                and abs(int(proposed["risk_score"]) - int(independent["risk_score"])) <= 20
            )

        result = json.loads(gl.vm.run_nondet_unsafe(leader_fn, validator_fn))
        self.assessment_count = u64(int(self.assessment_count) + 1)
        assessment_id = "chg_" + str(int(self.assessment_count))
        self.assessments[assessment_id] = json.dumps(
            {
                "assessment_id": assessment_id,
                "policy_id": policy_id,
                "baseline_url": policy["baseline_url"],
                "candidate_url": candidate_url,
                "created_by": str(gl.message.sender_address).lower(),
                "state": "ASSESSED",
                "result": result,
                "challenge_url": "",
                "resolution": "",
                "accepted_write": {"assessment_id": assessment_id, "sequence": int(self.assessment_count)},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        policy["active_assessment_id"] = assessment_id
        self.policies[policy_id] = json.dumps(policy, sort_keys=True, separators=(",", ":"))
        self.assessment_ids.append(assessment_id)
        return assessment_id

    @gl.public.write
    def challenge_change(self, assessment_id: str, challenge_url: str) -> str:
        assessment = _load_assessment(self, assessment_id)
        if assessment["state"] != "ASSESSED":
            raise Exception("only_assessed_changes_can_be_challenged")
        challenge_url = _canonical_url(challenge_url)
        if challenge_url in (assessment["baseline_url"], assessment["candidate_url"]):
            raise Exception("challenge_requires_independent_evidence")
        assessment["state"] = "CHALLENGED"
        assessment["challenge_url"] = challenge_url
        assessment["challenged_by"] = str(gl.message.sender_address).lower()
        self.assessments[assessment_id] = json.dumps(assessment, sort_keys=True, separators=(",", ":"))
        return assessment_id

    @gl.public.write
    def resolve_challenge(self, assessment_id: str) -> str:
        assessment = _load_assessment(self, assessment_id)
        policy = _load_policy(self, assessment["policy_id"])
        _require_owner(policy)
        if assessment["state"] != "CHALLENGED":
            raise Exception("assessment_is_not_challenged")
        commitment = _source_commitment(
            assessment["baseline_url"], assessment["candidate_url"], assessment["challenge_url"]
        )

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
        assessment["state"] = "UPHELD" if resolution["resolution"] == "UPHOLD" else "OVERTURNED"
        self.assessments[assessment_id] = json.dumps(assessment, sort_keys=True, separators=(",", ":"))
        return assessment_id

    @gl.public.write
    def finalize_change(self, assessment_id: str) -> str:
        assessment = _load_assessment(self, assessment_id)
        policy = _load_policy(self, assessment["policy_id"])
        _require_owner(policy)
        if assessment["state"] != "ASSESSED":
            raise Exception("only_unchallenged_assessments_can_finalize")
        if assessment["result"]["decision"] not in ("NON_MATERIAL", "MATERIAL_ACCEPTABLE"):
            raise Exception("consensus_did_not_authorize_change")
        policy["baseline_url"] = assessment["candidate_url"]
        policy["baseline_url_hash"] = _hash(assessment["candidate_url"])
        policy["active_assessment_id"] = ""
        policy["version"] = int(policy["version"]) + 1
        assessment["state"] = "FINALIZED"
        self.policies[assessment["policy_id"]] = json.dumps(policy, sort_keys=True, separators=(",", ":"))
        self.assessments[assessment_id] = json.dumps(assessment, sort_keys=True, separators=(",", ":"))
        return assessment_id


def _evaluate_change(policy: dict, candidate_url: str, commitment: str) -> str:
    baseline = gl.nondet.web.render(policy["baseline_url"], mode="text")[:6000]
    candidate = gl.nondet.web.render(candidate_url, mode="text")[:6000]
    prompt = f'''Compare a public governance policy baseline and candidate against the stated rules.
Rules: {policy["governance_rules"]}
Baseline: {baseline}
Candidate: {candidate}
Return minified JSON with decision (NON_MATERIAL, MATERIAL_ACCEPTABLE, MATERIAL_REJECTED, INSUFFICIENT), risk_score (0-100), summary (under 350 chars), and source_commitment exactly {commitment}.'''
    data = json.loads(gl.nondet.exec_prompt(prompt))
    return json.dumps({"decision": str(data["decision"]).upper(), "risk_score": max(0, min(100, int(data["risk_score"]))), "summary": str(data["summary"])[:350], "source_commitment": str(data["source_commitment"]), "observed_snapshot_hashes": [_hash(baseline), _hash(candidate)]}, sort_keys=True, separators=(",", ":"))


def _resolve_with_challenge(assessment: dict, commitment: str) -> str:
    baseline = gl.nondet.web.render(assessment["baseline_url"], mode="text")[:4000]
    candidate = gl.nondet.web.render(assessment["candidate_url"], mode="text")[:4000]
    challenge = gl.nondet.web.render(assessment["challenge_url"], mode="text")[:4000]
    prompt = f'''Resolve a challenged policy assessment. Baseline: {baseline}\nCandidate: {candidate}\nChallenge: {challenge}\nReturn minified JSON with resolution (UPHOLD or OVERTURN) and source_commitment exactly {commitment}.'''
    data = json.loads(gl.nondet.exec_prompt(prompt))
    return json.dumps({"resolution": str(data["resolution"]).upper(), "source_commitment": str(data["source_commitment"])}, sort_keys=True, separators=(",", ":"))


def _parse_evaluation(raw: str) -> dict:
    data = json.loads(raw)
    if data.get("decision") not in ("NON_MATERIAL", "MATERIAL_ACCEPTABLE", "MATERIAL_REJECTED", "INSUFFICIENT"):
        raise Exception("invalid_decision")
    if int(data.get("risk_score", -1)) < 0 or int(data.get("risk_score", 101)) > 100:
        raise Exception("invalid_risk_score")
    if not str(data.get("source_commitment", "")).startswith("h"):
        raise Exception("invalid_source_commitment")
    return data


def _parse_resolution(raw: str) -> dict:
    data = json.loads(raw)
    if data.get("resolution") not in ("UPHOLD", "OVERTURN"):
        raise Exception("invalid_resolution")
    if not str(data.get("source_commitment", "")).startswith("h"):
        raise Exception("invalid_source_commitment")
    return data


def _load_policy(contract: PolicyChangeGate, policy_id: str) -> dict:
    raw = contract.policies.get(policy_id, "")
    if len(raw) == 0:
        raise Exception("policy_not_found")
    return json.loads(raw)


def _load_assessment(contract: PolicyChangeGate, assessment_id: str) -> dict:
    raw = contract.assessments.get(assessment_id, "")
    if len(raw) == 0:
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


def _source_commitment(*urls: str) -> str:
    return _hash("|".join(urls))


def _hash(value: str) -> str:
    acc = 2166136261
    for char in value:
        acc = (acc ^ ord(char)) * 16777619 % 4294967296
    return "h" + hex(acc)[2:].rjust(8, "0")

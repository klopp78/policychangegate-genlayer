"""Deterministic lifecycle model for the contract's authorization invariants."""

from dataclasses import dataclass


@dataclass
class Assessment:
    state: str
    deadline: int
    transition_log: list
    guardians: list
    threshold: int
    approvals: list


class GateModel:
    def __init__(self):
        self.now = 100
        self.policy_id = ""
        self.active = ""
        self.assessments = {}
        self.policy_count = 0
        self.change_count = 0

    def register(self):
        self.policy_count += 1
        self.policy_id = f"pol_{self.policy_count}"
        return self.policy_id

    def assess(self, guardians=None, threshold=0):
        assert self.policy_id and not self.active
        self.change_count += 1
        change_id = f"chg_{self.change_count}"
        self.assessments[change_id] = Assessment("ASSESSED", self.now + 10, ["ASSESSED"], guardians or [], threshold, [])
        self.active = change_id
        return change_id

    def challenge(self, change_id):
        item = self.assessments[change_id]
        assert item.state == "ASSESSED" and self.now <= item.deadline
        item.state = "CHALLENGED"
        item.transition_log.append("CHALLENGED")

    def resolve(self, change_id, uphold):
        item = self.assessments[change_id]
        assert item.state == "CHALLENGED"
        item.state = "RESOLVED_UPHELD" if uphold else "RESOLVED_OVERTURNED"
        item.transition_log.append(item.state)
        if not uphold:
            self.active = ""

    def finalize(self, change_id):
        item = self.assessments[change_id]
        assert item.state in ("ASSESSED", "RESOLVED_UPHELD") and self.now >= item.deadline
        assert len(item.approvals) >= item.threshold
        item.state = "FINALIZED"
        item.transition_log.append("FINALIZED")
        self.active = ""

    def audit_pack(self, change_id):
        item = self.assessments[change_id]
        return {"assessment_id": change_id, "state": item.state, "transition_log": item.transition_log, "guardians": item.guardians, "approvals": item.approvals}

    def approve(self, change_id, guardian):
        item = self.assessments[change_id]
        assert self.now >= item.deadline and guardian in item.guardians and guardian not in item.approvals
        item.approvals.append(guardian)
        item.transition_log.append("GUARDIAN_APPROVED")


def test_register_assess_challenge_resolve_and_finalize():
    gate = GateModel()
    assert gate.register() == "pol_1"
    first = gate.assess()
    gate.challenge(first)
    gate.resolve(first, uphold=True)
    gate.now = 110
    gate.finalize(first)
    assert gate.assessments[first].state == "FINALIZED" and not gate.active


def test_overturned_challenge_releases_policy_for_retry():
    gate = GateModel()
    gate.register()
    first = gate.assess()
    gate.challenge(first)
    gate.resolve(first, uphold=False)
    assert gate.assessments[first].state == "RESOLVED_OVERTURNED" and not gate.active
    retry = gate.assess()
    assert retry == "chg_2"


def test_challenge_window_blocks_late_challenge_and_early_finalization():
    gate = GateModel()
    gate.register()
    change = gate.assess()
    try:
        gate.finalize(change)
    except AssertionError:
        pass
    else:
        raise AssertionError("early finalization was allowed")
    gate.now = 111
    try:
        gate.challenge(change)
    except AssertionError:
        pass
    else:
        raise AssertionError("late challenge was allowed")


def test_audit_pack_preserves_transition_log():
    gate = GateModel()
    gate.register()
    change = gate.assess()
    gate.challenge(change)
    gate.resolve(change, uphold=True)
    pack = gate.audit_pack(change)
    assert pack["assessment_id"] == "chg_1"
    assert pack["state"] == "RESOLVED_UPHELD"
    assert pack["transition_log"] == ["ASSESSED", "CHALLENGED", "RESOLVED_UPHELD"]


def test_guardian_threshold_is_a_real_finalization_boundary():
    gate = GateModel()
    gate.register()
    change = gate.assess(["guardian-a", "guardian-b"], threshold=2)
    gate.now = 110
    gate.approve(change, "guardian-a")
    try:
        gate.finalize(change)
    except AssertionError:
        pass
    else:
        raise AssertionError("a single guardian bypassed a 2-of-2 threshold")
    gate.approve(change, "guardian-b")
    gate.finalize(change)
    pack = gate.audit_pack(change)
    assert pack["approvals"] == ["guardian-a", "guardian-b"]


if __name__ == "__main__":
    test_register_assess_challenge_resolve_and_finalize()
    test_overturned_challenge_releases_policy_for_retry()
    test_challenge_window_blocks_late_challenge_and_early_finalization()
    test_audit_pack_preserves_transition_log()
    test_guardian_threshold_is_a_real_finalization_boundary()
    print("PolicyChangeGate lifecycle tests passed")

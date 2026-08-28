"""Deterministic lifecycle model for the contract's authorization invariants."""

from dataclasses import dataclass


@dataclass
class Assessment:
    state: str
    deadline: int


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

    def assess(self):
        assert self.policy_id and not self.active
        self.change_count += 1
        change_id = f"chg_{self.change_count}"
        self.assessments[change_id] = Assessment("ASSESSED", self.now + 10)
        self.active = change_id
        return change_id

    def challenge(self, change_id):
        item = self.assessments[change_id]
        assert item.state == "ASSESSED" and self.now <= item.deadline
        item.state = "CHALLENGED"

    def resolve(self, change_id, uphold):
        item = self.assessments[change_id]
        assert item.state == "CHALLENGED"
        item.state = "RESOLVED_UPHELD" if uphold else "RESOLVED_OVERTURNED"
        if not uphold:
            self.active = ""

    def finalize(self, change_id):
        item = self.assessments[change_id]
        assert item.state in ("ASSESSED", "RESOLVED_UPHELD") and self.now >= item.deadline
        item.state = "FINALIZED"
        self.active = ""


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


if __name__ == "__main__":
    test_register_assess_challenge_resolve_and_finalize()
    test_overturned_challenge_releases_policy_for_retry()
    test_challenge_window_blocks_late_challenge_and_early_finalization()
    print("PolicyChangeGate lifecycle tests passed")

# PolicyChangeGate for GenLayer

## Interactive project

The web app connects a Studio wallet to register baselines, request consensus
assessment for a candidate policy URL, submit a challenge, resolve it, finalize
an eligible change, and read exact persistent contract records.

- Contract v2: `0x2AA8243bBF30148557Bdbf6f34aC07c31DACea41`
- Explorer: https://explorer-studio.genlayer.com/address/0x2AA8243bBF30148557Bdbf6f34aC07c31DACea41
- Source: https://github.com/klopp78/policychangegate-genlayer

PolicyChangeGate is a challengeable authorization workflow for public policy,
specification, or governance-document changes. A policy owner registers an
immutable baseline URL and rules, submits a candidate, receives a GenLayer
consensus assessment, and either finalizes an unchallenged acceptable change or
resolves a challenge using independent counter-evidence.

## Lifecycle

1. `register_policy` establishes an owner-bound baseline.
2. `assess_change` produces a durable `ASSESSED` record with a stable source commitment.
3. Any account may `challenge_change` with an independent HTTPS source.
4. The owner can `resolve_challenge`, creating `UPHELD` or `OVERTURNED`.
5. Only an unchallenged consensus-approved assessment may `finalize_change` and advance the baseline.

Every assessment is stored by its contract-generated `chg_*` ID, retains the
accepted-write sequence, a 24-hour challenge deadline, retry ancestry, and
immutable URL/rendered-source commitments. An upheld challenge can finalize
only after the window closes; an overturned challenge releases the policy for a
new `retry_change` assessment. Validators compare structured decisions and
stable commitments rather than exact dynamic page HTML.

## Verification

```powershell
python scripts/check_contract.py
python tests/test_lifecycle.py
```

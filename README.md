# PolicyChangeGate for GenLayer

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

Every assessment is stored by ID, retains the accepted-write sequence, and can
be retrieved with `get_assessment`. Validators compare structured decisions and
stable URL provenance commitments rather than exact dynamic page HTML.

## Verification

```powershell
python scripts/check_contract.py
```

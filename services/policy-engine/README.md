# Policy engine (Phase 3)

Deterministic evaluation of **action proposals** against **execution context** facts. Returns `allow`, `deny`, or `conditional`. Does not persist rows, drive execution state, or invoke tools.

## Package layout

- `policy_engine/evaluator.py` — rule logic
- `policy_engine/service.py` — callable façade for the orchestrator

## Rule pack (`phase3_deterministic_v1`)

- `action_type` must be `escalate_incident` (other actions → deny).
- `policy_scope == phase3_deny` → **deny**.
- `environment == prod` or `policy_scope == phase3_conditional` → **conditional** (approval required).
- Otherwise → **allow**.

## Tests

From `services/policy-engine` with `common-schemas` on `PYTHONPATH`:

```bash
export PYTHONPATH=../../packages/common-schemas/src:.
python -m pytest tests -q
```

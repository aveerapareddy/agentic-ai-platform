# Policy engine (Phase 3)

Deterministic evaluation of **action proposals** against **execution context** facts. Returns `allow`, `deny`, or `conditional`. Does not persist rows, drive execution state, or invoke tools. **Gateway** exposes read/simulate APIs; this service owns evaluation logic only.

## Package layout

- `policy_engine/evaluator.py` — rule logic
- `policy_engine/service.py` — callable façade for the orchestrator

## Rule pack (`phase3_deterministic_v1`)

- `action_type` must be `escalate_incident` (other actions → deny).
- `policy_scope == phase3_deny` → **deny**.
- `environment == prod` or `policy_scope == phase3_conditional` → **conditional** (approval required).
- Otherwise → **allow**.

## Rule descriptors and simulation (Session E)

- `list_rule_descriptors()` — static catalog (`rule_id`, `description`, `applies_to`, `decision`, `reason`).
- `simulate_policy(PolicySimulateRequest, tenant_id=…)` — runs the same evaluator as runtime; returns `PolicySimulateResult` with matched rules and references.

No dynamic rule DSL or rule mutation in this session.

## Tests

From `services/policy-engine` with `common-schemas` on `PYTHONPATH`:

```bash
export PYTHONPATH=../../packages/common-schemas/src:.
python -m pytest tests -q
```

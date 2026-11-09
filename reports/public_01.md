# Grade report — public_01_dev

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.335 | -2.0% | 0.240 | -1.9% | 0.492 | +0.1% | 0% | 55 (57) |
| nw_kyc | 0.423 | +15.4% | 0.275 | +13.5% | 0.601 | +0.6% | 0% | 28 (21) |
| nw_renewal | 0.446 | +7.1% | 0.278 | +5.3% | 0.546 | +0.9% | 7% | 42 (54) |
| ALL | 0.391 | +5.1% | 0.260 | +3.6% | 0.534 | +0.9% | 3% | 125 (132) |

## Changes applied by the controller

6 applied — beneficial: 4, neutral: 2

- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.026 didΔ=-0.018 → **beneficial**
- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.102 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.082 → **beneficial**
- nw_renewal v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.004 → **neutral**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.258 → **beneficial**

## Governance

```
{
  "approval_requests": 5,
  "decisions": {
    "approved": 4,
    "rejected": 1,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 1
  },
  "applied_via_approval": 4,
  "auto_applied": 2,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "nw_renewal": 1,
    "nw_kyc": 1,
    "ks_cancel": 1
  }
}
```

## Incidents

```
[]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{
  "nw_renewal:welcome_message=W3": {
    "3": 0.129,
    "4": 0.129,
    "5": 0.123,
    "6": 0.137,
    "7": 0.131
  }
}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0
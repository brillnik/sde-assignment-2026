# Grade report — public_01_dev

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.344 | +0.7% | 0.241 | -1.6% | 0.503 | +2.2% | -0% | 58 (57) |
| nw_kyc | 0.406 | +10.8% | 0.263 | +8.5% | 0.604 | +1.2% | 0% | 34 (21) |
| nw_renewal | 0.449 | +7.8% | 0.276 | +4.6% | 0.555 | +2.4% | 7% | 47 (54) |
| ALL | 0.392 | +5.4% | 0.257 | +2.5% | 0.542 | +2.3% | 3% | 139 (132) |

## Changes applied by the controller

6 applied — neutral: 2, beneficial: 4

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.026 didΔ=-0.016 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.010 → **neutral**
- nw_renewal v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.050 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.075 → **beneficial**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.143 → **beneficial**

## Governance

```
{
  "approval_requests": 6,
  "decisions": {
    "rejected": 2,
    "approved": 4,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 2
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
    "3": 0.118,
    "4": 0.117,
    "5": 0.123,
    "6": 0.131,
    "7": 0.126
  }
}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0
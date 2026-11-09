# Grade report — pert_C

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.304 | +30.7% | 0.210 | +21.1% | 0.501 | +5.8% | 44% | 74 (241) |
| nw_kyc | 0.450 | +17.1% | 0.290 | +18.3% | 0.585 | -2.3% | 0% | 36 (18) |
| nw_renewal | 0.465 | +36.9% | 0.279 | +30.8% | 0.554 | +1.6% | 7% | 70 (45) |
| ALL | 0.389 | +29.4% | 0.249 | +24.0% | 0.540 | +2.1% | 14% | 180 (304) |

## Changes applied by the controller

16 applied — beneficial: 10, neutral: 6

- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.012 didΔ=+0.025 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.075 → **beneficial**
- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- ks_cancel v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.005 → **neutral**
- ks_cancel v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.005 → **neutral**
- ks_cancel v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.003 → **neutral**
- ks_cancel v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.027 → **beneficial**
- ks_cancel v7 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.027 → **beneficial**
- ks_cancel v8 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.015 → **neutral**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.049 → **beneficial**
- ks_cancel v9 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.029 → **beneficial**
- ks_cancel v10 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.028 → **beneficial**
- ks_cancel v11 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.009 → **neutral**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.198 → **beneficial**
- nw_renewal v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.146 → **beneficial**
- ks_cancel v13 (controller_approved) dims=['prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**

## Governance

```
{
  "approval_requests": 5,
  "decisions": {
    "approved": 5,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 5,
  "auto_applied": 11,
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
[
  {
    "type": "did_flagged",
    "workflow": "ks_cancel",
    "at": "D1 11:00",
    "flagged_did_share_by_day": {
      "1": 0.02,
      "2": 0.021,
      "3": 0.019,
      "4": 0.021,
      "5": 0.021,
      "6": 0.021,
      "7": 0.018,
      "8": 0.022,
      "9": 0.025
    }
  },
  {
    "type": "did_flagged",
    "workflow": "nw_renewal",
    "at": "D3 15:00",
    "flagged_did_share_by_day": {
      "3": 0.163,
      "4": 0.021,
      "5": 0.023,
      "6": 0.021,
      "7": 0.02,
      "8": 0.018,
      "9": 0.021
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "nw_renewal",
    "at": "D4 12:00"
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D5 11:30",
    "mttr_minutes": 285,
    "fixed_by": "controller_approved"
  }
]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{}
```

Credits used: 3 · validation runs: 1 · LLM fix calls: 0
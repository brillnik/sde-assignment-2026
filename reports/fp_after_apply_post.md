# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.362 | +53.8% | 0.247 | +36.3% | 0.502 | +7.2% | 35% | 75 (348) |
| nw_kyc | 0.458 | +22.5% | 0.287 | +22.3% | 0.603 | -0.9% | 0% | 32 (29) |
| nw_renewal | 0.480 | +10.8% | 0.288 | +9.9% | 0.555 | +0.1% | 6% | 66 (54) |
| ALL | 0.422 | +27.5% | 0.269 | +22.5% | 0.542 | +1.8% | 22% | 173 (431) |

## Changes applied by the controller

17 applied — neutral: 6, beneficial: 11

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.009 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.015 didΔ=+0.026 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.086 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.054 → **beneficial**
- ks_cancel v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.179 → **beneficial**
- ks_cancel v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.152 → **beneficial**
- ks_cancel v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.088 → **beneficial**
- ks_cancel v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.037 → **beneficial**
- ks_cancel v7 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.036 → **beneficial**
- ks_cancel v8 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.035 → **beneficial**
- ks_cancel v9 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.015 → **neutral**
- ks_cancel v11 (controller_approved) dims=['prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.200 → **beneficial**
- nw_renewal v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.010 → **neutral**
- ks_cancel v12 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.006 → **neutral**
- ks_cancel v13 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.007 → **neutral**
- ks_cancel v14 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.008 → **neutral**

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
  "auto_applied": 12,
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
    "at": "D2 10:00",
    "flagged_did_share_by_day": {
      "2": 0.115,
      "3": 0.017,
      "4": 0.022,
      "5": 0.019,
      "6": 0.021,
      "7": 0.016,
      "8": 0.018,
      "9": 0.018
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D3 11:30",
    "mttr_minutes": 165,
    "fixed_by": "controller_approved"
  },
  {
    "type": "supervisor_edit",
    "workflow": "nw_renewal",
    "at": "D5 15:00"
  }
]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{
  "nw_renewal:welcome_message=W3": {
    "2": 0.115,
    "3": 0.128,
    "4": 0.132,
    "5": 0.133,
    "6": 0.121,
    "7": 0.121,
    "8": 0.123,
    "9": 0.127
  }
}
```

Credits used: 3 · validation runs: 1 · LLM fix calls: 0
# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.348 | +47.6% | 0.243 | +34.3% | 0.488 | +4.4% | 36% | 91 (348) |
| nw_kyc | 0.465 | +24.5% | 0.293 | +25.1% | 0.596 | -2.0% | -8% | 30 (29) |
| nw_renewal | 0.482 | +11.4% | 0.288 | +9.9% | 0.558 | +0.5% | 5% | 67 (54) |
| ALL | 0.418 | +26.3% | 0.268 | +22.3% | 0.537 | +0.8% | 20% | 188 (431) |

## Changes applied by the controller

18 applied — beneficial: 12, harmful: 2, neutral: 4

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.013 didΔ=+0.000 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=-0.013 didΔ=+0.064 → **harmful**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.020 didΔ=+0.023 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.053 → **beneficial**
- ks_cancel v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.179 → **beneficial**
- ks_cancel v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.152 → **beneficial**
- ks_cancel v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.088 → **beneficial**
- ks_cancel v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.034 → **beneficial**
- ks_cancel v7 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.034 → **beneficial**
- ks_cancel v8 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.033 → **beneficial**
- ks_cancel v9 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.009 → **neutral**
- nw_kyc v3 (controller_approved) dims=['welcome_message', 'caller_id'] engageΔ=+0.028 didΔ=+0.259 → **beneficial**
- ks_cancel v11 (controller_approved) dims=['prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**
- ks_cancel v12 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.009 → **neutral**
- nw_kyc v4 (controller_approved) dims=['welcome_message'] engageΔ=-0.027 didΔ=+0.000 → **harmful**
- nw_renewal v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.005 → **neutral**
- nw_kyc v5 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.002 → **neutral**
- nw_kyc v6 (controller_approved) dims=['welcome_message'] engageΔ=+0.028 didΔ=+0.000 → **beneficial**

## Governance

```
{
  "approval_requests": 9,
  "decisions": {
    "rejected": 1,
    "approved": 8,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 1
  },
  "applied_via_approval": 8,
  "auto_applied": 10,
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
      "2": 0.1,
      "3": 0.023,
      "4": 0.021,
      "5": 0.017,
      "6": 0.023,
      "7": 0.019,
      "8": 0.021,
      "9": 0.021
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D3 11:30",
    "mttr_minutes": 300,
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
    "3": 0.161,
    "4": 0.176,
    "5": 0.171,
    "6": 0.165,
    "7": 0.161,
    "8": 0.178,
    "9": 0.183
  }
}
```

Credits used: 3 · validation runs: 1 · LLM fix calls: 0
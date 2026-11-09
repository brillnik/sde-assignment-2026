# Grade report — pert_A

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.368 | +15.9% | 0.255 | +14.4% | 0.495 | +0.1% | -3% | 77 (52) |
| nw_kyc | 0.467 | +25.5% | 0.302 | +24.2% | 0.582 | -0.6% | 0% | 38 (23) |
| nw_renewal | 0.453 | +42.5% | 0.283 | +46.9% | 0.536 | -4.9% | -23% | 74 (126) |
| ALL | 0.417 | +26.7% | 0.274 | +26.6% | 0.528 | -1.4% | -10% | 189 (201) |

## Changes applied by the controller

9 applied — beneficial: 7, neutral: 1, harmful: 1

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=-0.004 didΔ=+0.029 → **beneficial**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.014 didΔ=+0.061 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.167 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.223 → **beneficial**
- ks_cancel v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.015 → **neutral**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.070 → **beneficial**
- nw_renewal v5 (controller_approved) dims=['prompt_version'] engageΔ=-0.047 didΔ=+0.000 → **harmful**
- ks_cancel v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.107 → **beneficial**
- ks_cancel v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.061 → **beneficial**

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
  "auto_applied": 4,
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
    "workflow": "nw_renewal",
    "at": "D1 14:00",
    "flagged_did_share_by_day": {
      "1": 0.176,
      "2": 0.019,
      "3": 0.02,
      "4": 0.017,
      "5": 0.016,
      "6": 0.022,
      "7": 0.021,
      "8": 0.017,
      "9": 0.021
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "nw_renewal",
    "at": "D4 10:30",
    "mttr_minutes": 1425,
    "fixed_by": "controller_approved"
  },
  {
    "type": "did_flagged",
    "workflow": "ks_cancel",
    "at": "D6 12:00",
    "flagged_did_share_by_day": {
      "6": 0.147,
      "7": 0.018,
      "8": 0.021,
      "9": 0.021
    }
  }
]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{
  "nw_renewal:welcome_message=W2": {
    "3": 0.122,
    "4": 0.114,
    "5": 0.127,
    "6": 0.124,
    "7": 0.128,
    "8": 0.124,
    "9": 0.12
  }
}
```

Credits used: 3 · validation runs: 1 · LLM fix calls: 0
# Grade report — pert_A

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.359 | +13.0% | 0.247 | +11.0% | 0.497 | +0.6% | -1% | 80 (52) |
| nw_kyc | 0.457 | +22.9% | 0.296 | +21.5% | 0.584 | -0.4% | 0% | 34 (23) |
| nw_renewal | 0.453 | +42.4% | 0.277 | +43.9% | 0.547 | -2.9% | -23% | 68 (126) |
| ALL | 0.411 | +24.9% | 0.267 | +23.4% | 0.534 | -0.4% | -9% | 182 (201) |

## Changes applied by the controller

15 applied — neutral: 2, beneficial: 11, harmful: 2

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.004 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.014 didΔ=+0.024 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.086 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.042 → **beneficial**
- nw_renewal v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.162 → **beneficial**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.203 → **beneficial**
- nw_renewal v6 (controller_approved) dims=['prompt_version'] engageΔ=-0.047 didΔ=+0.000 → **harmful**
- ks_cancel v3 (controller_approved) dims=['cohorts', 'voice', 'schedule'] engageΔ=+0.022 didΔ=+0.000 → **beneficial**
- ks_cancel v4 (controller_approved) dims=['cohorts', 'voice', 'schedule'] engageΔ=-0.021 didΔ=+0.000 → **harmful**
- ks_cancel v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.126 → **beneficial**
- ks_cancel v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.112 → **beneficial**
- ks_cancel v7 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.067 → **beneficial**
- ks_cancel v8 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.039 → **beneficial**
- ks_cancel v9 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.038 → **beneficial**
- ks_cancel v10 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.017 → **neutral**

## Governance

```
{
  "approval_requests": 7,
  "decisions": {
    "approved": 7,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 7,
  "auto_applied": 8,
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
      "1": 0.17,
      "2": 0.022,
      "3": 0.019,
      "4": 0.021,
      "5": 0.019,
      "6": 0.022,
      "7": 0.025,
      "8": 0.02,
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
      "6": 0.225,
      "7": 0.022,
      "8": 0.019,
      "9": 0.019
    }
  }
]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{
  "nw_renewal:welcome_message=W2": {
    "3": 0.121,
    "4": 0.118,
    "5": 0.119,
    "6": 0.122,
    "7": 0.121,
    "8": 0.121,
    "9": 0.117
  }
}
```

Credits used: 3 · validation runs: 1 · LLM fix calls: 0
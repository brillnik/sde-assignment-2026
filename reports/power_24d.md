# Grade report — power_24d

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.396 | +5.9% | 0.261 | +7.6% | 0.491 | -1.5% | 0% | 171 (157) |
| nw_kyc | 0.522 | +31.1% | 0.315 | +30.9% | 0.599 | -0.6% | 0% | 90 (64) |
| nw_renewal | 0.484 | +6.5% | 0.281 | +6.4% | 0.547 | +0.1% | 2% | 167 (152) |
| ALL | 0.452 | +11.4% | 0.278 | +11.5% | 0.534 | -0.3% | 1% | 428 (373) |

## Changes applied by the controller

6 applied — beneficial: 4, harmful: 1, neutral: 1

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=-0.000 didΔ=+0.028 → **beneficial**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.026 didΔ=-0.046 → **harmful**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.193 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.092 → **beneficial**
- ks_cancel v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.015 → **neutral**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.094 → **beneficial**

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
    "3": 0.131,
    "4": 0.117,
    "5": 0.129,
    "6": 0.127,
    "7": 0.125,
    "8": 0.129,
    "9": 0.126,
    "10": 0.121,
    "11": 0.113,
    "12": 0.131,
    "13": 0.122,
    "14": 0.123,
    "15": 0.124,
    "16": 0.133,
    "17": 0.121,
    "18": 0.115,
    "19": 0.126,
    "20": 0.124,
    "21": 0.126,
    "22": 0.117,
    "23": 0.129
  }
}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0
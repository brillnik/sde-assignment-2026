# Grade report — public_03_load

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.345 | +2.4% | 0.243 | +0.0% | 0.507 | +2.1% | 12% | 373 (409) |
| arav_kyc_1 | 0.442 | +23.2% | 0.257 | +19.3% | 0.599 | -0.3% | 0% | 403 (352) |
| arav_renewal_0 | 0.457 | +12.8% | 0.282 | +6.8% | 0.575 | +5.0% | 29% | 445 (408) |
| kest_cancel_2 | 0.342 | +1.6% | 0.246 | +1.3% | 0.498 | -0.2% | 5% | 407 (418) |
| kest_kyc_1 | 0.382 | +7.3% | 0.227 | +6.0% | 0.596 | -0.2% | 0% | 382 (370) |
| kest_renewal_0 | 0.466 | +15.8% | 0.282 | +6.6% | 0.584 | +7.2% | 35% | 429 (403) |
| nort_cancel_2 | 0.340 | +0.3% | 0.246 | +0.8% | 0.495 | -0.6% | -1% | 370 (368) |
| nort_kyc_1 | 0.474 | +33.2% | 0.274 | +27.3% | 0.596 | +0.1% | 0% | 505 (318) |
| nort_renewal_0 | 0.456 | +12.5% | 0.283 | +7.1% | 0.571 | +4.2% | 23% | 442 (419) |
| tide_cancel_2 | 0.351 | +2.4% | 0.244 | +0.1% | 0.512 | +2.1% | 18% | 406 (401) |
| tide_kyc_1 | 0.471 | +32.2% | 0.271 | +26.4% | 0.596 | -0.4% | 0% | 427 (376) |
| tide_renewal_0 | 0.466 | +15.3% | 0.283 | +7.0% | 0.584 | +7.1% | 37% | 453 (425) |
| ALL | 0.416 | +13.5% | 0.262 | +8.6% | 0.561 | +2.8% | 14% | 5042 (4667) |

## Changes applied by the controller

51 applied — neutral: 19, beneficial: 30, harmful: 2

- nort_cancel_2 v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- kest_renewal_0 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.026 didΔ=-0.020 → **beneficial**
- tide_renewal_0 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.026 didΔ=-0.020 → **beneficial**
- tide_cancel_2 v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- tide_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.084 → **beneficial**
- tide_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.004 → **neutral**
- kest_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.085 → **beneficial**
- arav_cancel_2 v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- kest_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.002 → **neutral**
- nort_kyc_1 v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.091 → **beneficial**
- arav_renewal_0 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.026 didΔ=-0.018 → **beneficial**
- nort_renewal_0 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.026 didΔ=-0.018 → **beneficial**
- nort_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.077 → **beneficial**
- arav_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.071 → **beneficial**
- tide_kyc_1 v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.098 → **beneficial**
- arav_kyc_1 v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.100 → **beneficial**
- kest_renewal_0 v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.020 → **neutral**
- kest_kyc_1 v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.079 → **beneficial**
- kest_cancel_2 v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- nort_renewal_0 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.039 didΔ=+0.000 → **beneficial**
- tide_cancel_2 v3 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.028 didΔ=+0.000 → **beneficial**
- arav_cancel_2 v3 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=-0.007 didΔ=+0.000 → **neutral**
- nort_cancel_2 v3 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.003 didΔ=+0.000 → **neutral**
- tide_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.077 didΔ=+0.000 → **beneficial**
- nort_kyc_1 v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.411 → **beneficial**
- arav_renewal_0 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.042 didΔ=+0.000 → **beneficial**
- kest_renewal_0 v6 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.066 didΔ=+0.000 → **beneficial**
- tide_kyc_1 v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.411 → **beneficial**
- tide_renewal_0 v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.005 → **neutral**
- arav_kyc_1 v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.346 → **beneficial**
- arav_cancel_2 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.019 didΔ=+0.000 → **beneficial**
- tide_renewal_0 v7 (controller_approved) dims=['cohorts', 'voice', 'schedule'] engageΔ=+0.017 didΔ=+0.000 → **beneficial**
- nort_cancel_2 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'schedule'] engageΔ=-0.012 didΔ=+0.000 → **harmful**
- nort_renewal_0 v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.001 → **neutral**
- tide_cancel_2 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.017 didΔ=+0.000 → **beneficial**
- arav_renewal_0 v5 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.021 didΔ=+0.000 → **beneficial**
- kest_renewal_0 v7 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.027 didΔ=+0.000 → **beneficial**
- arav_cancel_2 v5 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.031 didΔ=+0.000 → **beneficial**
- nort_cancel_2 v5 (controller_approved) dims=['cohorts', 'welcome_message', 'schedule'] engageΔ=+0.011 didΔ=+0.000 → **beneficial**
- kest_renewal_0 v8 (controller_approved) dims=['cohorts', 'voice', 'caller_id', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- tide_cancel_2 v5 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- nort_renewal_0 v6 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=-0.020 didΔ=+0.000 → **harmful**
- arav_renewal_0 v6 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.023 didΔ=+0.000 → **beneficial**
- nort_renewal_0 v7 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- tide_cancel_2 v6 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=-0.004 didΔ=+0.000 → **neutral**
- tide_renewal_0 v8 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- kest_cancel_2 v3 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.054 didΔ=+0.000 → **beneficial**
- nort_cancel_2 v6 (controller_approved) dims=['cohorts', 'welcome_message', 'schedule'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- arav_cancel_2 v6 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.013 didΔ=+0.000 → **beneficial**
- kest_renewal_0 v9 (controller_approved) dims=['cohorts', 'voice', 'caller_id', 'schedule'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- nort_renewal_0 v8 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=-0.002 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 48,
  "decisions": {
    "approved": 42,
    "rejected": 6,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 6
  },
  "applied_via_approval": 42,
  "auto_applied": 9,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "nort_renewal_0": 2,
    "nort_kyc_1": 1,
    "nort_cancel_2": 1,
    "kest_renewal_0": 1,
    "kest_kyc_1": 1,
    "kest_cancel_2": 1,
    "arav_renewal_0": 1,
    "arav_kyc_1": 1,
    "arav_cancel_2": 1,
    "tide_renewal_0": 1,
    "tide_kyc_1": 1,
    "tide_cancel_2": 1
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
  "nort_renewal_0:welcome_message=W3": {
    "3": 0.025,
    "4": 0.0
  },
  "kest_renewal_0:welcome_message=W3": {
    "3": 0.65,
    "4": 0.65
  },
  "arav_renewal_0:welcome_message=W3": {
    "3": 0.613,
    "4": 0.62
  },
  "tide_renewal_0:welcome_message=W3": {
    "3": 0.652,
    "4": 0.634
  }
}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0
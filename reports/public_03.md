# Grade report — public_03_load

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.363 | +7.7% | 0.260 | +6.8% | 0.496 | -0.1% | 3% | 453 (409) |
| arav_kyc_1 | 0.466 | +29.9% | 0.270 | +25.5% | 0.595 | -0.9% | 0% | 429 (352) |
| arav_renewal_0 | 0.435 | +7.3% | 0.276 | +4.4% | 0.559 | +2.1% | 14% | 420 (408) |
| kest_cancel_2 | 0.356 | +5.7% | 0.256 | +5.6% | 0.496 | -0.6% | 1% | 430 (418) |
| kest_kyc_1 | 0.458 | +28.7% | 0.267 | +24.5% | 0.593 | -0.7% | 0% | 437 (370) |
| kest_renewal_0 | 0.452 | +12.4% | 0.281 | +6.1% | 0.570 | +4.7% | 23% | 441 (403) |
| nort_cancel_2 | 0.364 | +7.3% | 0.259 | +6.3% | 0.499 | +0.1% | 2% | 415 (368) |
| nort_kyc_1 | 0.458 | +28.8% | 0.268 | +24.5% | 0.591 | -0.7% | 0% | 449 (318) |
| nort_renewal_0 | 0.443 | +9.4% | 0.281 | +6.3% | 0.560 | +2.3% | 16% | 460 (419) |
| tide_cancel_2 | 0.365 | +6.3% | 0.259 | +6.0% | 0.502 | +0.1% | 5% | 409 (401) |
| tide_kyc_1 | 0.423 | +18.7% | 0.246 | +14.5% | 0.601 | +0.4% | 0% | 384 (376) |
| tide_renewal_0 | 0.447 | +10.5% | 0.282 | +6.6% | 0.564 | +3.2% | 19% | 439 (425) |
| ALL | 0.419 | +14.3% | 0.267 | +10.8% | 0.553 | +1.3% | 8% | 5166 (4667) |

## Changes applied by the controller

34 applied — beneficial: 25, harmful: 4, neutral: 5

- tide_cancel_2 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=-0.000 didΔ=+0.026 → **beneficial**
- nort_cancel_2 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=-0.000 didΔ=+0.028 → **beneficial**
- arav_cancel_2 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=-0.000 didΔ=+0.028 → **beneficial**
- kest_kyc_1 v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.225 → **beneficial**
- tide_renewal_0 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.026 didΔ=-0.044 → **harmful**
- nort_renewal_0 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.026 didΔ=-0.044 → **harmful**
- tide_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.095 → **beneficial**
- nort_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.095 → **beneficial**
- kest_renewal_0 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.025 didΔ=-0.042 → **harmful**
- kest_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.089 → **beneficial**
- nort_kyc_1 v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.249 → **beneficial**
- tide_kyc_1 v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.198 → **beneficial**
- kest_cancel_2 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=-0.000 didΔ=+0.027 → **beneficial**
- arav_renewal_0 v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.025 didΔ=-0.042 → **harmful**
- arav_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.089 → **beneficial**
- arav_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.640 → **beneficial**
- nort_cancel_2 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.015 → **neutral**
- arav_cancel_2 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.015 → **neutral**
- tide_cancel_2 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.015 → **neutral**
- kest_renewal_0 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.058 didΔ=+0.000 → **beneficial**
- kest_kyc_1 v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.144 → **beneficial**
- nort_renewal_0 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.027 didΔ=+0.000 → **beneficial**
- tide_renewal_0 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.039 didΔ=+0.000 → **beneficial**
- nort_kyc_1 v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.155 → **beneficial**
- kest_cancel_2 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.015 → **neutral**
- tide_cancel_2 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.023 didΔ=+0.000 → **beneficial**
- tide_kyc_1 v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.146 → **beneficial**
- arav_renewal_0 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.039 didΔ=+0.000 → **beneficial**
- nort_cancel_2 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.027 didΔ=+0.000 → **beneficial**
- kest_renewal_0 v5 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.019 didΔ=+0.000 → **beneficial**
- nort_renewal_0 v5 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.012 didΔ=+0.000 → **beneficial**
- kest_cancel_2 v4 (controller_approved) dims=['cohorts', 'voice', 'caller_id', 'schedule'] engageΔ=+0.009 didΔ=+0.000 → **neutral**
- arav_cancel_2 v4 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.030 didΔ=+0.000 → **beneficial**
- tide_renewal_0 v5 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.029 didΔ=+0.000 → **beneficial**

## Governance

```
{
  "approval_requests": 33,
  "decisions": {
    "approved": 26,
    "rejected": 6,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 6
  },
  "applied_via_approval": 26,
  "auto_applied": 8,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "nort_renewal_0": 1,
    "nort_kyc_1": 1,
    "nort_cancel_2": 1,
    "kest_renewal_0": 1,
    "kest_kyc_1": 1,
    "kest_cancel_2": 1,
    "arav_renewal_0": 1,
    "arav_kyc_1": 2,
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
    "3": 0.305,
    "4": 0.46
  },
  "kest_renewal_0:welcome_message=W3": {
    "3": 0.524,
    "4": 0.559
  },
  "tide_renewal_0:welcome_message=W3": {
    "3": 0.302,
    "4": 0.56
  },
  "arav_renewal_0:welcome_message=W3": {
    "4": 0.409
  }
}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0
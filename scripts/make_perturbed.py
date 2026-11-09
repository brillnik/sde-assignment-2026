"""Generate perturbed scenarios (same schema, different truth/incidents/policy) to check the controller is not fitted to
the public truth. These files are test fixtures for *us*; the controller never reads them."""
import copy
import yaml

base = yaml.safe_load(open("scenarios/public_02_incidents.yaml"))
dev = yaml.safe_load(open("scenarios/public_01_dev.yaml"))

def wfs(sc):
    return {w["id"]: w for t in sc["tenants"] for w in t["workflows"]}

# A: different effects, other DID flagged earlier, bad prompt (P4) on nw_renewal, decaying W2
a = copy.deepcopy(base); a["name"] = "pert_A"; a["seed"] = 303
a["effects"] = [
    {"workflow": "nw_renewal", "dim": "voice", "value": "V4", "mult": 1.2, "where": {"age_band": ["18-30"]}},
    {"workflow": "nw_renewal", "dim": "voice", "value": "V2", "mult": 0.9},
    {"workflow": "nw_renewal", "dim": "welcome_message", "value": "W2", "mult": 1.16, "decay": {"after_exposure_days": 3, "to_mult": 0.92, "over_days": 2}},
    {"workflow": "nw_kyc", "dim": "welcome_message", "value": "W2", "mult": 1.1, "where": {"lang": ["hi"]}},
    {"workflow": "ks_cancel", "dim": "voice", "value": "V2", "mult": 1.14, "where": {"city_tier": ["1", "2"]}},
    {"workflow": "ks_cancel", "dim": "welcome_message", "value": "W3", "mult": 0.88},
]
a["incidents"] = [
    {"type": "did_flagged", "workflow": "nw_renewal", "did": "D1", "at": "D1 14:00", "base_health": 0.4},
    {"type": "supervisor_edit", "workflow": "nw_renewal", "at": "D4 10:30", "patch": {"prompt_version": "P4"}, "note": "persuasive prompt"},
    {"type": "did_flagged", "workflow": "ks_cancel", "did": "D1", "at": "D6 12:00", "base_health": 0.5},
]

# B: NULL world - no variant truly works. Any promoted winner is a false winner.
b = copy.deepcopy(dev); b["name"] = "pert_B_null"; b["seed"] = 404; b["days"] = 10
b["effects"] = []; b["incidents"] = []

# C: tighter policy + two caller-ID incidents + supervisor schedule edit + approver hours shifted
c = copy.deepcopy(base); c["name"] = "pert_C"; c["seed"] = 505
for w in wfs(c).values():
    g = w["governance"]
    g["approver_hours"] = [11, 17]; g["approver_latency_minutes"] = [60, 240]; g["proposal_ttl_hours"] = 12
    g["max_requests_per_24h"] = 2; g["base_reject_rate"] = 0.25
c["effects"] = [
    {"workflow": "nw_renewal", "dim": "voice", "value": "V3", "mult": 1.18, "where": {"lang": ["ta", "hi"]}},
    {"workflow": "nw_kyc", "dim": "voice", "value": "V2", "mult": 1.12},
    {"workflow": "ks_cancel", "dim": "welcome_message", "value": "W2", "mult": 1.1, "where": {"age_band": ["60+"]}},
]
c["incidents"] = [
    {"type": "did_flagged", "workflow": "ks_cancel", "did": "D1", "at": "D1 11:00", "base_health": 0.35},
    {"type": "did_flagged", "workflow": "nw_renewal", "did": "D2", "at": "D3 15:00", "base_health": 0.4},
    {"type": "supervisor_edit", "workflow": "nw_renewal", "at": "D4 12:00",
     "patch": {"schedule": {"hour_weights": {"default": {str(h): 1 for h in range(9, 21)}}}}, "note": "supervisor resets schedule"},
    {"type": "supervisor_edit", "workflow": "ks_cancel", "at": "D5 11:30", "patch": {"prompt_version": "P2"}, "note": "bad script"},
]
for sc in (a, b, c):
    yaml.safe_dump(sc, open(f"scenarios/perturbed/{sc['name']}.yaml", "w"), sort_keys=False)
print("written")

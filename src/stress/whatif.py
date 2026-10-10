from src.riskengine.impact import cluster_components, cluster_impact

MAX_LENGTH = 300
WHAT_IF_BASELINE_MENTIONS = 10.0
OUTLET_RANGE = (1, 30)
VOLUME_OPTIONS = [1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0]
EXAMPLES = [
    "Russia launches full-scale invasion of Ukraine as explosions heard in Kyiv",
    "Fitch cuts Russia's rating further into junk, says debt default is imminent",
    "Federal Reserve raises interest rates by 50 basis points to fight inflation",
    "Brent crude surges above $130 a barrel as US weighs ban on Russian oil",
    "Apple unveils new iPhone SE at spring event",
    "Antitrust regulators open probe into Google ad business",
]


def what_if_event(result: dict, outlets: int, volume_multiple: float) -> dict:
    signal = result["signal"]
    baseline = WHAT_IF_BASELINE_MENTIONS
    components = cluster_components([signal["impact"]["score"]], outlets, int(round(baseline * volume_multiple)), baseline)
    event = dict(result["event"])
    event.update({
        "impact_components": components,
        "impact": cluster_impact(components),
        "n_outlets": outlets,
        "warmup": False,
        "representative_signal_ids": [signal["signal_id"]],
    })
    return event

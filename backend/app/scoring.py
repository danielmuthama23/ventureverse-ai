"""Evidence weighting, city scores and the critic's weakness list.

Two views of the same evidence:
  player: each claim weighted by the label the founder gave it (face value
          when unreviewed), minus anything the founder challenged away.
  truth:  each claim weighted by what the evidence really supports.
"""
from __future__ import annotations

from . import data_loader

WEIGHT = {"verified": 1.0, "estimate": 0.6, "hypothesis": 0.25}


def _weight(claim: dict, labels: dict[str, str], mode: str) -> float:
    if mode == "truth":
        return WEIGHT[claim["truth"]]
    lab = labels.get(claim["id"])
    return WEIGHT[lab] if lab else claim["source_confidence"]  # unreviewed: taken at face value


def city_scores(found: list[str], labels: dict[str, str], excluded: set[str], mode: str = "player") -> dict[str, int]:
    by_id = data_loader.claim_by_id()
    raw = {c: 0.0 for c in data_loader.venture()["cities"]}
    for cid in found:
        c = by_id[cid]
        if not c["city"] or (mode != "truth" and cid in excluded):
            continue
        raw[c["city"]] += c["signal"] * _weight(c, labels, mode)
    return {k: max(4, min(98, round(38 + v * 7))) for k, v in raw.items()}


def top_city(scores: dict[str, int]) -> str:
    return max(scores.items(), key=lambda kv: kv[1])[0]


def hypothesis_share(found: list[str], city: str) -> float:
    by_id = data_loader.claim_by_id()
    pos = hyp = 0
    for cid in found:
        c = by_id[cid]
        if c["city"] == city and c["signal"] > 0:
            pos += c["signal"]
            if c["truth"] == "hypothesis":
                hyp += c["signal"]
    return hyp / pos if pos else 0.0


def weaknesses(found: list[str], city: str) -> list[dict]:
    """Candidate weaknesses; `real` is computed from the data and never sent to the client."""
    by_id = data_loader.claim_by_id()
    ids = [i for i in found if by_id[i]["city"] == city]
    has_interview = any(by_id[i]["interview"] for i in ids)
    comp_negative = any(by_id[i]["agent"] == "competitor" and by_id[i]["signal"] < 0 for i in ids)
    unverified = sum(1 for i in ids if by_id[i]["truth"] != "verified")
    return [
        {"text": f"More than a third of the positive evidence for {city} is hypothesis.", "real": hypothesis_share(found, city) > 0.34},
        {"text": f"No direct customer interviews cover {city}.", "real": not has_interview},
        {"text": f"Competitors already have a strong position in {city}.", "real": comp_negative},
        {"text": f"Most evidence for {city} is unverified.", "real": unverified > len(ids) / 2},
        {"text": "The market data is out of date.", "real": False},
    ]

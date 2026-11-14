"""Offline narrative used when no local LLM is reachable. Facts only: it
restates retrieved passages and withholds verified/estimate/hypothesis labels."""
from __future__ import annotations


def offline_summary(agent: dict, idea_profile: dict, claims: list[dict], extra: str = "") -> str:
    s = ""
    if claims:
        cols = sorted({c["collection"] for c in claims})
        s += f'{agent["name"]} retrieved {len(claims)} passages from {", ".join(cols)}.\n'
        s += f'Closest match: "{claims[0]["claim"]}" ({claims[0]["source"]}).\n'
    if agent["id"] == "founder":
        p = idea_profile
        s += f'Idea profile: sector {p["sector"]}, geography {p["geo"]}, model {p["model"]}.\n'
        if not p["matched"]:
            s += "Note: the demo corpus covers Kenyan agricultural marketplaces, so other ideas will fit poorly.\n"
    s += extra
    s += "Nothing runs until you decide." if agent["id"] == "critic" else "Status labels are withheld. Review each claim."
    return s

from app import data_loader, scoring


def all_ids():
    return [c["id"] for c in data_loader.claims() if not c["extra"]]


def test_scores_bounded_and_complete():
    sc = scoring.city_scores(all_ids(), {}, set())
    assert set(sc) == set(data_loader.venture()["cities"])
    assert all(4 <= v <= 98 for v in sc.values())


def test_face_value_overrates_nairobi_and_truth_prefers_nakuru():
    ids = all_ids()
    assert scoring.top_city(scoring.city_scores(ids, {}, set())) == "Nairobi"
    assert scoring.top_city(scoring.city_scores(ids, {}, set(), "truth")) == "Nakuru"


def test_labelling_hypotheses_moves_the_recommendation():
    ids = all_ids()
    labels = {c["id"]: c["truth"] for c in data_loader.claims() if c["id"] in ids}
    assert scoring.top_city(scoring.city_scores(ids, labels, set())) == "Nakuru"


def test_weaknesses_hide_nothing_but_mark_decoy():
    w = scoring.weaknesses(all_ids(), "Nairobi")
    assert len(w) == 5 and w[-1]["real"] is False and w[0]["real"] is True

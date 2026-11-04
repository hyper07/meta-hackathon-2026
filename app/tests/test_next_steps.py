"""
Notice's next steps: similar public cases (real ones, with their official answer), verified places to turn,
her own Title IX or HR contact, and an export about one person. Legal information, never legal advice.
"""
import json

from fastapi.testclient import TestClient

from scenarios.training_cases import CASES
from watchme import main, notice
from watchme.config import settings


def record(types, setting="school", match="some", who="Prof. R"):
    return {"id": "r1", "setting": setting, "who": who,
            "review": {"match": match, "moments": [{"quote": "q", "type": t, "why": ""} for t in types]}}


def test_similar_cases_are_real_public_cases_with_their_official_answer():
    found = notice.similar_cases(record(["conditions", "isolation"]))
    assert 1 <= len(found) <= 3
    real = {c["id"]: c for c in CASES}
    for case in found:
        source = real[case["id"]]                                  # never a case that isn't in the set
        assert case["official"] == source["official"] and case["url"] == source["url"]
        assert set(case["shared"]) <= {notice.TYPES[t][0] for t in source["expect"]}
    # the cases sharing the most kinds of conduct come first
    shared = [len(c["shared"]) for c in found]
    assert shared == sorted(shared, reverse=True)


def test_nothing_is_suggested_when_the_review_found_nothing():
    assert notice.similar_cases(record([], match="none")) == []
    assert notice.similar_cases({"id": "r2", "review": None}) == []


def test_cases_from_the_rescinded_eeoc_guidance_say_so():
    every = [notice.similar_cases(record([t]), n=40) for t in notice.TYPES]
    flagged = [c for cases in every for c in cases if "Enforcement Guidance on Harassment in the Workplace" in c["source"]]
    assert flagged and all("rescinded in January 2026" in c["note"] for c in flagged)


def test_the_app_ships_the_same_cases_as_the_test_set():
    assert json.loads(json.dumps(notice.PUBLIC_CASES)) == [
        {k: c[k] for k in ("id", "setting", "expect", "official", "source", "url")} for c in CASES]


def test_the_numbers_are_the_verified_ones():
    text = json.dumps(notice.RESOURCES)
    for number in ("1-800-669-4000",          # EEOC (eeoc.gov/contact-eeoc)
                   "1-800-421-3481",          # Department of Education, Office for Civil Rights
                   "800-656-4673",            # RAINN
                   "1-800-799-7233", "88788",  # National Domestic Violence Hotline (thehotline.org)
                   "844-878-2274"):           # Cyber Civil Rights Initiative helpline
        assert number in text, number


def test_an_export_about_one_person_leaves_everyone_else_out(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    notice.add("He said I'd get the shifts if I came for a drink.", None, setting="work", who="Manager D",
               where="", when="2026-10-27T09:40", source="debrief")
    notice.add("He kept asking me out after I said no.", None, setting="school", who="Prof. R",
               where="", when="2026-10-28T15:10", source="debrief")
    text = notice.export(notice.read(), who="prof. r")
    assert "Prof. R" in text and "kept asking me out" in text
    assert "Manager D" not in text and "shifts" not in text
    assert "1 entries" in text or "1 entry" in text


def test_her_title_ix_and_hr_contacts_come_back_with_the_notice_page(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "demo_mode", False)
    client = TestClient(main.app)
    r = client.post("/api/profile", json={"name": "Alex", "contacts": [],
                                          "help": {"title_ix": "titleix@school.edu", "hr": "Dana, hr@company.com"}})
    assert r.status_code == 200
    page = client.get("/api/notice").json()
    assert page["help"] == {"title_ix": "titleix@school.edu", "hr": "Dana, hr@company.com"}
    assert "similar" in page


def test_a_case_about_a_different_basis_is_never_shown():
    real = {c["id"]: c for c in CASES}
    for types in (["appearance"], ["advances", "touching"], ["conditions", "isolation"], ["sexual_comments"]):
        for case in notice.similar_cases(record(types), n=40):
            other = set(real[case["id"]]["expect"]) & {"race_origin", "religion", "age", "disability", "lgbtq", "pregnancy"}
            assert not other, (types, case["id"], other)   # sexual harassment never gets a race or religion case


def test_a_save_without_her_contacts_keeps_them(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "demo_mode", False)
    client = TestClient(main.app)
    client.post("/api/profile", json={"name": "Alex", "contacts": [], "help": {"title_ix": "titleix@school.edu", "hr": ""}})
    client.post("/api/profile", json={"name": "Alex", "contacts": []})          # an app build that doesn't send them
    assert client.get("/api/notice").json()["help"]["title_ix"] == "titleix@school.edu"

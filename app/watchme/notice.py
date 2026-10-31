"""
Notice: help the owner notice whether something at school, at work or online
matched what harassment policies describe. Not an emergency mode: no check-ins,
no alerts.

    debrief (her own words, typed, spoken or pasted messages) ─┐
                                                                ├─▶ review() ── Muse Spark: moments, exact quotes, a type each
    a recorded session's transcript ────────────────────────────┘        │
                                                                          ▼
                                        the notice book (hash-chained, like a session log)
                                                                          ▼
                                        patterns() ── per person she named, counted by code, not by the model

The types follow the EEOC's description of harassment (unwelcome conduct based on
sex, race, color, religion, national origin, age 40+, disability or genetic
information; sex includes sexual orientation, gender identity and pregnancy),
plus bullying, threats and online abuse, which school and workplace policies
commonly cover. Each carries its source, so the app points at the definitions
instead of making its own. The EEOC says its pages are under review (2026), and
it rescinded its 2024 harassment guidance in January 2026; the law itself has
not changed. The app never says "you were harassed": it says which words match
which description, and that only she decides what it was.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from collections import Counter, defaultdict

from . import muse, store
from .config import settings

SOURCES = {
    "eeoc": {"name": "EEOC: Sexual harassment", "url": "https://www.eeoc.gov/sexual-harassment"},
    "eeoc_harassment": {"name": "EEOC: Harassment", "url": "https://www.eeoc.gov/harassment"},
    "eeoc_retaliation": {"name": "EEOC: Retaliation", "url": "https://www.eeoc.gov/retaliation"},
    "eeoc_race": {"name": "EEOC: Race and color", "url": "https://www.eeoc.gov/racecolor-discrimination"},
    "eeoc_origin": {"name": "EEOC: National origin", "url": "https://www.eeoc.gov/national-origin-discrimination"},
    "eeoc_religion": {"name": "EEOC: Religion", "url": "https://www.eeoc.gov/religious-discrimination"},
    "eeoc_age": {"name": "EEOC: Age", "url": "https://www.eeoc.gov/age-discrimination"},
    "eeoc_disability": {"name": "EEOC: Disability", "url": "https://www.eeoc.gov/eeoc-disability-related-resources"},
    "eeoc_sex": {"name": "EEOC: Sex-based discrimination", "url": "https://www.eeoc.gov/sex-based-discrimination"},
    "eeoc_pregnancy": {"name": "EEOC: Pregnancy", "url": "https://www.eeoc.gov/pregnancy-discrimination"},
    "ftc_takedown": {"name": "FTC: intimate images shared without consent",
                     "url": "https://consumer.ftc.gov/consumer-alerts/2026/09/was-your-intimate-image-shared-online-without-your-consent-heres-what-do"},
    "ocr": {"name": "U.S. Department of Education, Office for Civil Rights: how complaints work",
            "url": "https://www.ed.gov/laws-and-policy/civil-rights-laws/ensuring-equal-access/how-eds-office-civil-rights-resolves-complaints"},
}

# Groups, in the order the screen shows them.
GROUPS = {"sexual": "Sexual harassment", "identity": "Because of who you are", "conduct": "Bullying, threats and pressure",
          "online": "Online"}

# key: (label, what it means in plain words, source key or None when it is not a legal category, group)
TYPES = {
    "sexual_comments": ("Sexual comments or jokes", "Remarks, jokes or questions of a sexual nature you didn't welcome. "
                        "The EEOC lists \"verbal or physical harassment of a sexual nature\".", "eeoc", "sexual"),
    "appearance": ("Comments about your body or looks", "Remarks about your body, clothes or looks, in a sexual way or "
                   "because of your sex.", "eeoc", "sexual"),
    "advances": ("Unwanted advances", "Asking you out, for a date or for sex when you didn't welcome it. The EEOC lists "
                 "\"unwelcome sexual advances, requests for sexual favors\".", "eeoc", "sexual"),
    "touching": ("Unwanted touching", "Touching, blocking your way or standing too close when you didn't want it.", "eeoc",
                 "sexual"),
    "after_no": ("Kept going after you said no", "It continued after you refused, changed the subject or left. "
                 "\"Unwelcome\" is the heart of every definition.", "eeoc_harassment", "sexual"),
    "sex_based": ("Put-downs because of your sex", "Insults or remarks about women (or men) in general. The EEOC: harassment "
                  "\"does not have to be of a sexual nature\" and \"can include offensive remarks about a person's sex\".",
                  "eeoc", "identity"),
    "race_origin": ("Race, color, ethnicity or where you're from", "Slurs, jokes, mockery of your accent, name or culture, "
                    "or remarks about your race, skin color, ethnicity, national origin or immigration status.",
                    "eeoc_race", "identity"),
    "religion": ("Your religion", "Mockery of your faith, dress or practices, slurs, or pressure to give up or adopt beliefs.",
                 "eeoc_religion", "identity"),
    "age": ("Your age", "Remarks or jokes about being old, slow or out of touch, aimed at someone 40 or older. Federal law "
            "protects age from 40.", "eeoc_age", "identity"),
    "disability": ("A disability or health condition", "Mockery of a disability, a medical condition, an accommodation "
                   "or a mental-health condition.", "eeoc_disability", "identity"),
    "lgbtq": ("Sexual orientation or gender identity", "Slurs, jokes or remarks about being gay, lesbian, bisexual or "
              "transgender, outing someone, or repeatedly using the wrong name or pronouns on purpose. The EEOC treats "
              "these as harassment because of sex.", "eeoc_sex", "identity"),
    "pregnancy": ("Pregnancy or caregiving", "Remarks about being pregnant, breastfeeding, or having children to care "
                  "for, such as doubting your commitment because of it.", "eeoc_pregnancy", "identity"),
    "conditions": ("Strings attached", "A grade, job, shift, reference or opportunity tied to going along with it. The EEOC "
                   "counts harassment that \"results in an adverse employment decision\".", "eeoc", "conduct"),
    "retaliation": ("Punished for objecting", "Being treated worse after you complained or said no. The EEOC calls this "
                    "retaliation, and complaining to a manager about harassment is protected.", "eeoc_retaliation", "conduct"),
    "threats": ("Threats or intimidation", "Threats of harm, intimidation, or physical aggression. The EEOC lists "
                "\"physical assaults or threats\" and intimidation.", "eeoc_harassment", "conduct"),
    "bullying": ("Bullying or belittling", "Repeated insults, humiliation, ridicule or being made to doubt yourself. Federal "
                 "law covers it only when it's tied to who you are (above), but many school codes of conduct and "
                 "workplace policies prohibit it either way.", None, "conduct"),
    "isolation": ("Getting you alone", "Pressure to meet alone, after hours or off site. Not a legal category on its own, "
                  "but a common part of the pattern.", None, "conduct"),
    "online": ("Online abuse", "Unwanted messages that keep coming, posts or comments aimed at you, impersonation, or "
               "sharing your photos or personal information. Sharing intimate images without consent is a federal "
               "crime, and platforms must remove them within 48 hours of a request.", "ftc_takedown", "online"),
}

FREQUENCY = ("The EEOC: \"petty slights, annoyances, and isolated incidents (unless extremely serious) will not rise to "
             "the level of illegality\", but harassment is illegal \"when it is so frequent or severe that it creates a "
             "hostile or offensive work environment\". That's why a dated record of each time matters.")

RESOURCES = {
    "school": [
        "Your school's Title IX coordinator for sex-based harassment: every school that receives federal funding has one, "
        "and you can ask about supportive measures without filing anything. For race, national origin or disability, ask "
        "the dean of students or the disability services office.",
        "The Department of Education's Office for Civil Rights generally takes complaints within 180 days of the last incident.",
    ],
    "work": [
        "HR, or a manager outside the person's reporting line. Complaining about harassment is protected from retaliation.",
        "The EEOC: in general, 180 days to file a charge (longer where state law extends it).",
    ],
    "online": [
        "Report it on the platform and keep screenshots with the date and the account name before blocking.",
        "Intimate images shared without consent: platforms must remove them within 48 hours of your request; if they "
        "don't, report it at TakeItDown.ftc.gov. StopNCII.org can help block copies on participating platforms.",
    ],
    "any": ["RAINN, free and confidential, 24/7: 800-656-4673, or chat at rainn.org (for sexual harassment and assault)."],
}

DISCLAIMER = "Only you decide what this was. This explains what the words match; it isn't legal advice."

PROMPT = f"""You help someone notice whether what happened to them at school, at work or online matches
common descriptions of harassment. You get their own account (first person), messages they pasted, or a
transcript of a conversation they recorded, where [owner] is them and [other] is anyone else.
Speech-to-text makes mistakes.

Types, use only these keys:
{chr(10).join(f'- {k}: {label}. {plain}' for k, (label, plain, _, _) in TYPES.items())}

Rules:
- Find the moments that match a type. For each, copy the exact words from the text. Never quote words
  that are not in the text. One moment can match more than one type: list it once per type.
- Describe the words, not the person. Never say they were harassed or that anyone is guilty. No legal
  advice, no diagnosis.
- Not matches: jokes or flirting both people clearly welcome; ordinary feedback on work or grades, even
  blunt; a fair decision explained on its merits; a manager raising real performance or conduct issues;
  respectful questions about someone's culture, faith or accommodation; one polite invitation that was
  dropped after a no; talk about other people's experiences.
- match: "none" if nothing matches, "some" if parts match or it is unclear whether it was welcome,
  "clear" if the words plainly match a type.
- summary: two short, calm sentences in plain words, speaking to them as "you".

Answer with JSON only:
{{"match": "none|some|clear", "moments": [{{"quote": "...", "type": "<key>", "why": "one short sentence"}}], "summary": "..."}}"""


async def review(text: str, setting: str = "") -> dict | None:
    """None when Muse Spark is not configured; {"error": ...} when the call failed."""
    if not settings.muse_ready or not text.strip():
        return None
    try:
        answer = muse._first_json(await muse._chat(PROMPT, f"Setting: {setting or 'not given'}\n\n{text}",
                                                   max_tokens=4000, timeout=60, model=settings.reviewer_model))
    except Exception as error:
        return {"error": f"{type(error).__name__}: {error}", "retry": muse.retryable(error)}
    plain = re.sub(r"^\[\w+\]\s*", "", text, flags=re.MULTILINE).lower()
    moments = []
    for m in answer.get("moments") or []:
        quote = str(m.get("quote") or "").strip()
        # A quote the model can't point to in the text is dropped, as in the Analyst.
        if m.get("type") in TYPES and quote and quote.lower() in plain:
            moments.append({"quote": quote, "type": m["type"], "why": str(m.get("why") or "")[:240]})
    match = answer.get("match") if answer.get("match") in ("none", "some", "clear") else "some"
    if not moments:
        match = "none"
    return {"match": match, "moments": moments, "summary": str(answer.get("summary") or "")[:500],
            "engine": settings.reviewer_model or settings.meta_model}


# ── the notice book ──────────────────────────────────────────────────────────

def book() -> store.EvidenceLog:
    return store.EvidenceLog(folder=settings.data_dir / "notice")


def add(text: str, review_: dict | None, *, setting: str, who: str, where: str, when: str,
        source: str, session: str | None = None, pending: bool = False) -> dict:
    """pending: the review couldn't run (no network); set_review() adds it later."""
    return book().append("record", id=uuid.uuid4().hex[:10], when=when or time.strftime("%Y-%m-%dT%H:%M"),
                         setting=setting, who=who.strip()[:60], where=where.strip()[:80], source=source,
                         session=session, text=text[:6000], review=review_, pending=pending)


def label(record_id: str, *, setting: str, who: str, where: str) -> dict:
    """Who, where and the setting, added later (a live session has none). A new line; the record itself is never edited."""
    return book().append("label", id=record_id, setting=setting, who=who.strip()[:60], where=where.strip()[:80])


def set_review(record_id: str, review_: dict) -> dict:
    """A review done later, once the network was back. A new line; the record itself is never edited."""
    return book().append("review", id=record_id, review=review_)


def read() -> dict:
    path = book().path
    lines = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    records: dict[str, dict] = {}
    for line in lines:
        if line["kind"] == "record":
            records[line["id"]] = dict(line)
        elif line["kind"] == "label" and line["id"] in records:
            records[line["id"]].update({k: line[k] for k in ("setting", "who", "where") if line.get(k)}, labelled=True)
        elif line["kind"] == "review" and line["id"] in records:
            records[line["id"]].update(review=line["review"], pending=False, reviewed_at=line.get("at"))
    return {"records": list(records.values()), "chain": store.verify(lines)}


def patterns(records: list[dict]) -> list[dict]:
    """Per person she named: how often, over how long, and which types. Counted here, not by the model."""
    people: dict[str, list[dict]] = defaultdict(list)
    names: dict[str, str] = {}
    for r in records:
        review_ = r.get("review") or {}
        if review_.get("match") not in ("some", "clear"):
            continue
        key = r.get("who", "").strip().lower() or "(not named)"
        names.setdefault(key, r.get("who", "").strip() or "Not named")
        people[key].append(r)
    out = []
    for key, rs in people.items():
        dates = sorted(r["when"][:10] for r in rs)
        types = Counter(t for r in rs for t in {m["type"] for m in r["review"]["moments"]})   # occasions, not quotes
        out.append({
            "who": names[key], "times": len(rs), "first": dates[0], "last": dates[-1],
            "types": [{"type": t, "label": TYPES[t][0], "count": n} for t, n in types.most_common()],
            "repeated": len(rs) >= 2,
        })
    return sorted(out, key=lambda p: (-p["times"], p["who"]))


def export(data: dict) -> str:
    """A dated, plain-text record she can keep, print or hand to a Title IX office or HR."""
    lines = ["# Notice record", "",
             f"Exported {time.strftime('%Y-%m-%d %H:%M')}. {len(data['records'])} entries.",
             f"Integrity: {'unaltered' if data['chain']['ok'] else 'ALTERED at line ' + str(data['chain'].get('broken_at'))}"
             + (f", hash chain head {data['chain']['head']}" if data['chain'].get('head') else "") + ".", ""]
    for r in data["records"]:
        review_ = r.get("review") or {}
        lines += [f"## {r['when'].replace('T', ' ')} · {r.get('who') or 'not named'}"
                  + (f" · {r['where']}" if r.get("where") else ""), "",
                  f"Setting: {r.get('setting') or 'not given'}. Written as: "
                  f"{'my own account' if r['source'] == 'debrief' else 'transcript of session ' + str(r.get('session'))}.", "",
                  "> " + r["text"].replace("\n", "\n> "), ""]
        for m in review_.get("moments") or []:
            lines.append(f"- \"{m['quote']}\": {TYPES[m['type']][0]}. {m['why']}")
        if review_.get("summary"):
            lines += ["", review_["summary"]]
        lines += ["", f"Record hash: {r['hash']}", ""]
    lines += ["---", DISCLAIMER, FREQUENCY]
    return "\n".join(lines) + "\n"

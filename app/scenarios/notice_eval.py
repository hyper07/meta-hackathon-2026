"""
Run every Notice test account through notice.review() and score it.

    uv run python -m scenarios.notice_eval              # our own 16 accounts (notice_cases.py)
    uv run python -m scenarios.notice_eval --training   # public training examples (training_cases.py)

A case that should match counts as found when the review says "some" or "clear"
and names an expected type among its moments. A harmless case should come back
"none". Results go to results/<stamp>-notice[-training].{json,md}.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from watchme import notice
from watchme.config import settings


RESULTS = Path(__file__).resolve().parent / "results"


def _expected(case: dict) -> list[str]:
    e = case["expect"]
    return [e] if isinstance(e, str) else list(e or [])


async def main(args: list[str]) -> None:
    training = "--training" in args
    if training:
        from .training_cases import CASES
    else:
        from .notice_cases import CASES
    if not settings.muse_ready:
        raise SystemExit("Notice needs Muse Spark: set MODEL_API_KEY (or META_API_KEY).")
    rows = []
    for case in CASES:
        t0 = time.time()
        review = await notice.review(case["text"], case["setting"]) or {}
        types = sorted({m["type"] for m in review.get("moments", [])})
        match = review.get("match", "error")
        expect = _expected(case)
        if expect:
            right = match in ("some", "clear") and bool(set(expect) & set(types))
        else:
            right = match == "none"
        rows.append({"id": case["id"], "setting": case.get("setting"), "expect": expect, "match": match, "types": types,
                     "right": right, "all_named": set(expect) <= set(types) if expect else None,
                     "seconds": round(time.time() - t0, 1), "error": review.get("error"), "summary": review.get("summary"),
                     "official": case.get("official"), "source": case.get("source")})
        print(f"{case['id']:28s} expect={','.join(expect) or 'none':24s} match={match:6s} {'ok' if right else 'WRONG'} {types}")

    harm = [r for r in rows if r["expect"]]
    ok = [r for r in rows if not r["expect"]]
    seconds = sorted(r["seconds"] for r in rows)
    lines = [
        f"## Notice review{' on public training examples' if training else ''}: {settings.reviewer_model or settings.meta_model}", "",
        f"- Should match, found with an expected type: **{sum(r['right'] for r in harm)} of {len(harm)}** "
        f"(every expected type named: {sum(bool(r['all_named']) for r in harm)} of {len(harm)})",
        f"- Should not match, came back \"none\": **{sum(r['right'] for r in ok)} of {len(ok)}**",
        f"- Seconds per review: median {seconds[len(seconds) // 2]}, worst {seconds[-1]}", "",
        "| case | setting | expected | match | types named | right |", "|---|---|---|---|---|---|",
        *[f"| {r['id']} | {r['setting'] or ''} | {', '.join(r['expect']) or 'none'} | {r['match']} | {', '.join(r['types']) or '–'} "
          f"| {'yes' if r['right'] else '✗'} |" for r in rows],
    ]
    report = "\n".join(lines)
    RESULTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M")
    stamp += "-notice" + ("-training" if training else "")
    (RESULTS / f"{stamp}.json").write_text(json.dumps(rows, indent=2))
    (RESULTS / f"{stamp}.md").write_text(report + "\n")
    print("\n" + report)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))

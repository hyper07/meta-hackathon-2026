"""
Build (and optionally publish) the Watch Me safety scenes as a Hugging Face dataset.

    cd app && uv run --with huggingface_hub --with datasets python ../benchmarks/publish_dataset.py <out dir>            # build
    cd app && uv run --with huggingface_hub --with datasets python ../benchmarks/publish_dataset.py <out dir> --publish  # and upload

Needs the rendered scenes (app/scenarios/out/, see benchmarks/run.sh). Publishing reads HF_TOKEN from the
environment or .env and uploads to <your user>/watch-me-safety-scenes.

What goes in (one Parquet file per config, so every config loads the same way; the audio is embedded):
  data/scenes.parquet          22 scene recordings (16 kHz WAV) with the script line by line (role, voice, text,
                               start, end, where the harm starts), the label and the background
  data/enrollment.parquet      the owner's three enrollment lines, for voice-lock tests
  data/notice_public.parquet   40 public training cases with their official answer and source
  data/notice_ours.parquet     16 cases of our own
Watch Me's measured results on this set stay in the GitHub repo (app/scenarios/results/), linked from the card.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

from scenarios.notice_cases import CASES as OUR_CASES  # noqa: E402
from scenarios.training_cases import CASES as PUBLIC_CASES  # noqa: E402

OUT_SCENES = APP / "scenarios" / "out"
REPO_NAME = "watch-me-safety-scenes"
ENROLL_TEXT = "Watch me. This is my voice, and only I can turn this on or off."

CARD = """---
license: cc-by-4.0
language:
- en
pretty_name: Watch Me safety scenes
size_categories:
- n<1K
task_categories:
- audio-classification
- text-classification
tags:
- safety
- harassment
- domestic-violence
- personal-safety
- speech
- synthetic
- benchmark
configs:
- config_name: scenes
  data_files:
  - split: train
    path: data/scenes.parquet
- config_name: notice_public
  data_files:
  - split: train
    path: data/notice_public.parquet
- config_name: notice_ours
  data_files:
  - split: train
    path: data/notice_ours.parquet
- config_name: enrollment
  data_files:
  - split: train
    path: data/enrollment.parquet
---

# Watch Me safety scenes

A small benchmark for one question: **listening to a conversation around someone, should a safety assistant
ask her "Are you OK?"** It has spoken scenes with their scripts, labelled harmful or harmless, and written
accounts of harassment at school, work and online, labelled with what an official source concluded.

It is the test set of [Watch Me](https://github.com/hyper07/meta-hackathon-2026), a voice-locked safety
assistant built for the Meta Global AI Developer Hackathon 2026, published so other systems can be measured
the same way. Every voice is synthetic and every scene is fictional.

## What's in it

| Config | Rows | What |
|---|---|---|
| `scenes` | 22 | the scene's audio (16 kHz WAV), with its script line by line: who speaks (`owner` is the person being protected), the synthetic voice, the text, start and end in seconds, and `harm_starts` on the first harmful line. 11 harmful, 9 harmless hard cases, 2 school and work (Notice) |
| `enrollment` | 3 | the owner saying her enrollment line, for voice-lock (speaker verification) tests |
| `notice_public` | 40 | public anti-harassment training examples with an official answer (EEOC, New York State, StopBullying.gov), rewritten as first-person accounts; `expect` lists the kinds of conduct the source named, `official` its conclusion, with `source` and `url` |
| `notice_ours` | 16 | accounts written for Watch Me, 8 that should match and 8 that should not |

**Harmful scenes:** drink pressure then "I feel dizzy"; unwanted touching; "don't tell anyone, nobody will
believe you"; followed on the way home; others talking about her while she can't respond; quiet pressure on a
date; street harassment; a stranger saying "stop watching"; a rideshare driver going the wrong way; a former
partner's threat; drugging symptoms.

**Harmless hard cases:** banter ("stop it, that's hilarious"); flirting; a horror film retold ("I'll kill
you"); a crime report on TV; someone else's story retold; board-game trash talk; a gym trainer ("don't stop");
ordering food; walking home with a friend.

## How it was made

- **Voices:** [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (Apache-2.0), one voice per role; the
  owner is always `af_heart`. No real person's voice is used.
- **Backgrounds** are generated in code (Watch Me's `app/scenarios/build.py`): party (layered synthetic
  chatter, a beat and pink noise), bar, street (brown noise with passing cars), TV (a synthetic newsreader
  across the room) and quiet room tone.
- **Scripts** were written by the people who built Watch Me. The public Notice cases are paraphrased from
  official training material; their character names are left out.

## Results on this set

Watch Me, streamed through the real app in 4-second chunks ([result files](https://github.com/hyper07/meta-hackathon-2026/tree/main/app/scenarios/results)):

| What hears · what judges | Harmful asked | Harmless asked (needless) |
|---|---|---|
| The script word for word · Muse Spark Open (open weights) | 11 of 11 | 0 of 9 |
| The script word for word · hosted Muse Spark 1.3 + 1.1 | 11 of 11 | 0 of 9 |
| The script word for word · phrase list and fixed rules, no model | 11 of 11 | 2 of 9 |
| Whisper on the audio · Muse Spark Open | 8 of 11 (19 of 22 started) | 0 of 9 |
| Whisper on the audio · hosted Muse models | 9 of 11 (20 of 22 started) | 0 of 9 |

Notice reviewer on `notice_public`: Muse Wonder 1.0 40 of 40, Muse Spark Open 38 of 40.

## Limits

- **Small and synthetic.** 22 scenes and 56 cases, written by the system's own builders, with synthetic
  voices. Use it to compare versions and systems, not as a claim about real-world accuracy.
- **English, US-centred.** The official sources are US federal and New York State material.
- **Rescinded guidance.** 11 public cases come from the EEOC's 2024 harassment guidance, which the EEOC
  rescinded in January 2026; they are used as realistic scenarios with a stated conclusion, not as current law.
- **Not for surveillance.** The scenes model someone who switched an assistant on for herself. Don't use them
  to build systems that listen to people without their consent.

## Use

```python
from datasets import load_dataset
scenes = load_dataset("hyper07/watch-me-safety-scenes", "scenes", split="train")   # audio needs torchcodec
cases = load_dataset("hyper07/watch-me-safety-scenes", "notice_public", split="train")
```

## Licence and sources

CC BY 4.0. Voices: Kokoro-82M (Apache-2.0). Public cases paraphrased from: U.S. EEOC guidance and Youth@Work
material; New York State Sexual Harassment Prevention Model Training (2023) and Case Studies (2018);
StopBullying.gov. Each row names its source and links it.
"""


def build(out: Path) -> None:
    from datasets import Audio, Dataset

    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)
    manifest = json.loads((OUT_SCENES / "manifest.json").read_text())

    def wav(path: Path) -> dict:
        return {"bytes": path.read_bytes(), "path": path.name}

    rows = []
    for scene in manifest["scenes"]:
        harm = next((l["start"] for l in scene["lines"] if l.get("harm_starts")), None)
        rows.append({"audio": wav(OUT_SCENES / f"{scene['id']}.wav"), "id": scene["id"], "label": scene["label"],
                     "background": scene["background"], "note": scene["note"], "seconds": scene["seconds"],
                     "first_harm_at": harm,
                     "transcript": "\n".join(f"[{l['role']}] {l['text']}" for l in scene["lines"]),
                     "script": [{"role": l["role"], "voice": l["voice"], "text": l["text"], "start": l["start"],
                                 "end": l["end"], "harm_starts": bool(l.get("harm_starts"))} for l in scene["lines"]]})
    Dataset.from_list(rows).cast_column("audio", Audio(sampling_rate=16_000)).to_parquet(out / "data" / "scenes.parquet")

    enroll = [{"audio": wav(path), "speaker": "owner", "voice": "kokoro:af_heart", "text": ENROLL_TEXT}
              for path in sorted(OUT_SCENES.glob("_owner_enroll_*.wav"))]
    Dataset.from_list(enroll).cast_column("audio", Audio(sampling_rate=16_000)).to_parquet(out / "data" / "enrollment.parquet")

    Dataset.from_list([{
        "id": c["id"], "setting": c["setting"], "text": c["text"], "expect": list(c["expect"]),
        "should_match": bool(c["expect"]), "official": c["official"], "source": c["source"], "url": c["url"],
        "rescinded_guidance": "Enforcement Guidance on Harassment in the Workplace" in c["source"]}
        for c in PUBLIC_CASES]).to_parquet(out / "data" / "notice_public.parquet")
    Dataset.from_list([{
        "id": c["id"], "setting": c["setting"], "text": c["text"],
        "expect": c["expect"] if c["expect"] not in (None, "none") else None,
        "should_match": c["expect"] not in (None, "none", [])}
        for c in OUR_CASES]).to_parquet(out / "data" / "notice_ours.parquet")

    (out / "README.md").write_text(CARD)
    print(f"built {out}: {len(rows)} scenes, {len(enroll)} enrollment lines, "
          f"{len(PUBLIC_CASES)} public and {len(OUR_CASES)} own Notice cases")


def token() -> str:
    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"]
    for line in (ROOT / ".env").read_text().splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "HF_TOKEN" and value.strip():
            return value.strip().strip('"').strip("'")
    raise SystemExit("HF_TOKEN not set")


def publish(out: Path) -> str:
    from huggingface_hub import HfApi

    api = HfApi(token=token())
    repo = f"{api.whoami()['name']}/{REPO_NAME}"
    api.create_repo(repo, repo_type="dataset", exist_ok=True)
    api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(out), delete_patterns=["*"],
                      commit_message="Watch Me safety scenes: 22 spoken scenes with scripts and audio, 56 Notice cases")
    return f"https://huggingface.co/datasets/{repo}"


if __name__ == "__main__":
    out = Path(sys.argv[1])
    build(out)
    if "--publish" in sys.argv:
        print("published:", publish(out))

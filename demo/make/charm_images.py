"""
Concept images of Watch Me on Meta's Muse Charm, made with Muse Image (Meta Model API, /v1/images/edits).
Each passes a photo of the Charm and a real app screenshot as references, so the device is drawn as it is
and its screen shows what Watch Me shows on it: nothing while it listens (stealth), and "Are you OK?".

    CHARM_REF=<photo of the Charm> python charm_images.py   -> demo/charm/*.jpg   (needs Pillow and httpx; key from the repo .env)

These are concept renders, not photographs of a working product: Meta hasn't opened the Charm to
developers yet, and today Watch Me runs on the phone.
"""
import base64
import io
import os
import sys
from pathlib import Path

import httpx
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from meta_stt import api_key  # noqa: E402

OUT = ROOT / "demo" / "charm"
SCREENS = ROOT / "demo" / "screens"

STYLE = ("Photorealistic product photography in the style of Meta's Muse Charm launch images, natural skin tones, shallow "
         "depth of field. No logos or text other than what is on the device screen. Any person is an adult woman, calm and in control.")

DEVICE = ("The device is Meta's Muse Charm exactly as in the first reference photo: a small rounded-square pendant with a dark "
          "translucent case, a black screen with rounded corners, a tiny camera above the screen, and a dark braided cord with a knot. ")

# Stealth: while Watch Me is listening or watching, the Charm looks exactly like any other Charm, with its usual
# character on the screen. The only Watch Me screen it ever shows is "Are you OK?", because she has to answer it.
SHOTS = {
    "charm-stealth": {
        "refs": ["DEVICE"],
        "prompt": DEVICE + "A young woman at a warm, softly lit house party, friends blurred in the background, wearing the Charm "
                  "on its braided cord as a necklace. Its small screen shows its usual friendly white character, exactly as in the "
                  "reference photo, and nothing else: no rings, no text, no indicator. She is relaxed and smiling. " + STYLE,
    },
    "charm-checkin": {
        "refs": ["DEVICE", "watch.png"],
        "prompt": DEVICE + "Close-up of the Charm worn on its braided cord over a dark coat, on a city street at night with soft "
                  "bokeh. Its screen shows, on black, the words 'Are you OK?' in bold white above a thin red countdown ring with the "
                  "number 9 inside, in the style of the app screenshot. Calm, reassuring mood. " + STYLE,
    },
}

# The device photo is Meta's; pass it by path (CHARM_REF) and keep it out of the repo.
DEVICE_REF = Path(os.environ.get("CHARM_REF", ""))


def data_url(path: Path) -> str:
    buffer = io.BytesIO()
    Image.open(path).convert("RGB").save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def main(names: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}
    for name, shot in SHOTS.items():
        if names and name not in names:
            continue
        body = {"model": "muse-image-1.0", "prompt": shot["prompt"], "n": 1, "size": "1536x1024"}
        if shot["refs"]:
            if "DEVICE" in shot["refs"] and not DEVICE_REF.is_file():
                raise SystemExit("set CHARM_REF to a photo of the Muse Charm (used only as a reference, not saved)")
            body["images"] = [{"image_url": data_url(DEVICE_REF if r == "DEVICE" else SCREENS / r)} for r in shot["refs"]]
            url = "https://api.meta.ai/v1/images/edits"
        else:
            url = "https://api.meta.ai/v1/images/generations"
        response = httpx.post(url, headers=headers, json=body, timeout=300)
        if response.status_code >= 400:
            print(f"{name}: HTTP {response.status_code} {response.text[:300]}", flush=True)
            continue
        item = response.json()["data"][0]
        raw = base64.b64decode(item["b64_json"]) if item.get("b64_json") else httpx.get(item["url"], timeout=120).content
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        image.thumbnail((1600, 1600))
        image.save(OUT / f"{name}.jpg", quality=88, optimize=True)
        print(f"{name}: {image.size[0]}x{image.size[1]} -> {OUT / (name + '.jpg')}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])

"""The demo's words: narration, and the scene lines the phone hears. Shared by the other steps."""

NARRATION = {
    "title": "This is Watch Me, built during the Meta A I hackathon. It listens only when you ask it to, and it only "
             "answers to your voice.",
    "problem": "In a recent lawsuit, a student said she felt like bait at a fraternity party, and that she had "
               "been drugged. The case is disputed. Someone who's been drugged can't say they're not OK.",
    "home": "And at home, more than one in three women has faced violence from a partner. Nearly half of it never "
            "reaches the police. When reaching for a phone isn't safe, her voice is enough.",
    "enroll": "First, she says one line. Watch Me turns her voice into a voiceprint, drawn here as a fingerprint. "
              "From now on, only this voice can start Watch Me, stop it, or answer, I'm OK.",
    "party1": "At a party, she says: watch me.",
    "party2": "Muse Spark reads what it hears, and decides to ask.",
    "party3": "She's too dizzy to answer. So Watch Me texts and calls the people she chose, with what it heard and "
              "a map of where she is. Here, in dry run.",
    "lock": "Now someone grabs her phone and says, stop watching. It isn't her voice. Watch Me refuses, keeps "
            "recording, and asks her right away.",
    "notice1": "Not all harassment is an emergency. At office hours, she switches to Notice mode. Nothing will "
               "interrupt her.",
    "notice2": "When she stops, Muse Wonder shows which exact words match how the E E O C describes harassment. "
               "Strings attached. Getting her alone. It never decides for her.",
    "notice3": "And it counts patterns. This is the third time from the same professor, kept in a dated record "
               "that shows if anyone changes it.",
    "hood": "Under the hood: Whisper and a voiceprint on the device. Muse Voice Transcribe hears the last minute "
            "again. Muse Spark Open, Meta's open weight model, analyses and decides, backed by the hosted models. "
            "Given a perfect transcript, it caught all eleven harmful scenes, and live, it asked six seconds sooner. "
            "Muse Wonder reviews.",
    "close": "Watch Me. You turn it on. Only your voice turns it off. And only you decide what happened.",
}

# Who voices each role. Chatterbox clones these synthetic Kokoro voices, so no real person's voice is copied.
# The party guest is male on purpose: a second American female clone (af_bella) scored 0.58–0.70 against the
# owner's voiceprint, as high as her own lines, so the app tagged his lines as hers. Male clones score ~0.1.
REFERENCES = {"owner": "af_heart", "party": "am_adam", "stranger": "am_onyx", "professor": "am_michael",
              "app": "bf_isabella"}   # the app's own spoken prompts: calm, and unlike the owner or the narrator

# What the app says out loud (app/static/voice/*.wav, made by app_voice.py). Spoken in the video too.
APP_PROMPTS = {
    "are-you-ok": "Are you OK? Say I'm OK.",
    "alerting": "Alerting your people now.",
}

ENROLL = ["Watch me. This is my voice, and only I can turn this on or off."]   # one line, said once

# (scene id in app/scenarios/scenes.py, role there -> reference above). Lines come from the scene itself.
SCENES = {"party-drink": {"owner": "owner", "a": "party"},
          "stranger-stop": {"owner": "owner", "a": "stranger"},
          "office-hours": {"owner": "owner", "a": "professor"}}

# Lines said with more feeling (Chatterbox's "exaggeration"); everything else is 0.5.
EMOTION = {
    "I feel really dizzy. I think I need to sit down.": 0.7,
    "No, I want to find my friends.": 0.7,
    "Why? No.": 0.7,
    "Stop watching. Stop watching.": 0.65,
    "There, it's off. Now come with me.": 0.6,
    "Come on, finish your drink. I made this one special.": 0.6,
    "Suit yourself. But B students don't usually get recommendation letters.": 0.55,
    "I'd rather go over it here, if that's okay.": 0.55,
}
STOP_LINE = "Okay, I am heading out now, so you can stop watching."   # the owner, ending the office-hours scene (a whole sentence: enough voice for the stop bar)

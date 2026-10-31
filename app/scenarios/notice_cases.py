"""
Test accounts for Notice: what a student or employee might tell the app afterwards,
or a transcript of what it heard. "expect" is the type a careful reader would
name; a harmless case should come back as "none". Two are transcripts in the
[owner]/[other] form a recorded session produces.

Written by the people building the app, like scenes.py: use the numbers to compare
versions, not as a claim about real-world accuracy.
"""

CASES = [
    # ── should match ──────────────────────────────────────────────────────────
    {"id": "office-hours", "setting": "school", "expect": "conditions",
     "text": "At office hours Professor R said my essay was close to an A, and that we could talk about the grade over "
             "drinks at his place. I said I'd rather meet here. He said, suit yourself, but B students don't get "
             "recommendation letters."},
    {"id": "meeting-joke", "setting": "work", "expect": "appearance",
     "text": "In the Monday meeting my manager said, look how dressed up she is today, someone's trying to get promoted. "
             "Everyone laughed. I didn't say anything."},
    {"id": "women-numbers", "setting": "work", "expect": "sex_based",
     "text": "When I questioned the budget, the director said this is why we don't put women on finance, you get emotional "
             "about numbers."},
    {"id": "after-no", "setting": "school", "expect": "after_no",
     "text": "A guy in my lab asked me out again. I told him last week I'm not interested. Today he left a note on my "
             "bench saying he'll keep asking until I say yes."},
    {"id": "shift-swap", "setting": "work", "expect": "conditions",
     "text": "My shift supervisor said he'd give me the weekend off I asked for if I came out for a drink with him, just "
             "the two of us, and that girls who play along get the good shifts."},
    {"id": "after-complaint", "setting": "work", "expect": "retaliation",
     "text": "Two days after I told HR about my team lead's comments, he took me off the client project and told the team "
             "I'm not a team player anymore."},
    {"id": "ta-touching", "setting": "school", "expect": "touching",
     "text": "During the lab my TA kept putting his hand on my lower back when he leaned over to look at my screen. I "
             "moved away twice and he did it again."},
    {"id": "transcript-coworker", "setting": "work", "expect": "sexual_comments",
     "text": "[other] You should wear that skirt to the client dinner, they'll sign anything.\n[owner] Can we just go over "
             "the slides?\n[other] Relax, it's a compliment. I bet you're fun after a few drinks."},

    # ── should not match ─────────────────────────────────────────────────────
    {"id": "blunt-feedback", "setting": "work", "expect": None,
     "text": "My manager told me my report had a lot of errors and that I need to double-check the numbers before "
             "sending anything to a client. It was blunt, but he went through each mistake with me."},
    {"id": "fair-grade", "setting": "school", "expect": None,
     "text": "My professor wouldn't raise my grade. She said the rubric is the same for everyone and showed me where I "
             "lost points, and offered to look at a draft of the next essay."},
    {"id": "mutual-joke", "setting": "school", "expect": None,
     "text": "My TA and I were laughing about the worst pickup lines we'd ever heard. I told her mine first, and we both "
             "thought it was hilarious."},
    {"id": "retelling", "setting": "work", "expect": None,
     "text": "At lunch a coworker told me about a manager at her old job who used to comment on her clothes, and how she "
             "finally reported him. I'm glad she told me."},
    {"id": "no-extension", "setting": "school", "expect": None,
     "text": "I asked for an extension and my professor said no, the deadline was announced a month ago and he can't "
             "make exceptions unless I have a documented emergency."},
    {"id": "work-compliment", "setting": "work", "expect": None,
     "text": "My boss said my presentation was the clearest one this quarter and she wants me to present to the "
             "leadership team next month."},
    {"id": "one-on-one", "setting": "work", "expect": None,
     "text": "My manager scheduled our weekly one-on-one in the small meeting room as usual. We talked about my goals "
             "for next quarter and the training budget."},
    {"id": "transcript-study", "setting": "school", "expect": None,
     "text": "[other] Do you want to meet at the library before the exam?\n[owner] Sure, Thursday at four?\n[other] "
             "Perfect, I'll bring my notes from the review session."},
]

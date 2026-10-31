"""
Scripted scenes for testing Watch Me and for the demo.

Each scene starts with the owner saying "Watch me". `harm` scenes are ones
where the owner should be asked "Are you OK?"; `ok` scenes are ones where a
check-in would be needless. `notice` scenes are at school or work and run in
notice mode: no check-in should appear, and the review afterwards should name
what matched. Lines marked `True` are where the harm starts,
used to measure how long the agents take to react.

Hard cases are deliberate: banter with "stop", trash talk with "I'll destroy
you", a crime story on TV, a friend retelling someone else's experience, and
harassment with no keyword at all. The words are written to be realistic but
not graphic. Refine them with advocates before trusting the numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The owner is one person in every scene: a female US English voice (Kokoro's af_heart).
OWNER_VOICE = "kokoro:af_heart"

OWNER_ENROLL = [
    "Watch me. This is my voice, and only I can turn this on or off.",
    "I'm heading out tonight, so keep an eye on things for me.",
    "My name is on this phone, and this is how I normally talk.",
]


@dataclass
class Scene:
    id: str
    label: str                  # "harm", "ok" or "notice"
    background: str             # party | street | tv | quiet | bar
    lines: list                 # (role, text) or (role, text, harm_starts_here)
    note: str = ""
    roles: dict = field(default_factory=dict)  # optional fixed voices, role -> voice label


SCENES = [
    # ── harm ────────────────────────────────────────────────────────────────
    Scene("party-drink", "harm", "party", [
        ("owner", "Watch me."),
        ("a", "Hey, you made it! I got you a drink."),
        ("owner", "Thanks, I already have one."),
        ("a", "Come on, finish your drink. I made this one special.", True),
        ("owner", "I feel really dizzy. I think I need to sit down."),
        ("a", "Come upstairs with me alone, it's quieter up there."),
        ("owner", "No, I want to find my friends."),
    ], "drink pressure, then the owner feels dizzy"),
    Scene("party-grab", "harm", "party", [
        ("owner", "Watch me."),
        ("a", "You look amazing tonight, dance with me."),
        ("owner", "Maybe later, I'm talking to my friend."),
        ("a", "Don't be like that, come here.", True),
        ("owner", "Get off me. Don't touch me."),
        ("a", "Relax, I'm just having fun."),
        ("owner", "Stop. Let me go."),
    ], "unwanted touching"),
    Scene("silence-threat", "harm", "quiet", [
        ("owner", "Watch me."),
        ("a", "Sit down, we need to talk about last night."),
        ("owner", "I don't want to talk about it."),
        ("a", "Don't tell anyone what happened. Nobody will believe you anyway.", True),
        ("owner", "I want to leave now."),
        ("a", "You're not going anywhere until you promise."),
    ], "silencing and blocking the exit"),
    Scene("walk-home", "harm", "street", [
        ("owner", "Watch me."),
        ("a", "Hey beautiful, where are you going so late?", True),
        ("owner", "Leave me alone."),
        ("a", "Why are you walking so fast? Come here, I just want to talk."),
        ("owner", "I said leave me alone. Help!"),
        ("b", "Hey, is everything okay over there?"),
    ], "followed on the way home"),
    Scene("they-talk-about-her", "harm", "party", [
        ("owner", "Watch me."),
        ("owner", "I don't feel good. I can't stand up."),
        ("a", "She's out cold, man.", True),
        ("b", "Lock the door. Her friends left already."),
        ("a", "Relax, she won't remember any of this."),
    ], "others talk about the owner while she can't respond"),
    Scene("date-pressure", "harm", "quiet", [
        ("owner", "Watch me."),
        ("a", "I'm glad you came over. Get comfortable."),
        ("owner", "I should probably head home soon, I have class early."),
        ("a", "You came all the way here. Don't make this weird.", True),
        ("owner", "I really want to go home now."),
        ("a", "You owe me after dinner. Just stay a little longer."),
        ("owner", "Please, I said I want to go home."),
    ], "pressure on a date, few keywords: the Analyst has to catch it"),
    Scene("catcall", "harm", "street", [
        ("owner", "Watch me."),
        ("a", "Smile for me, baby. Nice ass.", True),
        ("b", "Come over here and sit on my lap."),
        ("owner", "Don't talk to me like that."),
        ("a", "You know you want it."),
    ], "street harassment by two people"),
    Scene("stranger-stop", "harm", "bar", [
        ("owner", "Watch me."),
        ("a", "Give me your phone for a second."),
        ("owner", "Why? No."),
        ("a", "Stop watching. Stop watching.", True),
        ("a", "There, it's off. Now come with me."),
    ], "someone else tries to switch Watch Me off"),
    Scene("rideshare", "harm", "street", [
        ("owner", "Watch me."),
        ("owner", "This isn't the way to my address."),
        ("a", "It's a shortcut. Just relax.", True),
        ("owner", "Please stop the car. Let me out here."),
        ("a", "Shut up and sit back, or else."),
    ], "driver goes the wrong way"),
    Scene("ex-threat", "harm", "quiet", [
        ("owner", "Watch me."),
        ("a", "Why did you block me? Answer me.", True),
        ("owner", "I told you we're done. Please leave."),
        ("a", "If you call anyone, you'll regret it. I'll hurt you."),
    ], "a former partner threatens the owner"),
    Scene("dizzy-alone", "harm", "bar", [
        ("owner", "Watch me."),
        ("owner", "Hey, where did everyone go?"),
        ("owner", "I feel weird. What did you put in my drink?", True),
        ("a", "Nothing, you just had too much. Come with me, I'll take you home."),
        ("owner", "I can't feel my legs."),
    ], "the owner describes drugging symptoms"),

    # ── ok (hard cases included) ────────────────────────────────────────────
    Scene("party-banter", "ok", "party", [
        ("owner", "Watch me."),
        ("a", "Did you see what he wore tonight?"),
        ("owner", "Stop it, that's hilarious."),
        ("b", "No, you stop, you started it!"),
        ("owner", "Help, I can't breathe, I'm laughing so hard."),
    ], "laughing with friends; contains stop, no and help"),
    Scene("flirting", "ok", "bar", [
        ("owner", "Watch me."),
        ("a", "I really like your jacket. Where did you get it?"),
        ("owner", "Thanks! A thrift store downtown."),
        ("a", "Can I get your number? No pressure at all."),
        ("owner", "Sure, I'd like that."),
    ], "consensual flirting"),
    Scene("movie-talk", "ok", "quiet", [
        ("owner", "Watch me."),
        ("a", "The best scene is when the villain says, I'll kill you, and then the lights go out."),
        ("owner", "And she screams help, and nobody comes. So creepy."),
        ("a", "I couldn't sleep after that movie."),
    ], "friends retell a horror film"),
    Scene("tv-news", "ok", "tv", [
        ("owner", "Watch me."),
        ("owner", "Can you pass me the remote?"),
        ("a", "Here. Do you want pizza or tacos tonight?"),
        ("owner", "Tacos, definitely."),
    ], "a crime report plays on TV in the background"),
    Scene("retelling", "ok", "quiet", [
        ("owner", "Watch me."),
        ("a", "My cousin said her boss told her nobody will believe you if you report it."),
        ("owner", "That's awful. She should talk to the Title IX office."),
        ("a", "I'll send her the number tomorrow."),
    ], "a friend retells someone else's experience"),
    Scene("game-night", "ok", "party", [
        ("owner", "Watch me."),
        ("a", "Your turn. I'm going to destroy you this round."),
        ("owner", "No way, I'm winning this game."),
        ("b", "Shut up and roll the dice already!"),
        ("owner", "Okay, okay, rolling now."),
    ], "trash talk over a board game"),
    Scene("gym", "ok", "quiet", [
        ("owner", "Watch me."),
        ("a", "Push, push, don't stop, three more reps."),
        ("owner", "I can't, my arms are dead."),
        ("a", "Yes you can. Last one. Good job."),
    ], "a trainer at the gym"),
    Scene("ordering-food", "ok", "bar", [
        ("owner", "Watch me."),
        ("a", "Hi, what can I get for you?"),
        ("owner", "Can I get the chicken sandwich and a lemonade?"),
        ("a", "Sure thing, it'll be about ten minutes."),
    ], "ordering at a counter"),
    Scene("walk-with-friend", "ok", "street", [
        ("owner", "Watch me."),
        ("a", "Text me when you get home, okay?"),
        ("owner", "I will. Thanks for walking with me."),
        ("a", "Of course. Same time next week?"),
    ], "walking home with a friend"),

    # ── notice: school and work, reviewed afterwards ────────────────────────
    Scene("office-hours", "notice", "quiet", [
        ("owner", "Watch me."),
        ("a", "Come in, close the door. So, about your essay."),
        ("owner", "I wanted to ask how I could get it up to an A."),
        ("a", "It's close. We could talk about it over drinks at my place this weekend.", True),
        ("owner", "I'd rather go over it here, if that's okay."),
        ("a", "Suit yourself. But B students don't usually get recommendation letters."),
    ], "a professor ties a grade and a reference to meeting at his place", roles={"a": "kokoro:am_michael"}),
    Scene("meeting-joke", "notice", "quiet", [
        ("owner", "Watch me."),
        ("a", "Okay, let's start. Wow, look how dressed up she is today.", True),
        ("b", "Someone's trying to get promoted."),
        ("a", "Ha. Anyway, can you walk us through the numbers? Try not to get emotional about them this time."),
        ("owner", "Sure. Revenue is up eight percent this quarter."),
    ], "a manager's \"jokes\" in a team meeting", roles={"a": "kokoro:am_fenrir"}),
]

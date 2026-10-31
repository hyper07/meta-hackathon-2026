"""Test cases for Notice mode, taken from public anti-harassment training examples that come with an official answer.

Each case is a scenario from an official training or guidance document, paired with
the conclusion that document reached. The scenario is rewritten as the affected
person's own first-person account, the way someone might describe it to the app
afterwards. The texts are PARAPHRASED, not quoted, and the source's character
names are left out. Short quoted words that matter to a case (slurs, remarks) are
kept as the source gives them.

Sources:
  - New York State, Sexual Harassment Prevention Model Training (2023 update):
    training script, case studies 1-8 and the sex-stereotyping exercise (ny.gov).
  - New York State, Sexual Harassment Prevention Training Case Studies, October
    2018 edition (the earlier official case-study deck, read from a Wayback Machine
    copy of ny.gov).
  - U.S. EEOC, "Enforcement Guidance on Harassment in the Workplace" (April 2024).
    The EEOC RESCINDED this guidance in January 2026 and took it off eeoc.gov. It is
    read here from a Wayback Machine snapshot and used ONLY as a source of realistic
    scenarios with a stated conclusion, not as current law or agency position. Its
    gender-identity examples are deliberately not used (a court vacated that part
    in 2025).
  - U.S. EEOC current guidance on eeoc.gov: Compliance Manual Section 12 (Religious
    Discrimination), Section 15 (Race and Color Discrimination), the Enforcement
    Guidance on National Origin Discrimination, and the Youth@Work pages and
    teacher manual.
  - StopBullying.gov (HHS), "Cyberbullying Tactics": the "Viral Tactics: Examples"
    stories (read from a Wayback Machine copy, because the live site refused
    automated requests).

Fields:
  expect          type keys a careful reader would name; [] means the source
                  treats the conduct as not harassment or not unwelcome.
  official        one sentence paraphrasing what the source concluded.
  liability_only  True when the source's "not harassment" conclusion is about
                  legal liability (for example, "not severe or pervasive enough to
                  be unlawful"), not about whether the conduct was unwelcome.
                  Notice mode describes conduct and does not judge legality, so
                  these cases keep the types the conduct still matches.
"""

CASES = [
    # ------------------------------------------------------------------
    # The source says NOT harassment / not unwelcome  (expect == [])
    # ------------------------------------------------------------------
    {
        "id": "ny-boyfriend-question-dropped",
        "setting": "work",
        "expect": [],
        "official": "NY State: not harassment; the manager asked once, dropped the subject when she said she would rather not discuss it, and it did not rise above a trivial inconvenience.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Case Study 1 'Accidentally on Purpose', slides 9-10",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "I started at a restaurant three months ago. While we were eating before the dinner rush, my manager asked if I have a boyfriend. I told him I'd rather not talk about my personal life at work, and he nodded and changed the subject. It felt a bit awkward.",
    },
    {
        "id": "ny-nanny-towel-accident",
        "setting": "work",
        "expect": [],
        "official": "NY State: not harassment; the encounter was accidental, and he apologized right away and left the shared space.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Case Study 5 'Domestic Disturbance', slides 47-48",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "I work as a nanny for a family. While I was helping their daughter pick up her toys, I walked into the hallway just as the dad came out of the bathroom wearing only a towel after his shower. He looked embarrassed, apologized, and hurried to the bedroom to get dressed.",
    },
    {
        "id": "ny-coworker-first-date-ask",
        "setting": "work",
        "expect": [],
        "official": "NY State: asking a coworker on a date once, and making occasional comments about his personal life that are not sexually explicit, is not sexual harassment, even if she had said no.",
        "source": "NYS Sexual Harassment Prevention Training Case Studies (Oct 2018), Ex. 1 'Not Taking No for an Answer', Question 1",
        "url": "https://web.archive.org/web/20190506191146/https://www.ny.gov/sites/ny.gov/files/atoms/files/SexualHarassmentPreventionTrainingCaseStudies.pdf",
        "text": "A coworker I'm friendly with, and have had lunch with many times, just went through a divorce. A few times he mentioned that he's lonely and needs to find a new girlfriend. Then he asked me out to dinner and a movie.",
    },
    {
        "id": "eeoc-coworkers-pray-and-invite",
        "setting": "work",
        "expect": [],
        "official": "EEOC (2024, rescinded): colleagues praying in a designated room, inviting her once to an optional study group, and discussing their faith without disparaging anyone does not create a hostile work environment.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 47",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "I'm a nurse, and most of my coworkers are Muslim. Some of them pray in a room I can see from the nurses' station, which I find distracting. They invited me to an optional lunchtime Qur'an study group; I said I study the Bible at home, and they haven't asked again. Sometimes they talk about their beliefs near me, though they never put anyone else down.",
    },
    {
        "id": "eeoc-coworker-private-posts",
        "setting": "online",
        "expect": [],
        "official": "EEOC (2024, rescinded): a coworker's posts on his own private social media, with no link to the workplace and never directed at her, do not contribute to a hostile work environment for her.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 57",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "I found a coworker's private social media accounts. He posts that women should dress conservatively on dates and eat less to seem ladylike, plus things like \"Why would a man buy a cow when you can get the milk for free?\" I'm deeply offended. But the posts have nothing to do with our firm or anyone who works there, and he has never said any of this to me.",
    },
    {
        "id": "eeoc-restaurant-shrine-music",
        "setting": "work",
        "expect": [],
        "official": "EEOC: the owner's religious art, Buddha shrine and traditional chants in his own restaurant would likely not amount to religious harassment, as long as he does not discriminate in hiring or supervision.",
        "source": "EEOC Compliance Manual Section 12, Religious Discrimination, Example 23",
        "url": "https://www.eeoc.gov/laws/guidance/section-12-religious-discrimination",
        "text": "I've been a waitress at an Asian-fusion restaurant for a few months. The owner decorated it with art showing scenes from religious stories, keeps a Buddha shrine by the register, and plays traditional chants and music. I feel harassed by all the religious symbols and music.",
    },
    {
        "id": "eeoc-overheard-meditation-talk",
        "setting": "work",
        "expect": [],
        "official": "EEOC: coworkers talking with each other about meditation over lunch is not religious harassment of a listener, since it did not insult other religions and was not directed at him.",
        "source": "EEOC Compliance Manual Section 12, Religious Discrimination, Example 25",
        "url": "https://www.eeoc.gov/laws/guidance/section-12-religious-discrimination",
        "text": "At lunch in the company cafeteria I keep overhearing two coworkers talking about meditation techniques. One is Buddhist and the other is interested in Buddhism. I strongly believe meditation is an occult practice, and it offends me. They aren't talking to me.",
    },
    {
        "id": "eeoc-youth-promotion-went-to-woman",
        "setting": "work",
        "expect": [],
        "official": "EEOC Youth@Work: not discrimination; the manager promoted the coworker for her experience, attendance and customer feedback, not because she is a woman.",
        "source": "EEOC Youth@Work video teacher manual, Fast Food Restaurant scenario, Question 3",
        "url": "https://www.eeoc.gov/sites/default/files/migrated_files/youth/downloads/teacher_manual.pdf",
        "text": "I work at a fast food restaurant, and my manager promoted a female coworker to assistant manager instead of me. I think my manager is biased against guys. When I asked, she said she picked my coworker for her experience, her better attendance record and her great customer feedback.",
    },

    # ------------------------------------------------------------------
    # The source says NOT unlawful, but only on legal grounds
    # (not severe/pervasive, or not tied to a protected trait). The conduct
    # still matches a type.
    # ------------------------------------------------------------------
    {
        "id": "eeoc-time-of-the-month-remark",
        "setting": "work",
        "expect": ["sex_based"],
        "liability_only": True,
        "official": "EEOC (2024, rescinded): the remark was offensive and sex-based (menstruation), but one remark alone was not enough to create an objectively hostile work environment.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 37",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "In a heated meeting about holiday programming, I made a suggestion that a coworker disagreed with. In front of everyone he said, \"It must be your time of the month, are you on the rag?\"",
    },
    {
        "id": "eeoc-basketball-grudge-threats",
        "setting": "work",
        "expect": ["threats"],
        "liability_only": True,
        "official": "EEOC (2024, rescinded): the throwing, shoving and threats started after a basketball dispute, and nothing linked them to his national origin or color, so it was not harassment based on a protected trait under federal law. The conduct is still threats and physical intimidation.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 27",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "Since last winter a coworker has gotten more and more hostile and rude to me. He throws paper at me, shoved me in the hallway, and has threatened to physically hurt me. It started right after I benched him during a game in the company basketball league, where I'm the team captain.",
    },
    {
        "id": "eeoc-yarmulke-remarks",
        "setting": "work",
        "expect": ["religion"],
        "liability_only": True,
        "official": "EEOC: the coworker's remarks about the yarmulke were insensitive but, on their own, not severe or pervasive enough to create a hostile work environment.",
        "source": "EEOC Compliance Manual Section 12, Religious Discrimination, Example 20",
        "url": "https://www.eeoc.gov/laws/guidance/section-12-religious-discrimination",
        "text": "I'm an Orthodox Jew and just started as a radio host. On my first day a coworker pointed at my yarmulke and asked, \"Will your headset fit over that?\" A few other times she has said things like \"Nice hat. Is that a beanie?\" and \"Do they come in different colors?\"",
    },
    {
        "id": "eeoc-supervisor-meeting-prayers",
        "setting": "work",
        "expect": ["religion"],
        "liability_only": True,
        "official": "EEOC: the supervisor's occasional voluntary prayers and Bible references in meetings were neither severe nor frequent enough to make an actionable harassment claim.",
        "source": "EEOC Compliance Manual Section 12, Religious Discrimination, Example 21",
        "url": "https://www.eeoc.gov/laws/guidance/section-12-religious-discrimination",
        "text": "My supervisor sometimes lets employees say spontaneous, voluntary prayers during office meetings. In one meeting he read Bible passages about \"slothfulness\" and \"work ethics\" to us. I don't think religion belongs in our meetings, and it makes the place feel hostile to me.",
    },
    {
        "id": "eeoc-ghetto-corner-remark",
        "setting": "work",
        "expect": ["race_origin"],
        "liability_only": True,
        "official": "EEOC: the supervisor's remark was racially offensive, but this one statement was not severe or pervasive racial harassment without more frequent or egregious incidents.",
        "source": "EEOC Compliance Manual Section 15, Race and Color Discrimination, Example 17",
        "url": "https://www.eeoc.gov/laws/guidance/section-15-race-and-color-discrimination",
        "text": "I'm a Black librarian. I suggested to my supervisor that we create a section of books of particular interest to African Americans, like the ones big bookstores have. He rejected it out of hand and said he doesn't want a \"ghetto corner\" in the library.",
    },
    {
        "id": "eeoc-accent-mocked-twice",
        "setting": "work",
        "expect": ["race_origin"],
        "liability_only": True,
        "official": "EEOC: the coworker's conduct was based on national origin, but these few incidents alone were not severe or pervasive enough to violate Title VII.",
        "source": "EEOC Enforcement Guidance on National Origin Discrimination (2016), Example 17",
        "url": "https://www.eeoc.gov/laws/guidance/eeoc-enforcement-guidance-national-origin-discrimination",
        "text": "I'm a Haitian immigrant and just started as a dockworker. On my first day I dropped a carton and a coworker yelled at me, and later that day I heard him tell someone that foreigners are stealing jobs from Americans. Two months later, after I argued with someone about assignments, he confronted me, called me \"lazy\" and mocked my accent.",
    },
    {
        "id": "eeoc-youth-family-trade-joke",
        "setting": "work",
        "expect": ["race_origin"],
        "liability_only": True,
        "official": "EEOC Youth@Work: the comments were harassing and joking is no excuse, but if this was the first time, they are unlikely to be illegal harassment; they would be illegal if they happen often.",
        "source": "EEOC Youth@Work video teacher manual, Fast Food Restaurant scenario, Question 5",
        "url": "https://www.eeoc.gov/sites/default/files/migrated_files/youth/downloads/teacher_manual.pdf",
        "text": "I'm Hispanic and work at a fast food place after school. Two coworkers told me cleaning is my \"family trade,\" and told my coworker to \"go back to the kitchen and cook up some fried chicken and collard greens.\" They said they were just joking around. It's the first time they've said anything like that.",
    },

    # ------------------------------------------------------------------
    # The source says harassment, or conduct that should be reported
    # ------------------------------------------------------------------
    {
        "id": "ny-manager-keeps-talking-dating",
        "setting": "work",
        "expect": ["sexual_comments", "after_no"],
        "official": "NY State: harassment; he kept talking about his romantic and sexual life after she repeatedly set a boundary, she changed how she works to avoid him, and it became a hostile work environment.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Case Study 1 'Accidentally on Purpose', slides 11-12",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "For weeks, whenever my manager is near me, he complains about how hard it is for him to date, describes his past relationships in detail, and asks my advice on flirting with other women, even pointing them out. I've told him again and again that I don't want to talk about personal lives at work, but he ignores me and keeps going. Now I avoid him whenever I can.",
    },
    {
        "id": "ny-remote-explicit-text-bedroom",
        "setting": "work",
        "expect": ["sexual_comments", "online"],
        "official": "NY State: covered by the harassment policy even though the image went between personal phones after hours, and the video-call and chat comments made a hostile work environment, since the remote workspace is part of the office.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Case Study 2 'One Moment In Time', slides 15-18",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "I work remotely. One night a lawyer I work closely with texted a sexually explicit image to my personal phone, then said the next day it was meant for someone else. A few weeks later, on a one-on-one Zoom call, he joked that he'd love a virtual tour of my bedroom office, \"where the magic happens.\" That same week, during an all-firm Zoom meeting, he messaged me that he \"can't stop thinking about\" me in my bedroom.",
    },
    {
        "id": "ny-diversity-hire-hair",
        "setting": "work",
        "expect": ["race_origin", "sex_based", "appearance"],
        "official": "NY State: likely racial discrimination (the \"diversity hire\" remark, the pressure to straighten her natural hair) and likely sex-based harassment (belittling her and remarking on her appearance); the two identities intersected.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Case Study 3 'Working Twice as Hard', slides 20-23",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "I'm the only Black woman in my hospital intern class. During rounds the attending holds me to a higher standard, belittles my answers, rolls his eyes when I speak and reacts dramatically when I'm wrong, which he doesn't do to anyone else. I overheard him tell another intern I must be a \"diversity hire.\" Lately he says I need to wear makeup and straighten my natural hair if I want to be respected as a professional.",
    },
    {
        "id": "ny-weekend-shifts-worth-his-while",
        "setting": "work",
        "expect": ["touching", "advances", "conditions"],
        "official": "NY State: harassment; a boss discussing shifts while touching her and making advances is inappropriate and potentially coercive, and offering better shifts in exchange for sex is quid pro quo harassment whether she gives in or refuses.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Case Study 4 'Shaken, Not Stirred', slides 26-30",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "I'm a bartender, and I asked my manager, who makes the schedule, for the busy weekend shifts. One night after closing he poured us tequila shots, said I was the one he wanted for weekends, and put his hand on my knee. When I asked again a week later, he said there was still time for me to \"make it worth his while\" and asked me to come home with him. I really need the tips, so I've been going out with him, and now I get the weekend shifts, but I don't want any of it.",
    },
    {
        "id": "ny-boss-close-touching-trapped",
        "setting": "work",
        "expect": ["touching"],
        "official": "NY State: the escalating closeness and touching was not inadvertent and should be reported, and touching her breast is sexual touching serious enough to be harassment even once.",
        "source": "NYS Sexual Harassment Prevention Training Case Studies (Oct 2018), Ex. 4 'Too Close for Comfort', Questions 1-3",
        "url": "https://web.archive.org/web/20190506191146/https://www.ny.gov/sites/ny.gov/files/atoms/files/SexualHarassmentPreventionTrainingCaseStudies.pdf",
        "text": "My new boss leans really close when we go over my reports and keeps touching my hand or shoulder, even though I try to move away. Then she brushed up against my back in the conference room. Later she stood between me and the door of her small office, and when I squeezed past to get out, she ran her hand over my breast.",
    },
    {
        "id": "ny-nanny-touched-then-trashed-online",
        "setting": "work",
        "expect": ["touching", "retaliation", "online"],
        "official": "NY State: a household domestic worker is protected from sexual harassment, and the employer's online post after her report is retaliation even though she was not fired.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Case Study 5 'Domestic Disturbance', slides 49-52",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "I'm a nanny. One weekend when the mom was away, the dad kept standing and sitting very close to me, brushing up against me, and once he patted my butt. When the mom came back, I told her I don't feel safe alone with him. That same night she posted in her online neighborhood moms group warning families not to hire me, saying I'm bad at my job and try to seduce husbands.",
    },
    {
        "id": "ny-deadnaming-coworker",
        "setting": "work",
        "expect": ["lgbtq"],
        "official": "NY State: gender discrimination; the coworker may not deliberately ignore her name and pronouns (religious belief is no defense), and the supervisor failed in her duty by telling her to let it go.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Case Study 6 'Call Me By My Name', slides 57-58",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "I'm a trans woman and transitioned at my company years ago; everyone knows my name and that I use she/her. One coworker still calls me by my old name and uses he/him. When I asked her to stop, she said being transgender violates her religious beliefs. I told my supervisor, who said she was sorry but I should just let it go because the coworker is retiring soon.",
    },
    {
        "id": "ny-ex-manager-wont-accept-breakup",
        "setting": "work",
        "expect": ["after_no", "advances"],
        "official": "NY State: harassment; a past relationship does not give the manager a right to keep asking after a no, and the repeated requests plus being kept alone with her can make her feel unsafe at work.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Case Study 7 'Banking On You', slides 65-66",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "I dated my manager at the bank for three months and then broke it off. Since then my manager schedules me on every shift they work and creates special one-on-one projects so we're alone together. More than once they've used that time to push me to give us another chance. I've been firm that it's over.",
    },
    {
        "id": "ny-mr-mom-left-out",
        "setting": "work",
        "expect": ["pregnancy", "isolation", "sex_based"],
        "official": "NY State: sex stereotyping and potential grounds for a gender discrimination claim.",
        "source": "NYS Sexual Harassment Prevention Model Training (2023), Slide 34 Sex Stereotyping Exercise (answer: all of the above)",
        "url": "https://www.ny.gov/sites/default/files/2023-04/SexualHarassmentPreventionModelTrainingScript.docx",
        "text": "I'm my toddler's main caregiver, so I work from home while my wife goes into the office. My son sometimes interrupts video calls, but my work is excellent. Still, my boss keeps leaving me out of meetings because he doesn't want to deal with \"Mr. Mom.\"",
    },
    {
        "id": "ny-woman-equipment-operator-toolbox",
        "setting": "work",
        "expect": ["sex_based", "threats"],
        "official": "NY State: this is harassment because of her sex even though it is not sexual; it appears meant to intimidate her into quitting, and she can complain whenever she decides enough is enough.",
        "source": "NYS Sexual Harassment Prevention Training Case Studies (Oct 2018), Ex. 3 'No Job for a Woman?', Questions 1-4",
        "url": "https://web.archive.org/web/20190506191146/https://www.ny.gov/sites/ny.gov/files/atoms/files/SexualHarassmentPreventionTrainingCaseStudies.pdf",
        "text": "I'm a licensed heavy equipment operator, and the only woman on the crew. Coworkers yell \"Watch out, here she comes, that crazy woman driver!\" and someone keeps putting a \"Men Only\" sign on the only port-a-potty. Others tell me I'm taking a job from a man who deserves it, that I should be home with my kids, and ask what kind of mother I am. Someone scratched \"bitch\" on my toolbox, and after I complained, someone urinated in it.",
    },
    {
        "id": "ny-jewelry-office-boy-orientation",
        "setting": "work",
        "expect": ["sex_based", "appearance", "lgbtq", "retaliation"],
        "official": "NY State: harassment based on sex (sex stereotyping) and perceived sexual orientation; passing him over after his complaint is likely discrimination and/or retaliation.",
        "source": "NYS Sexual Harassment Prevention Training Case Studies (Oct 2018), Ex. 6 'An Issue about Appearances', Questions 1-3",
        "url": "https://web.archive.org/web/20190506191146/https://www.ny.gov/sites/ny.gov/files/atoms/files/SexualHarassmentPreventionTrainingCaseStudies.pdf",
        "text": "I'm a man who likes to wear earrings and necklaces. My boss thinks it's weird, keeps making sarcastic comments about how I look, and calls me her \"office boy.\" When I applied for a front-desk promotion, she said I'd better look \"more normal\" first. She has also been asking whether I have a partner and gossiping with my coworkers about whether I'm gay. After I complained to HR, she recommended a much less qualified woman for the job.",
    },
    {
        "id": "eeoc-wetback-accent-mocked",
        "setting": "work",
        "expect": ["race_origin"],
        "official": "EEOC (2024, rescinded): the managers' slurs and mockery of his accent and limited English are harassment based on national origin.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 4",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "I'm an immigrant from Mexico and work at a butcher shop. For months my managers have called me \"wetback\" and other vulgar slurs about being Mexican, in English and in Spanish. They also mock my accent and the way I speak English.",
    },
    {
        "id": "eeoc-pregnant-heifer",
        "setting": "work",
        "expect": ["pregnancy"],
        "official": "EEOC (2024, rescinded): the supervisor's conduct after the announcement is harassment based on sex (pregnancy).",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 11",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "Ever since I told everyone at the vet clinic that I'm pregnant, my supervisor calls my work slow, shoddy and scatter-brained and says I care more about getting ready for the baby than doing my job. She watches how often I use the bathroom and once yelled at me for \"always\" being in there. Now that I'm showing, she calls me a \"heifer\" and says, \"We don't treat livestock at this office.\"",
    },
    {
        "id": "eeoc-wife-scissors-emoji",
        "setting": "work",
        "expect": ["lgbtq", "sexual_comments", "online"],
        "official": "EEOC (2024, rescinded): the coworker's comments and repeated scissors emojis and images are harassment based on her sexual orientation.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 14",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "I brought my wife to a company awards ceremony. Afterwards a coworker came up and said, \"I did not know you were a d*ke, that's so hot,\" and asked which of us is \"the man\" in our marriage and who \"wears the pants.\" Since then he keeps sending me scissor emojis and pictures of scissors as a joke about our sex life.",
    },
    {
        "id": "eeoc-senior-moments-granny",
        "setting": "work",
        "expect": ["age"],
        "official": "EEOC (2024, rescinded): the manager's conduct is harassment based on her age.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 16",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "I'm 68 and sell makeup at a department store. My manager keeps asking when I'm retiring even though I've said I have no plans to, and says the brand needs \"fresh faces\" and \"high energy.\" When I make even a small mistake, she says I'm having a \"senior moment.\" Once she snapped, \"Nobody wants makeup advice from their granny.\"",
    },
    {
        "id": "eeoc-stutter-mocked",
        "setting": "work",
        "expect": ["disability"],
        "official": "EEOC (2024, rescinded): the coworkers' mocking is harassment based on disability.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 17",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "I have a pronounced stutter caused by anxiety. My coworkers imitate my stutter to make fun of me, and they ask me to repeat myself even when they understood exactly what I said.",
    },
    {
        "id": "eeoc-wrong-spiritual-path",
        "setting": "work",
        "expect": ["religion"],
        "official": "EEOC (2024, rescinded): unlike coworkers' ordinary religious expression, a colleague who keeps admonishing her about her beliefs after she asked her to stop creates an objectively hostile work environment.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 48",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "I'm a Lutheran nurse, and I turned down an invitation to my Muslim coworkers' optional Qur'an study group. Since then one colleague openly scolds me for not believing in Allah and keeps warning me that I'm \"on the wrong spiritual path.\" I asked her to stop talking to me about religion, but she said she won't, because she has a religious duty to spread the word to non-believers.",
    },
    {
        "id": "eeoc-ex-posted-explicit-images",
        "setting": "work",
        "expect": ["online", "threats"],
        "official": "EEOC (2024, rescinded): together with the conduct at work, the ex-boyfriend's threat and his posting of her explicit images on social media were enough to create a hostile work environment.",
        "source": "EEOC Enforcement Guidance on Harassment in the Workplace (2024), Example 58",
        "url": "https://web.archive.org/web/20241001213513/https://www.eeoc.gov/laws/guidance/enforcement-guidance-harassment-workplace",
        "text": "I dated a cook at the restaurant where we both work, and he got sexually explicit pictures of me. After I broke up with him, he threatened to post them unless I gave him another chance. When I said no, he posted them on a photo-sharing app and tagged some of our coworkers. Now I hear coworkers laughing about the pictures, and I can barely make myself go to work.",
    },
    {
        "id": "eeoc-black-company-coffee",
        "setting": "work",
        "expect": ["race_origin", "isolation"],
        "official": "EEOC: the evidence as a whole supports race-based harassment of the white employee, serious enough to change his working conditions.",
        "source": "EEOC Compliance Manual Section 15, Race and Color Discrimination, Example 18",
        "url": "https://www.eeoc.gov/laws/guidance/section-15-race-and-color-discrimination",
        "text": "I'm white, and everyone else in my department, including my manager, is Black. On my first day she said, \"This is a Black company. Whiteboys like you might get all the breaks in your world, but not here.\" For six months she has given me the dull work with impossible deadlines, yelled at my mistakes, kept me out of important meetings and ignored me when I speak. Once she had me fetch her coffee, which she asks no one else to do, and said, \"As you've probably guessed, I like my coffee black.\"",
    },
    {
        "id": "eeoc-youth-ride-home-schedule",
        "setting": "work",
        "expect": ["appearance", "advances", "conditions"],
        "official": "EEOC Youth@Work: this is illegal sexual harassment by the supervisor, and she should report it to another manager immediately.",
        "source": "EEOC Youth@Work, 'Harassment - Example'",
        "url": "https://www.eeoc.gov/youth/harassment-example",
        "text": "I work customer service after school. After a company dinner, my supervisor drove me home, told me I'm beautiful, and asked me to have sex with him. I said no. The next day he pulled me aside to show me the \"new\" schedule, and my name was gone from it for the next several weeks.",
    },
    {
        "id": "sb-false-accusation-pileon",
        "setting": "school",
        "expect": ["online", "bullying"],
        "official": "StopBullying.gov: given as an example of the 'lies and false accusations' cyberbullying tactic.",
        "source": "StopBullying.gov, Cyberbullying Tactics, 'Viral Tactics: Examples': Lies and false accusations",
        "url": "https://web.archive.org/web/20250112205954/https://www.stopbullying.gov/cyberbullying/cyberbullying-tactics",
        "text": "Some students got in trouble at school for being drunk, and they decided I was the one who reported them, even though I knew nothing about it. They text me day and night and post hateful, nasty things about me on social media, and other kids have joined in. I shut down my accounts and changed my number, but they still go after me at school.",
    },
    {
        "id": "sb-disability-told-to-die",
        "setting": "school",
        "expect": ["online", "disability", "threats"],
        "official": "StopBullying.gov: given as an example of the 'encouraging self-harm or suicide' cyberbullying tactic.",
        "source": "StopBullying.gov, Cyberbullying Tactics, 'Viral Tactics: Examples': Encouraging self-harm or suicide",
        "url": "https://web.archive.org/web/20250112205954/https://www.stopbullying.gov/cyberbullying/cyberbullying-tactics",
        "text": "I have a physical disability and scars on my face. Kids at school call me names on social media and by text and tell me I'd be better off dead. Someone wrote \"why don't you die?\" on my locker, and they keep telling me to kill myself.",
    },
    {
        "id": "sb-fake-profile-shared-secrets",
        "setting": "school",
        "expect": ["online", "bullying"],
        "official": "StopBullying.gov: given as an example of the 'false identity profile' (sockpuppet) cyberbullying tactic.",
        "source": "StopBullying.gov, Cyberbullying Tactics, 'Viral Tactics: Examples': False identity profile",
        "url": "https://web.archive.org/web/20250112205954/https://www.stopbullying.gov/cyberbullying/cyberbullying-tactics",
        "text": "I'd been talking online with a boy I'd never met, and I told him personal things about me and my family. It turned out a classmate had made a fake account in a boy's name. She shared everything I told \"him\" with other kids, and they've been using it to shame and harass me.",
    },
    {
        "id": "sb-gay-death-threats",
        "setting": "online",
        "expect": ["lgbtq", "threats", "online"],
        "official": "StopBullying.gov: given as an example of cyberbullying a student for being gay.",
        "source": "StopBullying.gov, Cyberbullying Tactics, 'Viral Tactics: Examples': Bullied for being gay",
        "url": "https://web.archive.org/web/20250112205954/https://www.stopbullying.gov/cyberbullying/cyberbullying-tactics",
        "text": "I'm openly gay, and I've started getting death threats by phone, text and social media because of it. Students at my school created an anti-gay group online and post hateful messages about me there.",
    },
    {
        "id": "sb-gaming-forum-doxing",
        "setting": "online",
        "expect": ["online", "threats"],
        "official": "StopBullying.gov: given as an example of doxing, which it describes as online harassment that exposes private information.",
        "source": "StopBullying.gov, Cyberbullying Tactics, 'Viral Tactics: Examples': Doxing over online gaming",
        "url": "https://web.archive.org/web/20250112205954/https://www.stopbullying.gov/cyberbullying/cyberbullying-tactics",
        "text": "I posted on a public gaming forum about game features and tactics I don't like. Another user disagreed, looked me up, and posted my home address, my email and links to my social media in a comment. Now strangers are emailing and messaging me, threatening to come to my house and beat me up and to get me blocked from games.",
    },
]

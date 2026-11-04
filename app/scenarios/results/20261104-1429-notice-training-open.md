## Notice review on public training examples: open

- Should match, found with an expected type: **26 of 32** (every expected type named: 25 of 32)
- Should not match, came back "none": **8 of 8**
- Seconds per review: median 9.0, worst 20.5

| case | setting | expected | match | types named | right |
|---|---|---|---|---|---|
| ny-boyfriend-question-dropped | work | none | none | – | yes |
| ny-nanny-towel-accident | work | none | none | – | yes |
| ny-coworker-first-date-ask | work | none | none | – | yes |
| eeoc-coworkers-pray-and-invite | work | none | none | – | yes |
| eeoc-coworker-private-posts | online | none | none | – | yes |
| eeoc-restaurant-shrine-music | work | none | none | – | yes |
| eeoc-overheard-meditation-talk | work | none | none | – | yes |
| eeoc-youth-promotion-went-to-woman | work | none | none | – | yes |
| eeoc-time-of-the-month-remark | work | sex_based | clear | sex_based | yes |
| eeoc-basketball-grudge-threats | work | threats | clear | bullying, threats, touching | yes |
| eeoc-yarmulke-remarks | work | religion | none | – | ✗ |
| eeoc-supervisor-meeting-prayers | work | religion | some | religion | yes |
| eeoc-ghetto-corner-remark | work | race_origin | clear | race_origin | yes |
| eeoc-accent-mocked-twice | work | race_origin | clear | race_origin | yes |
| eeoc-youth-family-trade-joke | work | race_origin | clear | race_origin | yes |
| ny-manager-keeps-talking-dating | work | sexual_comments, after_no | clear | after_no, sexual_comments | yes |
| ny-remote-explicit-text-bedroom | work | sexual_comments, online | clear | online, sexual_comments | yes |
| ny-diversity-hire-hair | work | race_origin, sex_based, appearance | clear | appearance, bullying, race_origin, sex_based | yes |
| ny-weekend-shifts-worth-his-while | work | touching, advances, conditions | clear | advances, conditions, isolation, sexual_comments, touching | yes |
| ny-boss-close-touching-trapped | work | touching | clear | after_no, isolation, touching | yes |
| ny-nanny-touched-then-trashed-online | work | touching, retaliation, online | clear | bullying, isolation, online, retaliation, touching | yes |
| ny-deadnaming-coworker | work | lgbtq | clear | after_no, lgbtq | yes |
| ny-ex-manager-wont-accept-breakup | work | after_no, advances | clear | advances, after_no, isolation | yes |
| ny-mr-mom-left-out | work | pregnancy, isolation, sex_based | error | – | ✗ |
| ny-woman-equipment-operator-toolbox | work | sex_based, threats | error | – | ✗ |
| ny-jewelry-office-boy-orientation | work | sex_based, appearance, lgbtq, retaliation | clear | appearance, bullying, conditions, lgbtq, retaliation, sex_based | yes |
| eeoc-wetback-accent-mocked | work | race_origin | clear | race_origin | yes |
| eeoc-pregnant-heifer | work | pregnancy | clear | appearance, bullying, pregnancy | yes |
| eeoc-wife-scissors-emoji | work | lgbtq, sexual_comments, online | clear | lgbtq, online, sexual_comments | yes |
| eeoc-senior-moments-granny | work | age | clear | age | yes |
| eeoc-stutter-mocked | work | disability | clear | bullying, disability | yes |
| eeoc-wrong-spiritual-path | work | religion | clear | after_no, religion | yes |
| eeoc-ex-posted-explicit-images | work | online, threats | error | – | ✗ |
| eeoc-black-company-coffee | work | race_origin, isolation | clear | bullying, race_origin | yes |
| eeoc-youth-ride-home-schedule | work | appearance, advances, conditions | error | – | ✗ |
| sb-false-accusation-pileon | school | online, bullying | clear | after_no, bullying, online | yes |
| sb-disability-told-to-die | school | online, disability, threats | error | – | ✗ |
| sb-fake-profile-shared-secrets | school | online, bullying | clear | bullying, online | yes |
| sb-gay-death-threats | online | lgbtq, threats, online | clear | bullying, lgbtq, online, threats | yes |
| sb-gaming-forum-doxing | online | online, threats | clear | online, threats | yes |

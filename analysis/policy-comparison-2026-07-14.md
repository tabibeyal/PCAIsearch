# Deep-dive retrieval policy comparison

Generated: 2026-07-14

This asset compares the source lists that three candidate retrieval policies would feed to the deep-dive answer flow. All runs use the canon-only path (`exclude_commentary=True`) and the same six nikāyas selected, matching the reproduced scenario from issue #99.

- **round_robin** — status quo: one result per selected nikāya in turn.
- **global_best** — pure rerank order across the selected nikāyas; no representation guarantee.
- **relevance_floor:X.XX** — round-robin, but a nikāya only contributes chunks whose raw rerank score is at least `X.XX` times the best score in the candidate set.

The *Match %* column is the rank-normalized score the UI would display for that result set. The *Gist* is the first ~120 characters of the retrieved passage; judge on-topic/off-topic manually from the gist and title.

## Query: What did the Buddha say about anger?

Selected nikāyas: DN, MN, SN, AN, DHP, ITI

### round_robin (10 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | DN 33:327 | DN | Saṅgīti Sutta The Discourse for Reciting Together | 74.4% | • “Eight grounds for the arousal of energy: There is the case, friends, where a monk has some work to do. The thought o… |
| 2 | MN 12:7 | MN | Mahāsīhanāda Sutta The Great Lion’s Roar Discourse | 74.2% | “Sāriputta, this worthless man Sunakkhatta is angry. Out of anger, he has made this statement, (thinking,) ‘I will spea… |
| 3 | SN 12.46:4 | SN | Aññatara Sutta A Certain Brahman | 86.8% | [The Buddha:] “(To say,) ‘The one who acts is the same one who experiences,’ is one extreme.” |
| 4 | AN 10.75:23 | AN | Migāsālāya Sutta About Migāsālā | 69.0% | [8] “But then, Ānanda, there is the case where one individual is angry and yet he discerns, as it has come to be, the a… |
| 5 | DHP 17:2 | DHP |  VII : Anger | 50.0% | VII : Anger |
| 6 | ITI 4:3 | ITI |  Itivuttaka | 99.0% | This was said by the Blessed One, said by the Arahant, so I have heard: “Abandon one quality, monks, and I guarantee yo… |
| 7 | DN 33:328 | DN | Saṅgīti Sutta The Discourse for Reciting Together | 66.3% | “Then there is the case where a monk has done some work. The thought occurs to him: ‘I have done some work. While I was… |
| 8 | MN 86:18 | MN | Aṅgulimāla Sutta About Aṅgulimāla | 63.4% | The Buddha: |
| 9 | SN 12.46:6 | SN | Aññatara Sutta A Certain Brahman | 76.6% | [The Buddha:] “(To say,) ‘The one who acts is someone other than the one who experiences,’ is the second extreme. Avoid… |
| 10 | AN 8.30:30 | AN | Anuruddha Sutta To Anuruddha | 54.0% | The Buddha, |

### global_best (10 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | ITI 4:3 | ITI |  Itivuttaka | 99.0% | This was said by the Blessed One, said by the Arahant, so I have heard: “Abandon one quality, monks, and I guarantee yo… |
| 2 | ITI 10:3 | ITI | 10 13 Itivuttaka | 93.5% | This was said by the Blessed One, said by the Arahant, so I have heard: “Monks, one who has not fully known & fully und… |
| 3 | SN 12.46:4 | SN | Aññatara Sutta A Certain Brahman | 82.2% | [The Buddha:] “(To say,) ‘The one who acts is the same one who experiences,’ is one extreme.” |
| 4 | SN 12.46:6 | SN | Aññatara Sutta A Certain Brahman | 68.1% | [The Buddha:] “(To say,) ‘The one who acts is someone other than the one who experiences,’ is the second extreme. Avoid… |
| 5 | DN 33:327 | DN | Saṅgīti Sutta The Discourse for Reciting Together | 65.1% | • “Eight grounds for the arousal of energy: There is the case, friends, where a monk has some work to do. The thought o… |
| 6 | MN 12:7 | MN | Mahāsīhanāda Sutta The Great Lion’s Roar Discourse | 64.8% | “Sāriputta, this worthless man Sunakkhatta is angry. Out of anger, he has made this statement, (thinking,) ‘I will spea… |
| 7 | AN 10.75:23 | AN | Migāsālāya Sutta About Migāsālā | 57.7% | [8] “But then, Ānanda, there is the case where one individual is angry and yet he discerns, as it has come to be, the a… |
| 8 | DN 33:328 | DN | Saṅgīti Sutta The Discourse for Reciting Together | 53.9% | “Then there is the case where a monk has done some work. The thought occurs to him: ‘I have done some work. While I was… |
| 9 | DN 34:191 | DN | Dasuttara Sutta Progressing by Tens | 53.9% | “Then there is the case where a monk has done some work. The thought occurs to him: ‘I have done some work. While I was… |
| 10 | MN 86:18 | MN | Aṅgulimāla Sutta About Aṅgulimāla | 50.0% | The Buddha: |

### relevance_floor:0.60 (1 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | ITI 4:3 | ITI |  Itivuttaka | 99.0% | This was said by the Blessed One, said by the Arahant, so I have heard: “Abandon one quality, monks, and I guarantee yo… |

### relevance_floor:0.75 (1 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | ITI 4:3 | ITI |  Itivuttaka | 99.0% | This was said by the Blessed One, said by the Arahant, so I have heard: “Abandon one quality, monks, and I guarantee yo… |

### relevance_floor:0.90 (1 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | ITI 4:3 | ITI |  Itivuttaka | 99.0% | This was said by the Blessed One, said by the Arahant, so I have heard: “Abandon one quality, monks, and I guarantee yo… |

## Query: How does one develop mindfulness in meditation?

Selected nikāyas: DN, MN, SN, AN, DHP, ITI

### round_robin (10 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | DN 22:118 | DN | Mahā Satipaṭṭhāna Sutta The Great Establishing of Mindfulness Discourse | 84.2% | “Let alone half a month. If anyone would develop these four establishings of mindfulness in this way for seven days, on… |
| 2 | MN 62:26 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 99.0% | “Develop the meditation of mindfulness of in-&-out breathing. Mindfulness of in-&-out breathing, when developed & pursu… |
| 3 | SN 35.206:21 | SN | Chappāṇa Sutta The Six Animals | 96.0% | “Thus you should train yourselves: ‘We will develop mindfulness immersed in the body. We will pursue it, give it a mean… |
| 4 | AN 6.19:15 | AN | Maraṇassati Sutta Mindfulness of Death (1) | 86.4% | Then another monk addressed the Blessed One, “I, too, develop mindfulness of death.”… “I think, ‘O, that I might live f… |
| 5 | DHP 21:6 | DHP |  XI : Miscellany | 50.0% | But for those who are well-applied, constantly, to mindfulness immersed in the body; don’t indulge in what shouldn’t be… |
| 6 | ITI 27:7 | ITI |  Itivuttaka | 62.4% | When one develops–mindful– |
| 7 | DN 33:148 | DN | Saṅgīti Sutta The Discourse for Reciting Together | 84.2% | “And which is the exertion to develop? There is the case where a monk develops mindfulness as a factor for awakening de… |
| 8 | MN 62:19 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 96.3% | “Develop the meditation in tune with space. For when you are developing the meditation in tune with space, agreeable & … |
| 9 | SN 46.26:5 | SN | Khaya Sutta Ending | 89.5% | “There is the case, Udāyin, where a monk develops mindfulness as a factor for awakening dependent on seclusion, depende… |
| 10 | AN 9.63:4 | AN | Sikkhā-dubbalya Sutta Things That Weaken the Training | 83.7% | “To abandon these five things that weaken the training, one should develop the four establishings of mindfulness. Which… |

### global_best (10 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | MN 62:26 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 99.0% | “Develop the meditation of mindfulness of in-&-out breathing. Mindfulness of in-&-out breathing, when developed & pursu… |
| 2 | MN 62:19 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 90.5% | “Develop the meditation in tune with space. For when you are developing the meditation in tune with space, agreeable & … |
| 3 | SN 35.206:21 | SN | Chappāṇa Sutta The Six Animals | 89.5% | “Thus you should train yourselves: ‘We will develop mindfulness immersed in the body. We will pursue it, give it a mean… |
| 4 | MN 62:7 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 89.0% | Ven. Sāriputta saw Ven. Rāhula sitting at the foot of a tree, his legs folded crosswise, his body held erect, & with mi… |
| 5 | MN 62:15 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 82.0% | “Rāhula, develop the meditation in tune with earth. For when you are developing the meditation in tune with earth, agre… |
| 6 | SN 46.26:5 | SN | Khaya Sutta Ending | 68.7% | “There is the case, Udāyin, where a monk develops mindfulness as a factor for awakening dependent on seclusion, depende… |
| 7 | AN 6.19:15 | AN | Maraṇassati Sutta Mindfulness of Death (1) | 58.7% | Then another monk addressed the Blessed One, “I, too, develop mindfulness of death.”… “I think, ‘O, that I might live f… |
| 8 | DN 22:118 | DN | Mahā Satipaṭṭhāna Sutta The Great Establishing of Mindfulness Discourse | 51.7% | “Let alone half a month. If anyone would develop these four establishings of mindfulness in this way for seven days, on… |
| 9 | DN 33:148 | DN | Saṅgīti Sutta The Discourse for Reciting Together | 51.6% | “And which is the exertion to develop? There is the case where a monk develops mindfulness as a factor for awakening de… |
| 10 | AN 9.63:4 | AN | Sikkhā-dubbalya Sutta Things That Weaken the Training | 50.0% | “To abandon these five things that weaken the training, one should develop the four establishings of mindfulness. Which… |

### relevance_floor:0.60 (6 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | MN 62:26 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 99.0% | “Develop the meditation of mindfulness of in-&-out breathing. Mindfulness of in-&-out breathing, when developed & pursu… |
| 2 | SN 35.206:21 | SN | Chappāṇa Sutta The Six Animals | 83.7% | “Thus you should train yourselves: ‘We will develop mindfulness immersed in the body. We will pursue it, give it a mean… |
| 3 | MN 62:19 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 85.3% | “Develop the meditation in tune with space. For when you are developing the meditation in tune with space, agreeable & … |
| 4 | SN 46.26:5 | SN | Khaya Sutta Ending | 50.0% | “There is the case, Udāyin, where a monk develops mindfulness as a factor for awakening dependent on seclusion, depende… |
| 5 | MN 62:7 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 82.9% | Ven. Sāriputta saw Ven. Rāhula sitting at the foot of a tree, his legs folded crosswise, his body held erect, & with mi… |
| 6 | MN 62:15 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 71.6% | “Rāhula, develop the meditation in tune with earth. For when you are developing the meditation in tune with earth, agre… |

### relevance_floor:0.75 (5 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | MN 62:26 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 99.0% | “Develop the meditation of mindfulness of in-&-out breathing. Mindfulness of in-&-out breathing, when developed & pursu… |
| 2 | SN 35.206:21 | SN | Chappāṇa Sutta The Six Animals | 71.6% | “Thus you should train yourselves: ‘We will develop mindfulness immersed in the body. We will pursue it, give it a mean… |
| 3 | MN 62:19 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 74.5% | “Develop the meditation in tune with space. For when you are developing the meditation in tune with space, agreeable & … |
| 4 | MN 62:7 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 70.2% | Ven. Sāriputta saw Ven. Rāhula sitting at the foot of a tree, his legs folded crosswise, his body held erect, & with mi… |
| 5 | MN 62:15 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 50.0% | “Rāhula, develop the meditation in tune with earth. For when you are developing the meditation in tune with earth, agre… |

### relevance_floor:0.90 (3 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | MN 62:26 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 99.0% | “Develop the meditation of mindfulness of in-&-out breathing. Mindfulness of in-&-out breathing, when developed & pursu… |
| 2 | SN 35.206:21 | SN | Chappāṇa Sutta The Six Animals | 50.0% | “Thus you should train yourselves: ‘We will develop mindfulness immersed in the body. We will pursue it, give it a mean… |
| 3 | MN 62:19 | MN | Mahā Rāhulovāda Sutta The Greater Exhortation to Rāhula | 55.1% | “Develop the meditation in tune with space. For when you are developing the meditation in tune with space, agreeable & … |

## Query: What is the middle way between indulgence and asceticism?

Selected nikāyas: DN, MN, SN, AN, DHP, ITI

### round_robin (10 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | DN 1:300 | DN | Brahmajāla Sutta The Brahmā Net | 56.0% | 59. “Another says to him, ‘There is, my good man, that self of which you speak. I don’t say that there’s not. But it’s … |
| 2 | MN 12:76 | MN | Mahāsīhanāda Sutta The Great Lion’s Roar Discourse | 53.4% | “Thus in a variety of ways I stayed devoted to the practice of tormenting & torturing the body. That’s how it was for m… |
| 3 | SN 56.11:5 | SN | Dhammacakkappavattana Sutta Setting the Wheel of Dhamma in Motion | 99.0% | “There are these two extremes that are not to be indulged in by one who has gone forth. Which two? That which is devote… |
| 4 | AN 3.33:8 | AN | Sāriputta Sutta To Sāriputta | 52.8% | both of sensual desires, |
| 5 | DHP 2:9 | DHP |  I : Heedfulness | 54.3% | Don’t give way to heedlessness or to intimacy with sensual delight– for a heedful person, absorbed in jhana, attains an… |
| 6 | ITI 95:13 | ITI |  Itivuttaka | 54.0% | in sensual pleasures, the wise |
| 7 | DN 29:48 | DN | Pāsādika Sutta The Inspiring Discourse | 55.8% | “These are the four devotions to pleasure, Cunda, that are base, vulgar, common, ignoble, unprofitable, that do not lea… |
| 8 | MN 101:104 | MN | Devadaha Sutta At Devadaha | 50.0% | “Having abandoned these five hindrances—imperfections of awareness that weaken discernment—then, quite secluded from se… |
| 9 | SN 12.18:17 | SN | Timbarukkha Sutta To Timbarukkha | 68.9% | “Timbarukkha, I don’t say that—with the feeling being the same as the one who feels, existing from the beginning—pleasu… |
| 10 | AN 3.35:21 | AN | Hatthaka Sutta To Hatthaka | 52.7% | to sensual pleasures, |

### global_best (10 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | SN 56.11:5 | SN | Dhammacakkappavattana Sutta Setting the Wheel of Dhamma in Motion | 99.0% | “There are these two extremes that are not to be indulged in by one who has gone forth. Which two? That which is devote… |
| 2 | SN 12.18:17 | SN | Timbarukkha Sutta To Timbarukkha | 64.9% | “Timbarukkha, I don’t say that—with the feeling being the same as the one who feels, existing from the beginning—pleasu… |
| 3 | SN 12.15:7 | SN | Kaccānagotta Sutta To Kaccāna Gotta | 60.4% | “‘Everything exists’: That is one extreme. ‘Everything doesn’t exist’: That is a second extreme. Avoiding these two ext… |
| 4 | SN 22.90:13 | SN | Channa Sutta To Channa | 59.9% | “‘“Everything exists”: That is one extreme. “Everything doesn’t exist”: That is a second extreme. Avoiding these two ex… |
| 5 | SN 12.46:6 | SN | Aññatara Sutta A Certain Brahman | 57.9% | [The Buddha:] “(To say,) ‘The one who acts is someone other than the one who experiences,’ is the second extreme. Avoid… |
| 6 | SN 12.17:22 | SN | Acela Sutta To the Clothless Ascetic | 57.3% | “Kassapa, the statement, ‘With the one who acts being the same as the one who experiences, existing from the beginning,… |
| 7 | SN 12.48:11 | SN | Lokāyatika Sutta The Cosmologist | 56.2% | “‘Everything is a plurality is the fourth form of cosmology, brahman. Avoiding these two extremes, the Tathāgata teache… |
| 8 | SN 56.11:6 | SN | Dhammacakkappavattana Sutta Setting the Wheel of Dhamma in Motion | 52.9% | “And what is the middle way realized by the Tathāgata that—producing vision, producing knowledge—leads to stilling, to … |
| 9 | DN 1:300 | DN | Brahmajāla Sutta The Brahmā Net | 50.2% | 59. “Another says to him, ‘There is, my good man, that self of which you speak. I don’t say that there’s not. But it’s … |
| 10 | DN 29:48 | DN | Pāsādika Sutta The Inspiring Discourse | 50.0% | “These are the four devotions to pleasure, Cunda, that are base, vulgar, common, ignoble, unprofitable, that do not lea… |

### relevance_floor:0.60 (1 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | SN 56.11:5 | SN | Dhammacakkappavattana Sutta Setting the Wheel of Dhamma in Motion | 99.0% | “There are these two extremes that are not to be indulged in by one who has gone forth. Which two? That which is devote… |

### relevance_floor:0.75 (1 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | SN 56.11:5 | SN | Dhammacakkappavattana Sutta Setting the Wheel of Dhamma in Motion | 99.0% | “There are these two extremes that are not to be indulged in by one who has gone forth. Which two? That which is devote… |

### relevance_floor:0.90 (1 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | SN 56.11:5 | SN | Dhammacakkappavattana Sutta Setting the Wheel of Dhamma in Motion | 99.0% | “There are these two extremes that are not to be indulged in by one who has gone forth. Which two? That which is devote… |

## Query: What happens after death according to the Buddha?

Selected nikāyas: DN, MN, SN, AN, DHP, ITI

### round_robin (10 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | DN 16:518 | DN | Mahā Parinibbāna Sutta The Great Total Unbinding Discourse | 99.0% | “And for what reason is a Private Buddha worthy of a burial mound? (At the thought,) ‘This is the burial mound of a Pri… |
| 2 | MN 41:6 | MN | Sāleyyaka Sutta (Brahmans) of Sāla | 63.7% | As they were sitting there, the brahman householders of Sāla said to the Blessed One, “What is the reason, Master Gotam… |
| 3 | SN 22.86:5 | SN | Anurādha Sutta To Anurādha | 64.4% | When this was said, Ven. Anurādha said to the wandering sectarians, “Friends, the Tathāgata—the supreme man, the superl… |
| 4 | AN 3.66:56 | AN | Kālāma Sutta To the Kālāmas | 66.6% | “‘If there is a world after death, if there is the fruit & result of actions rightly & wrongly done, then this is the b… |
| 5 | DHP 22:3 | DHP |  XII : Hell | 50.0% | He goes to hell, the one who asserts what didn’t take place, as does the one who, having done, says, ‘I didn’t.’ Both–l… |
| 6 | ITI 106:21 | ITI |  Itivuttaka | 64.1% | and after death |
| 7 | DN 29:91 | DN | Pāsādika Sutta The Inspiring Discourse | 60.2% | “There are certain contemplatives & brahmans who are of this view, this opinion, ‘After death, the self is possessed of… |
| 8 | MN 135:9 | MN | Cūḷa Kamma-vibhaṅga Sutta The Shorter Analysis of Action | 53.9% | “But then there is the case where a woman or man, having abandoned the killing of living beings, abstains from killing … |
| 9 | SN 44.3:16 | SN | Sāriputta-Koṭṭhita Sutta Sāriputta and Koṭṭhita (1) | 57.7% | “‘The Tathāgata exists after death’ is immersed in consciousness. ‘The Tathāgata does not exist after death’ is immerse… |
| 10 | AN 3.66:62 | AN | Kālāma Sutta To the Kālāmas | 66.6% | “‘If there is a world after death, if there is the fruit & result of actions rightly & wrongly done, then this is the b… |

### global_best (10 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | DN 16:518 | DN | Mahā Parinibbāna Sutta The Great Total Unbinding Discourse | 99.0% | “And for what reason is a Private Buddha worthy of a burial mound? (At the thought,) ‘This is the burial mound of a Pri… |
| 2 | AN 3.66:56 | AN | Kālāma Sutta To the Kālāmas | 61.8% | “‘If there is a world after death, if there is the fruit & result of actions rightly & wrongly done, then this is the b… |
| 3 | AN 3.66:62 | AN | Kālāma Sutta To the Kālāmas | 61.8% | “‘If there is a world after death, if there is the fruit & result of actions rightly & wrongly done, then this is the b… |
| 4 | SN 22.86:5 | SN | Anurādha Sutta To Anurādha | 59.3% | When this was said, Ven. Anurādha said to the wandering sectarians, “Friends, the Tathāgata—the supreme man, the superl… |
| 5 | ITI 106:21 | ITI |  Itivuttaka | 59.0% | and after death |
| 6 | MN 41:6 | MN | Sāleyyaka Sutta (Brahmans) of Sāla | 58.5% | As they were sitting there, the brahman householders of Sāla said to the Blessed One, “What is the reason, Master Gotam… |
| 7 | DN 29:91 | DN | Pāsādika Sutta The Inspiring Discourse | 54.5% | “There are certain contemplatives & brahmans who are of this view, this opinion, ‘After death, the self is possessed of… |
| 8 | ITI 41:3 | ITI |  Itivuttaka | 53.4% | This was said by the Blessed One, said by the Arahant, so I have heard: “Monks, those beings are truly deprived who are… |
| 9 | SN 44.3:16 | SN | Sāriputta-Koṭṭhita Sutta Sāriputta and Koṭṭhita (1) | 51.6% | “‘The Tathāgata exists after death’ is immersed in consciousness. ‘The Tathāgata does not exist after death’ is immerse… |
| 10 | SN 44.11:11 | SN | Sabhiya Sutta With Sabhiya | 50.0% | “Now, Master Kaccāna, when asked if the Tathāgata exists after death, you say, ‘That has not been declared by the Bless… |

### relevance_floor:0.60 (1 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | DN 16:518 | DN | Mahā Parinibbāna Sutta The Great Total Unbinding Discourse | 99.0% | “And for what reason is a Private Buddha worthy of a burial mound? (At the thought,) ‘This is the burial mound of a Pri… |

### relevance_floor:0.75 (1 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | DN 16:518 | DN | Mahā Parinibbāna Sutta The Great Total Unbinding Discourse | 99.0% | “And for what reason is a Private Buddha worthy of a burial mound? (At the thought,) ‘This is the burial mound of a Pri… |

### relevance_floor:0.90 (1 sources)

| # | Sutta ID | Nikāya | Title | Match % | Gist |
|---|----------|--------|-------|--------:|------|
| 1 | DN 16:518 | DN | Mahā Parinibbāna Sutta The Great Total Unbinding Discourse | 99.0% | “And for what reason is a Private Buddha worthy of a burial mound? (At the thought,) ‘This is the burial mound of a Pri… |

## How to reproduce

```bash
PYTHONPATH=. NVIDIA_API_KEY=... QDRANT_URL=... QDRANT_API_KEY=... \
    python3 scripts/compare_policies.py
```

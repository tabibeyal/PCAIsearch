from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DictionaryEntry:
    label: str
    keywords: List[str]
    pali: str
    english_hint: Optional[str] = None


_ENTRIES: List[DictionaryEntry] = [
    DictionaryEntry(
        label="Dependent Origination (full chain)",
        keywords=[
            "dependent origination", "dependent arising", "conditioned arising",
            "how does ignorance cause", "ignorance cause suffering",
            "twelve links", "12 links", "chain of causation",
            "interdependent arising", "step by step suffering",
            "deepest origin", "root cause of suffering", "fundamental cause",
        ],
        pali="paṭicca-samuppāda avijjā saṅkhārā viññāṇa nāmarūpa salāyatana phassa vedanā taṇhā upādāna bhava jāti jarāmaraṇa",
        english_hint="with ignorance as condition volitional formations arise with formations as condition consciousness with consciousness name-and-form",
    ),
    DictionaryEntry(
        label="Kālāma Sutta / epistemology",
        keywords=[
            "kālāma", "kalama", "how to know", "whether a teaching is worth",
            "whether a religious teaching", "test a teaching", "religious teaching worth following",
            "don't follow tradition", "anussava", "not by hearsay",
            "how do you judge", "criteria for truth", "verify teaching",
        ],
        pali="kālāmā anussava parampara itikirā piṭakasampadā takkahetu nayahetu",
        english_hint="do not go by oral tradition lineage of teaching hearsay collection of texts logic inferential reasoning acceptance of a view pondering teacher",
    ),
    DictionaryEntry(
        label="Four Noble Truths",
        keywords=["four noble truths", "noble truth", "truth of suffering", "four truths"],
        pali="cattāri ariyasaccāni dukkha samudaya nirodha magga",
    ),
    DictionaryEntry(
        label="Suffering / dukkha",
        keywords=["suffering", "unsatisfactoriness", "cause of suffering", "origin of suffering"],
        pali="dukkha samudaya taṇhā upādāna bhava",
    ),
    DictionaryEntry(
        label="Ignorance / avijjā",
        keywords=["ignorance", "not knowing", "fundamental ignorance", "avijja"],
        pali="avijjā vijjā paṭicca-samuppāda mūla",
    ),
    DictionaryEntry(
        label="Noble Eightfold Path",
        keywords=[
            "eightfold path", "eight fold path", "noble eightfold",
            "path factors", "right view", "right intention", "right speech",
            "right action", "right livelihood", "right effort",
            "right mindfulness", "right concentration",
        ],
        pali="ariyo aṭṭhaṅgiko maggo sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi",
    ),
    DictionaryEntry(
        label="Five Aggregates",
        keywords=[
            "five aggregates", "five skandhas", "aggregates of clinging",
            "form feeling perception", "aggregates permanent", "lack a self",
            "khandha", "self in the aggregates", "no self in aggregates",
            "are the aggregates",
        ],
        pali="khandha rūpa vedanā saññā saṅkhārā viññāṇa anicca dukkha anattā",
        english_hint="form is not-self if form were self form would not lead to affliction feeling perception formations consciousness not-self",
    ),
    DictionaryEntry(
        label="Three Marks of Existence",
        keywords=[
            "inconstant", "inconstancy", "impermanent", "impermanence", "three marks", "anicca",
            "not-self", "no self", "anatta", "three characteristics",
            "unsatisfactory nature",
        ],
        pali="tilakkhaṇa anicca dukkha anattā sabbe saṅkhārā vipariṇāma",
    ),
    DictionaryEntry(
        label="Five Precepts",
        keywords=[
            "five precepts", "ethical training", "moral training",
            "precepts householder", "lay precepts", "undertake training",
        ],
        pali="pañcasīla pāṇātipātā adinnādānā kāmesumicchācārā musāvādā surāmeraya sīla",
    ),
    DictionaryEntry(
        label="Precept of truthfulness / lying",
        keywords=[
            "lying", "false speech", "telling the truth",
            "precept never break", "one precept", "truth telling",
            "honesty", "avoid lying", "speak truth",
        ],
        pali="musāvādā sacca ambalatthika-rāhulovāda sīla sammā-vācā",
        english_hint="not ashamed to tell a deliberate lie there is no bad deed they would not do",
    ),
    DictionaryEntry(
        label="Precept of non-killing",
        keywords=[
            "killing", "not killing", "first precept", "taking life",
            "ahimsa", "non-violence", "harm living beings", "abstain from killing",
        ],
        pali="pāṇātipātā ahiṃsā pāṇātipātā-veramaṇī sīla",
    ),
    DictionaryEntry(
        label="Precept of non-stealing",
        keywords=[
            "stealing", "not stealing", "taking what is not given",
            "second precept", "property theft", "refrain from stealing",
        ],
        pali="adinnādānā adinnadāna sīla",
    ),
    DictionaryEntry(
        label="Precept of sexual misconduct",
        keywords=[
            "sexual misconduct", "third precept", "sensual misconduct",
            "refrain from sexual misconduct", "kamesu micchacara",
        ],
        pali="kāmesumicchācārā sīla brahmacariya",
    ),
    DictionaryEntry(
        label="Precept of intoxicants",
        keywords=[
            "intoxicants", "alcohol", "fifth precept", "drink",
            "refrain from intoxicants", "surameraya",
        ],
        pali="surāmeraya majja pamādaṭṭhāna sīla",
    ),
    DictionaryEntry(
        label="Jhāna / absorption",
        keywords=[
            "jhana", "jhāna", "meditative absorption", "four jhanas",
            "first jhana", "second jhana", "third jhana", "fourth jhana",
            "enter jhana", "meditative states",
        ],
        pali="jhāna samādhi vitakka vicāra pīti sukha ekaggatā upekkhā",
    ),
    DictionaryEntry(
        label="Concentration / samādhi",
        keywords=[
            "concentration", "one-pointedness", "mental unification",
            "stillness of mind", "calm abiding", "serenity",
            "unified mind", "collected mind",
        ],
        pali="samādhi samatha cetaso ekodibhāva",
    ),
    DictionaryEntry(
        label="Mindfulness / satipaṭṭhāna",
        keywords=[
            "mindfulness", "four foundations of mindfulness", "satipatthana",
            "contemplation of body", "mindfulness of breathing",
            "breath awareness", "anapanasati", "ānāpānasati",
            "body mind contemplation",
        ],
        pali="satipaṭṭhāna kāyānupassanā vedanānupassanā cittānupassanā dhammānupassanā ānāpānasati",
    ),
    DictionaryEntry(
        label="Brahmavihārās / four immeasurables",
        keywords=[
            "good will", "goodwill", "loving kindness", "lovingkindness", "metta", "compassion",
            "sympathetic joy", "equanimity", "four immeasurables",
            "brahmaviharas", "divine abiding", "radiate goodwill",
            "boundless heart", "immeasurable mind",
        ],
        pali="brahmavihāra mettā karuṇā muditā upekkhā pharaṇa sattā",
    ),
    DictionaryEntry(
        label="Mettā / loving-kindness practice",
        keywords=["metta meditation", "loving kindness meditation", "good will meditation", "goodwill to all"],
        pali="mettā sattā sukhī hontu brahmavihāra pharaṇa",
    ),
    DictionaryEntry(
        label="Saw simile / patience under abuse",
        keywords=[
            "saw", "anger", "attacked with a saw", "sawn limb by limb",
            "patience under attack", "if someone attacks", "should a monk feel anger",
            "monk attacked", "abuse patience", "axe simile",
        ],
        pali="kakacūpama khanti anāghāta abyāpajjha mettā",
    ),
    DictionaryEntry(
        label="Raft simile",
        keywords=[
            "raft", "raft simile", "cross to the other shore",
            "dhamma like a raft", "leave the raft behind",
        ],
        pali="kullūpama dhamma vinaya ogha tīra",
    ),
    DictionaryEntry(
        label="Poison arrow simile",
        keywords=[
            "poison arrow", "poisoned arrow", "arrow in the flesh",
            "metaphysical questions", "undeclared questions", "unanswered",
        ],
        pali="sallena āhata avyākata abyākata diṭṭhi",
    ),
    DictionaryEntry(
        label="Spiritual friendship",
        keywords=[
            "spiritual friend", "good friend", "kalyanamitra", "admirable friend",
            "whole of the holy life", "half the holy life", "noble friend",
            "spiritual companionship",
        ],
        pali="kalyāṇamittā kalyāṇasahāya kalyāṇasampavaṅka brahmacariya",
    ),
    DictionaryEntry(
        label="Middle Way",
        keywords=[
            "middle way", "middle path", "neither too tight nor too loose",
            "lute strings", "extreme", "asceticism and sensual pleasure",
            "avoid extremes", "moderate path",
        ],
        pali="majjhimā paṭipadā atitta atilīna soṇa vīṇā",
    ),
    DictionaryEntry(
        label="First Sermon / Dhammacakkappavattana",
        keywords=[
            "first discourse", "first sermon", "setting in motion",
            "wheel of dhamma", "wheel of the dhamma", "deer park",
            "isipatana", "five ascetics", "first teaching",
        ],
        pali="dhammacakkappavattana isipatana migadāya pañcavaggiyā",
    ),
    DictionaryEntry(
        label="Sigālovāda / householder ethics",
        keywords=[
            "parents", "treat parents", "honour parents",
            "family", "husband wife", "sigala", "sigalovada",
            "householder ethics", "how should one treat",
            "obligations to family", "respect parents", "six directions",
        ],
        pali="sigālovāda mātāpitaro disa ācariya putta dāra mitta",
    ),
    DictionaryEntry(
        label="Death / maraṇānussati",
        keywords=[
            "death", "dying", "mortality", "old age death",
            "born to die", "recollection of death", "maranasati",
            "contemplation of death",
        ],
        pali="maraṇa jarā jāti maraṇānussati anicca",
    ),
    DictionaryEntry(
        label="Buddha's hesitation to teach / decision to teach",
        keywords=[
            "after enlightenment", "decide to teach", "hesitation to teach",
            "before deciding to teach", "consider after enlightenment",
            "who would understand", "reluctant to teach", "brahma asked buddha",
            "deep dhamma hard to teach",
        ],
        pali="nibbāna vimutti asaṅkhata gambhīra paṭicca-samuppāda",
        english_hint="deep hard to see hard to realize peaceful subtle against the stream this generation delights in attachment Brahma Sahampati teach",
    ),
    DictionaryEntry(
        label="Nibbāna / liberation",
        keywords=[
            "nibbana", "nirvana", "awakening", "enlightenment",
            "freedom from suffering", "cessation", "unbinding",
            "liberation", "deathless", "unconditioned",
        ],
        pali="nibbāna vimutti vimokkha sacchikiriyā asaṅkhata",
    ),
    DictionaryEntry(
        label="Wisdom / insight",
        keywords=[
            "wisdom", "insight", "discernment", "clear seeing",
            "true knowledge", "seeing things as they are",
        ],
        pali="paññā vijjā ñāṇa dassana yathābhūta",
    ),
    DictionaryEntry(
        label="Kamma / rebirth",
        keywords=[
            "rebirth", "reincarnation", "kamma", "karma",
            "action and result", "intention", "future lives", "next life",
            "volitional action",
        ],
        pali="kamma cetanā vipāka punabbhava saṃsāra",
    ),
    DictionaryEntry(
        label="Three Jewels / Refuges",
        keywords=[
            "three jewels", "three refuges", "buddha dharma sangha",
            "take refuge", "going for refuge", "tiratana",
            "refuge in the buddha",
        ],
        pali="tiratana buddha dhamma saṅgha saraṇa",
    ),
    DictionaryEntry(
        label="Stages of awakening",
        keywords=[
            "stream entry", "stream-entry", "once returner",
            "non-returner", "arahant", "stages of awakening",
            "four stages", "sotapanna", "sakadagami", "anagami",
            "stream enterer",
        ],
        pali="sotāpanna sakadāgāmī anāgāmī arahant ariya magga phala",
    ),
    DictionaryEntry(
        label="Fetters / ten fetters",
        keywords=[
            "fetter", "ten fetters", "mental fetters", "bonds",
            "what binds us", "ten bonds", "overcome fetters",
        ],
        pali="saṃyojana sakkāyadiṭṭhi vicikicchā sīlabbataparāmāsa kāmarāga paṭigha",
    ),
    DictionaryEntry(
        label="Five hindrances",
        keywords=[
            "five hindrances", "mental hindrances", "hindrance", "nīvaraṇa",
            "sloth torpor", "restlessness worry", "sensual desire",
            "ill will", "doubt as hindrance",
        ],
        pali="nīvaraṇa kāmacchanda vyāpāda thīnamiddha uddhacca-kukkucca vicikicchā",
    ),
    DictionaryEntry(
        label="Defilements / kilesa",
        keywords=[
            "defilement", "defilements", "kilesa", "mental defilement",
            "unwholesome", "roots of unwholesomeness", "greed hate delusion",
            "lobha dosa moha",
        ],
        pali="kilesa lobha dosa moha rāga byāpāda avijjā",
    ),
    DictionaryEntry(
        label="Sense restraint",
        keywords=[
            "sense restraint", "guarding sense doors", "sense control",
            "restrain senses", "eye ear nose tongue body mind",
            "guard the senses", "sense faculties",
        ],
        pali="indriyasaṃvara cakkhu sota ghāna jivhā kāya mano",
    ),
    DictionaryEntry(
        label="Vipassanā / insight",
        keywords=[
            "vipassana", "vipassanā", "insight meditation",
            "insight into impermanence", "dry insight", "bare insight",
        ],
        pali="vipassanā aniccānupassanā dukkhānupassanā anattānupassanā",
    ),
    DictionaryEntry(
        label="Not-self / anattā",
        keywords=[
            "not-self", "not self", "no self", "anatta", "anattā", "anata",
            "what is the self", "is there a self", "self and non-self",
        ],
        pali="anattā sabbe dhammā anattā khandha ahaṃkāra",
    ),
    DictionaryEntry(
        label="Cessation of dependent origination",
        keywords=[
            "cessation of suffering", "end of suffering", "how suffering ends",
            "nirodha", "cessation of dependent origination",
        ],
        pali="nirodha paṭicca-samuppāda-nirodha taṇhā-nirodha nibbāna",
    ),
    DictionaryEntry(
        label="Right effort / four great efforts",
        keywords=[
            "right effort", "four great efforts", "four right efforts",
            "abandon unwholesome", "cultivate wholesome", "viriya",
            "energy in practice",
        ],
        pali="sammappadhāna viriya āraddhaviriya padhāna",
    ),
    DictionaryEntry(
        label="Ethical conduct / sīla",
        keywords=[
            "ethical conduct", "sila", "moral conduct", "virtue",
            "training in ethics", "ethical behaviour",
        ],
        pali="sīla pārisuddhisīla ājīvapārisuddhisīla",
    ),
    DictionaryEntry(
        label="Monastic rules / Vinaya",
        keywords=[
            "monk rules", "monastic discipline", "vinaya", "monks and nuns",
            "rules of training", "patimokkha", "monastic code",
            "monks precepts", "bhikkhu rules",
        ],
        pali="vinaya pātimokkha bhikkhu bhikkhunī sikkhāpada",
    ),
    DictionaryEntry(
        label="Saṅgha / community",
        keywords=[
            "community of monks", "sangha", "saṅgha", "monastic community",
            "fourfold sangha", "bhikkhu sangha",
        ],
        pali="saṅgha bhikkhu bhikkhunī upāsaka upāsikā cātuddisa",
    ),
    DictionaryEntry(
        label="Four nutriments",
        keywords=[
            "four nutriments", "four foods", "nutriment", "food for consciousness",
            "contact as nutriment", "mental volition as nutriment",
        ],
        pali="āhāra kabaḷīkāra phassāhāra manosañcetanāhāra viññāṇāhāra",
    ),
    DictionaryEntry(
        label="Realms of existence",
        keywords=[
            "realms", "six realms", "heavenly realm", "hell realm",
            "deva", "brahma", "realm of beings", "planes of existence",
        ],
        pali="loka sugati duggati deva brahmaloka niraya tiracchāna",
    ),
    DictionaryEntry(
        label="Six recollections",
        keywords=[
            "recollection", "six recollections", "recollection of the buddha",
            "recollection of dhamma", "recollection of sangha",
            "anussati", "buddhānussati",
        ],
        pali="anussati buddhānussati dhammānussati saṅghānussati sīlānussati cāgānussati devatānussati",
    ),
    DictionaryEntry(
        label="Faith / saddhā",
        keywords=[
            "faith", "confidence", "trust in the dhamma",
            "faith in the buddha", "saddhā", "verified confidence",
        ],
        pali="saddhā saddahati aveccappasāda",
    ),
    DictionaryEntry(
        label="Conditioned things / saṅkhārā",
        keywords=[
            "conditioned things", "conditioned phenomena", "formations",
            "mental formations", "sankharas", "fabrications",
        ],
        pali="saṅkhārā sabbe saṅkhārā aniccā paṭicca-samuppāda",
    ),
    DictionaryEntry(
        label="Mind / citta",
        keywords=[
            "mind", "purification of mind", "training the mind",
            "taming the mind", "mind is the forerunner", "manopubbaṅgamā",
        ],
        pali="citta mano manopubbaṅgamā manomaya cetovimutti",
    ),
    DictionaryEntry(
        label="Mettāsutta",
        keywords=[
            "metta sutta", "mettasutta", "karaṇīya", "loving-kindness sutta",
            "as a mother guards her only child",
        ],
        pali="karaṇīyamettā mātā yathā niyaṃ puttaṃ āyusā ekaputtamanurakkhe",
    ),
    DictionaryEntry(
        label="Feeling tone / vedanā",
        keywords=[
            "feeling tone", "vedana", "pleasant feeling", "painful feeling",
            "neutral feeling", "three feelings", "types of feeling",
        ],
        pali="vedanā sukha dukkha adukkhamasukha",
    ),
    DictionaryEntry(
        label="Craving / addiction / compulsion",
        keywords=[
            "addiction", "addicted", "overcome addiction", "compulsion",
            "obsession", "overcome craving", "uncontrollable desire",
            "enslaved by desire", "consumed by desire", "hooked on",
            "can't stop", "intoxication", "bondage to desire",
            "mental ferment", "ferments", "āsava", "asava",
        ],
        pali="taṇhā rāga āsava nīvaraṇa kāmacchanda upādāna",
        english_hint="consumed by craving overwhelmed by desire not freed from ferment taint sensual pleasure clinging overcome",
    ),
]


def lookup(query: str) -> Optional[str]:
    q = query.lower()
    for entry in _ENTRIES:
        if any(kw in q for kw in entry.keywords):
            return entry.pali
    return None


def lookup_english(query: str) -> Optional[str]:
    q = query.lower()
    for entry in _ENTRIES:
        if any(kw in q for kw in entry.keywords):
            return entry.english_hint
    return None

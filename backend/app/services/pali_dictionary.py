import re
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
            "dependent origination", "dependent arising", "conditioned arising", "paticca-samuppada", "paṭicca-samuppāda",
            "twelve links", "12 links", "twelve nidanas", "chain of causation",
            "interdependent arising", "how does ignorance cause", "root cause of suffering",
            "ignorance", "avijja", "avijjā",
            "fabrications link", "formations link", "sankhara link",
            "name-and-form", "nama-rupa", "nāmarūpa",
            "six sense media", "six sense bases", "salayatana", "saḷāyatana",
            "contact", "phassa",
            "craving link", "tanha link", "taṇhā link",
            "clinging", "upadana", "upādāna",
            "becoming", "bhava",
            "birth", "jati", "jāti",
            "aging and death", "aging-and-death", "jaramarana", "jarāmaraṇa",
        ],
        pali="paṭicca-samuppāda avijjā saṅkhārā viññāṇa nāmarūpa salāyatana phassa vedanā taṇhā upādāna bhava jāti jarāmaraṇa",
        english_hint="with ignorance as condition fabrications arise with fabrications consciousness name-and-form six sense media contact feeling craving clinging becoming birth aging-and-death",
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
        keywords=[
            "four noble truths", "noble truth", "four truths", "ariyasaccani", "cattāri ariyasaccāni",
            "truth of stress", "truth of suffering", "noble truth of stress",
            "origination of stress", "origin of suffering", "samudaya", "arising of craving",
            "cessation of stress", "cessation of suffering", "nirodha", "unbinding",
            "path of practice", "path leading to cessation", "magga ariyasacca",
        ],
        pali="cattāri ariyasaccāni dukkha samudaya nirodha magga",
        english_hint="noble truth stress suffering origination cessation path of practice craving clinging becoming birth aging death sorrow lamentation pain grief despair",
    ),
    DictionaryEntry(
        label="Suffering / dukkha",
        keywords=["stress", "suffering", "unsatisfactoriness", "cause of suffering", "origin of suffering", "cause of stress", "dukkha"],
        pali="dukkha samudaya taṇhā upādāna bhava",
        english_hint="birth is suffering aging is suffering death is suffering sorrow lamentation pain grief despair not getting what one wants is suffering the five aggregates of clinging are suffering",
    ),
    DictionaryEntry(
        label="Ignorance / avijjā",
        keywords=["ignorance", "not knowing", "fundamental ignorance", "avijja"],
        pali="avijjā vijjā paṭicca-samuppāda mūla",
    ),
    DictionaryEntry(
        label="Noble Eightfold Path",
        keywords=[
            "eightfold path", "eight fold path", "noble eightfold", "path factors", "ariya magga", "atthangika",
            "right view", "samma-ditthi", "sammā-diṭṭhi",
            "right resolve", "right intention", "samma-sankappa", "sammā-saṅkappa",
            "right speech", "samma-vaca", "sammā-vācā",
            "right action", "samma-kammanta", "sammā-kammanta",
            "right livelihood", "samma-ajiva", "sammā-ājīva",
            "right effort", "samma-vayama", "sammā-vāyāma",
            "right mindfulness", "samma-sati", "sammā-sati",
            "right concentration", "samma-samadhi", "sammā-samādhi",
        ],
        pali="ariyo aṭṭhaṅgiko maggo sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi",
        english_hint="right view right resolve right speech right action right livelihood right effort right mindfulness right concentration noble eightfold path",
    ),
    DictionaryEntry(
        label="Five Aggregates",
        keywords=[
            "five aggregates", "five skandhas", "aggregates of clinging",
            "khandha", "self in the aggregates", "no self in aggregates",
            "are the aggregates", "lack a self",
            "form", "rupa", "rūpa",
            "feeling", "vedana", "vedanā",
            "perception aggregate", "sanna", "saññā",
            "fabrications", "formations", "mental formations", "sankhara", "saṅkhāra",
            "consciousness aggregate", "vinnana", "viññāṇa",
        ],
        pali="khandha rūpa vedanā saññā saṅkhārā viññāṇa anicca dukkha anattā",
        english_hint="form is not-self if form were self form would not lead to affliction feeling perception fabrications formations consciousness not-self",
    ),
    DictionaryEntry(
        label="Three Marks of Existence",
        keywords=[
            "inconstant", "inconstancy", "impermanent", "impermanence", "three marks", "anicca",
            "stress", "suffering", "not-self", "no self", "anatta", "three characteristics",
            "unsatisfactory nature",
        ],
        pali="tilakkhaṇa anicca dukkha anattā sabbe saṅkhārā vipariṇāma",
        english_hint="form is impermanent feeling is impermanent all fabrications are impermanent subject to change suffering not-self this is not mine I am not this this is not my self",
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
            "jhana", "jhāna", "meditative absorption", "four jhanas", "meditative states",
            "first jhana", "second jhana", "third jhana", "fourth jhana",
            "enter jhana", "attain jhana", "jhana factor",
            "directed thought", "vitakka",
            "evaluation", "vicara", "vicāra",
            "rapture", "piti", "pīti",
            "pleasure jhana", "sukha jhana",
            "singleness of preoccupation", "unification of mind", "ekaggatā", "ekaggata",
            "internal assurance", "ajjhattam sampasadanam",
            "infinite space", "akasanancayatana", "ākāsānañcāyatana",
            "infinite consciousness", "vinnānancāyatana", "viññāṇañcāyatana",
            "nothingness", "akincannayatana", "ākiñcaññāyatana",
            "neither perception nor non-perception", "nevasannānāsaññāyatana",
            "immaterial attainment", "formless jhana", "arupa jhana", "arūpa jhāna",
        ],
        pali="jhāna samādhi vitakka vicāra pīti sukha ekaggatā upekkhā ākāsānañcāyatana viññāṇañcāyatana ākiñcaññāyatana nevasaññānāsaññāyatana",
        english_hint="directed thought evaluation rapture pleasure singleness of preoccupation equanimity first second third fourth jhana seclusion unarisen arisen abandoned",
    ),
    DictionaryEntry(
        label="Concentration / samādhi",
        keywords=[
            "concentration", "one-pointedness", "mental unification",
            "stillness of mind", "calm abiding", "serenity",
            "unified mind", "collected mind",
            "samadhi", "samādhi",
        ],
        pali="samādhi samatha cetaso ekodibhāva",
        english_hint="unified mind concentrated one-pointed seclusion rapture pleasure equanimity developed cultivated noble right concentration made much of",
    ),
    DictionaryEntry(
        label="Mindfulness / satipaṭṭhāna",
        keywords=[
            "four foundations of mindfulness", "establishings of mindfulness",
            "satipatthana", "satipaṭṭhāna", "four frames of reference",
            "contemplation of the body", "contemplation of body", "kayanupassana", "kāyānupassanā",
            "contemplation of feelings", "contemplation of feeling", "feeling tone contemplation", "vedananupassana", "vedanānupassanā",
            "contemplation of the mind", "contemplation of mind", "cittanupassana", "cittānupassanā",
            "contemplation of mental qualities", "contemplation of dhammas", "dhammanupassana", "dhammānupassanā",
            "mindfulness of breathing", "breath awareness", "anapanasati", "ānāpānasati",
            "mindfulness of body", "mindfulness of feelings", "mindfulness of mind",
            "sati",
        ],
        pali="satipaṭṭhāna kāyānupassanā vedanānupassanā cittānupassanā dhammānupassanā ānāpānasati",
        english_hint="contemplation of body feelings mind mental qualities ardent alert mindful setting aside covetousness grief world establishing of mindfulness",
    ),
    DictionaryEntry(
        label="Brahmavihārās / four immeasurables",
        keywords=[
            "four brahmavihāras", "brahmavihara", "brahmaviharas", "brahmavihārā", "four immeasurables",
            "divine abiding", "boundless heart", "immeasurable mind", "sublime attitude",
            "good will", "goodwill", "loving kindness", "lovingkindness", "metta", "mettā",
            "compassion", "karuna", "karuṇā",
            "sympathetic joy", "appreciative joy", "mudita", "muditā",
            "equanimity", "upekkha", "upekkhā",
            "radiate goodwill", "suffuse with good will", "pervade with compassion",
        ],
        pali="brahmavihāra mettā karuṇā muditā upekkhā pharaṇa sattā",
        english_hint="good will compassion sympathetic joy equanimity radiate suffuse pervade all beings immeasurable boundless brahmavihara divine abiding",
    ),
    DictionaryEntry(
        label="Mettā / good will practice",
        keywords=[
            "metta meditation", "good will meditation", "loving kindness meditation",
            "goodwill to all", "goodwill to all beings", "metta practice",
            "may all beings be happy", "may they be free from suffering",
        ],
        pali="mettā sattā sukhī hontu brahmavihāra pharaṇa",
        english_hint="good will loving kindness may all beings be happy free from suffering at ease radiate suffuse unlimited",
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
        english_hint="avoiding these two extremes neither given over to sensual pleasure nor to self-mortification the middle path leading to calm direct knowledge awakening nibbana",
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
        label="Seven factors of awakening / bojjhaṅgā",
        keywords=[
            "seven awakening factors", "seven factors of awakening", "bojjhanga", "bojjhaṅgā",
            "awakening factors", "factors of enlightenment",
            "mindfulness awakening factor", "sati bojjhanga",
            "analysis of qualities", "dhamma-vicaya", "dhammavicaya", "investigation of phenomena",
            "persistence", "persistence awakening factor", "viriya bojjhanga", "energy awakening factor",
            "rapture", "piti", "pīti",
            "passaddhi", "tranquility awakening factor",
            "concentration awakening factor",
            "equanimity awakening factor",
        ],
        pali="bojjhaṅgā sati dhammavicaya viriya pīti passaddhi samādhi upekkhā",
        english_hint="mindfulness analysis of qualities persistence rapture serenity concentration equanimity factors of awakening bojjhanga cultivated developed fulfilled",
    ),
    DictionaryEntry(
        label="Two elements of nibbāna",
        keywords=[
            "nibbana element", "nibbāna element", "nibbanadhatu", "nibbānadhātu",
            "with residue", "without residue", "extinguishment element",
            "two elements of unbinding", "two nibbana elements",
            "parinibbana", "parinibbāna",
        ],
        pali="nibbānadhātu saupādisesā anupādisesā nibbāna parinibbāna",
        english_hint="two elements of unbinding with residue remaining the faculties still present but all suffering experienced here will fade away without residue remaining at death all that is felt not being relished will grow cold the destruction of passion aversion delusion",
    ),
    DictionaryEntry(
        label="Nibbāna / liberation",
        keywords=[
            "nibbana", "nirvana", "awakening", "enlightenment",
            "freedom from suffering", "cessation", "unbinding",
            "liberation", "deathless", "unconditioned",
        ],
        pali="nibbāna vimutti vimokkha sacchikiriyā asaṅkhata",
        english_hint="unborn unbecome unmade unconditioned there would be no escape from what is born become made conditioned deathless cessation unbinding freed released",
    ),
    DictionaryEntry(
        label="Wisdom / insight",
        keywords=[
            "wisdom", "insight", "discernment", "clear seeing",
            "true knowledge", "seeing things as they are",
            "panna", "paññā",
        ],
        pali="paññā vijjā ñāṇa dassana yathābhūta",
        english_hint="knowing and seeing things as they actually are discernment clear seeing understanding arising and passing away impermanent suffering not-self",
    ),
    DictionaryEntry(
        label="Kamma / rebirth",
        keywords=[
            "rebirth", "reincarnation", "kamma", "karma",
            "action and result", "intention", "future lives", "next life",
            "volitional action",
        ],
        pali="kamma cetanā vipāka punabbhava saṃsāra",
        english_hint="beings are owners of their actions heirs of their actions actions are the womb from which they are born whatever actions they do good or bad they will inherit",
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
            "fetter", "ten fetters", "mental fetters", "bonds", "saṃyojana", "samyojana",
            "what binds us", "ten bonds", "overcome fetters", "abandon fetters",
            "lower fetters", "higher fetters", "five lower fetters", "five higher fetters",
            "self-identity views", "sakkāyadiṭṭhi", "sakkāyaditthi", "identity view",
            "grasping at habits-and-practices", "sīlabbataparāmāsa", "silabbataparamasa",
            "grasping at precepts", "precepts-and-practices fetter",
            "sensual passion", "kāmarāga", "kamaraga",
            "resistance fetter", "paṭigha fetter", "patigha fetter",
            "passion for form", "rūparāga", "ruparaga",
            "passion for formlessness", "arūparāga", "aruparaga",
            "conceit fetter", "māna fetter", "sense of I am",
            "restlessness fetter", "uddhacca fetter",
            "ignorance fetter", "avijjā fetter",
        ],
        pali="saṃyojana sakkāyadiṭṭhi vicikicchā sīlabbataparāmāsa kāmarāga paṭigha rūparāga arūparāga māna uddhacca avijjā",
        english_hint="self-identity views uncertainty grasping at habits-and-practices sensual passion resistance passion for form formlessness conceit restlessness ignorance ten fetters bound released stream-enterer",
    ),
    DictionaryEntry(
        label="Five hindrances",
        keywords=[
            "five hindrances", "mental hindrances", "hindrance", "nīvaraṇa", "nivarana",
            "sensual desire", "kamacchanda", "kāmacchanda", "sensuality hindrance",
            "ill will", "byapada", "vyāpāda", "aversion hindrance",
            "sloth", "torpor", "thina-middha", "thīnamiddha", "laziness meditation",
            "restlessness", "worry", "anxiety meditation", "uddhacca", "kukkucca",
            "uncertainty", "vicikiccha", "vicikicchā", "doubt hindrance",
            "overcome hindrance", "abandon hindrance", "suppress hindrance",
        ],
        pali="nīvaraṇa kāmacchanda vyāpāda thīnamiddha uddhacca-kukkucca vicikicchā",
        english_hint="sensual desire ill will sloth torpor restlessness worry uncertainty five hindrances abandon suppress overcome nīvaraṇa not arisen arisen removed",
    ),
    DictionaryEntry(
        label="Defilements / kilesa",
        keywords=[
            "defilement", "defilements", "kilesa", "mental defilement",
            "unwholesome", "roots of unwholesomeness", "greed hate delusion",
            "lobha dosa moha",
            "raga", "rāga",
            "three roots", "three fires", "fire of greed", "fire of hate", "fire of delusion",
            "unskillful roots", "three unwholesome roots",
        ],
        pali="kilesa lobha dosa moha rāga byāpāda avijjā",
        english_hint="greed hate delusion contaminate the mind unwholesome roots defiled mind blameworthy leads to harm suffering not freed from rebirth",
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
        english_hint="form is not-self if form were self form would not lead to affliction this is not mine I am not this this is not my self feeling perception fabrications consciousness not-self",
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
        english_hint="virtue training rule of training restraint refraining abstaining purified upright blameless praised by the wise bodily verbal mental conduct",
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
        english_hint="mind is the forerunner of all actions with mind as chief mind-made if one speaks or acts with a corrupted mind suffering follows if with a clear mind happiness follows",
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
    DictionaryEntry(
        label="Three types of craving",
        keywords=[
            "three kinds of craving", "three types of craving", "three cravings",
            "craving for sensuality", "kāmataṇhā", "kamatanha",
            "craving for becoming", "bhavataṇhā", "bhavatanha", "craving for existence",
            "craving for non-becoming", "vibhavataṇhā", "vibhavatanha", "craving for annihilation",
            "craving for non-existence",
            "tanha", "taṇhā",
        ],
        pali="taṇhā kāmataṇhā bhavataṇhā vibhavataṇhā samudaya",
        english_hint="craving for sensuality craving for becoming craving for non-becoming origin of stress noble truth origination",
    ),
    DictionaryEntry(
        label="Four Types of Clinging / upādāna",
        keywords=[
            "four types of clinging", "four kinds of clinging", "upadana types",
            "clinging to sensuality", "kāmupādāna", "kamupādāna",
            "clinging to views", "diṭṭhupādāna", "ditthupadana",
            "clinging to habits-and-practices", "sīlabbatupādāna", "silabbatupādāna",
            "clinging to doctrine of self", "attavādupādāna", "attavādupadana",
            "clinging to precepts", "grasping at views",
        ],
        pali="upādāna kāmupādāna diṭṭhupādāna sīlabbatupādāna attavādupādāna",
        english_hint="clinging to sensuality views habits-and-practices doctrine of self four types of clinging upādāna arising cessation dependent origination",
    ),
    DictionaryEntry(
        label="Six Sense Bases / āyatana",
        keywords=[
            "six sense bases", "twelve sense bases", "ayatana", "āyatana",
            "internal sense bases", "external sense bases",
            "eye base", "ear base", "nose base", "tongue base", "body base", "mind base",
            "eye contact", "ear contact", "sense contact",
            "allure of the senses", "gratification of the senses", "escape from the senses",
            "gratification danger escape", "delight and lust in the senses",
            "fire of form", "fire of sounds",
        ],
        pali="āyatana cakkhu sota ghāna jivhā kāya mano rūpa sadda gandha rasa phoṭṭhabba dhamma phassa",
        english_hint="eye ear nose tongue body intellect forms sounds smells tastes tactile sensations mental qualities contact arising cessation gratification danger escape allure",
    ),
    DictionaryEntry(
        label="Five Spiritual Faculties / Five Powers",
        keywords=[
            "five faculties", "five spiritual faculties", "pañcaindriya", "pancaindriya",
            "five powers", "pañcabala", "pancabala",
            "faculty of conviction", "faculty of persistence", "faculty of mindfulness",
            "faculty of concentration", "faculty of discernment",
            "power of conviction", "power of persistence", "power of discernment",
            "conviction faculty", "saddhā faculty", "saddha faculty",
            "persistence faculty", "viriya faculty",
            "mindfulness faculty", "sati faculty",
            "concentration faculty", "samādhi faculty",
            "discernment faculty", "paññā faculty",
        ],
        pali="pañcaindriya pañcabala saddhā viriya sati samādhi paññā indriya bala",
        english_hint="conviction persistence mindfulness concentration discernment five faculties five powers noble disciple developed cultivated made much of",
    ),
    DictionaryEntry(
        label="Four Bases of Power / iddhipāda",
        keywords=[
            "four bases of power", "bases of power", "iddhipada", "iddhipāda",
            "roads to success", "four roads to power",
            "intent base of power", "chanda iddhipāda", "desire-to-act",
            "persistence base of power", "viriya iddhipāda",
            "intent-mind base of power", "citta iddhipāda",
            "investigation base of power", "vimamsa", "vīmaṃsā", "vimamsā",
            "psychic power", "supranormal power", "iddhi",
        ],
        pali="iddhipāda chanda viriya citta vīmaṃsā samādhi padhāna iddhi",
        english_hint="intent persistence consciousness investigation four bases of power developed cultivated concentrated ardent alert mindful psychic power roads to success",
    ),
    DictionaryEntry(
        label="Dāna / Generosity",
        keywords=[
            "generosity", "giving", "dāna", "dana", "donation",
            "gift", "charitable giving", "benefits of generosity",
            "gift of dhamma", "give freely", "open hand",
            "merits of giving", "merit from giving",
            "householder giving", "lay supporter generosity",
        ],
        pali="dāna cāga tyāga deyyadhamma dāyaka",
        english_hint="generosity giving gift merit reward open hand unsurpassed gift of dhamma cāga relinquishment",
    ),
    DictionaryEntry(
        label="Three Trainings / tisikkhā",
        keywords=[
            "three trainings", "tisikkha", "tisikkhā",
            "training in higher virtue", "training in higher mind",
            "training in higher discernment", "adhisīla", "adhicitta", "adhipaññā",
            "virtue concentration discernment", "virtue concentration wisdom",
            "gradual training", "threefold training",
        ],
        pali="tisikkhā adhisīla adhicitta adhipaññā sīla samādhi paññā sikkhā",
        english_hint="training in higher virtue training in higher mind training in higher discernment threefold training gradual path virtue concentration discernment",
    ),
    DictionaryEntry(
        label="Disenchantment / nibbidā",
        keywords=[
            "disenchantment", "nibbidā", "nibbida",
            "dispassion", "virāga", "viraga", "fading of passion",
            "disenchanted", "dispassionate",
            "disenchantment dispassion release",
            "seeing as inconstant leads to disenchantment",
            "weariness with the world",
        ],
        pali="nibbidā virāga vimutti ñāṇadassana anicca dukkha anattā",
        english_hint="disenchanted with form feeling perception fabrications consciousness dispassion release disenchantment fades away freed knowing and seeing as it actually is",
    ),
    DictionaryEntry(
        label="Liberation of mind / Liberation through discernment",
        keywords=[
            "liberation of mind", "cetovimutti", "ceto-vimutti",
            "liberation through discernment", "paññāvimutti", "pañña-vimutti",
            "both-ways liberation", "ubhatobhāgavimutti",
            "released through wisdom", "heart-release", "awareness-release",
        ],
        pali="cetovimutti paññāvimutti ubhatobhāgavimutti vimutti vimokkha",
        english_hint="liberation of mind awareness-release heart-release liberation through discernment both-ways liberation released freed unbinding",
    ),
    DictionaryEntry(
        label="Body contemplation / asubha",
        keywords=[
            "32 parts of the body", "thirty-two parts", "body parts meditation",
            "foulness meditation", "asubha", "asubhā",
            "reflection on body parts", "loathsomeness of body",
            "charnel ground", "nine charnel grounds",
            "corpse meditation", "dead body stages",
            "hair nails teeth skin", "anatomical meditation",
        ],
        pali="asubha kāyagatāsati kesā lomā nakhā dantā taco maṃsa nhāru aṭṭhi",
        english_hint="hair nails teeth skin flesh tendons bones marrow kidneys heart liver foulness thirty-two parts loathsome asubha body is like this",
    ),
    DictionaryEntry(
        label="37 Wings to Awakening / bodhipakkhiyā dhammā",
        keywords=[
            "wings to awakening", "thirty-seven wings", "37 wings",
            "bodhipakkhiya", "bodhipakkhiyā dhammā",
            "qualities leading to awakening", "seven sets of awakening factors",
            "aids to awakening",
        ],
        pali="bodhipakkhiyā dhammā satipaṭṭhāna sammappadhāna iddhipāda indriya bala bojjhaṅgā magga",
        english_hint="four establishings of mindfulness four right efforts four bases of power five faculties five powers seven factors of awakening noble eightfold path wings to awakening",
    ),
    DictionaryEntry(
        label="Skillful and unskillful / kusala-akusala",
        keywords=[
            "skillful", "unskillful", "kusala", "akusala",
            "what is skillful", "what is unskillful",
            "skillful qualities", "unskillful qualities",
            "skillful action", "unskillful action",
            "wholesome roots", "unwholesome roots",
            "roots of skillfulness", "roots of unskillfulness",
            "non-greed", "non-aversion", "non-delusion",
            "alobha", "adosa", "amoha",
            "good conduct", "bad conduct", "three kinds of conduct",
            "bodily conduct", "verbal conduct", "mental conduct",
            "wholesome", "unwholesome",
        ],
        pali="kusala akusala lobha dosa moha alobha adosa amoha mūla",
        english_hint="skillful unskillful kusala akusala leads to welfare happiness harm suffering non-greed non-aversion non-delusion roots wholesome unwholesome",
    ),
    DictionaryEntry(
        label="Heedfulness / appamāda",
        keywords=[
            "heedfulness", "heedful", "heedless", "heedlessness",
            "appamāda", "appamada", "pamāda", "pamada",
            "diligence", "non-negligence", "negligence",
            "accomplish with heedfulness", "strive with heedfulness",
            "last words of the buddha",
            "ardent", "ātāpī", "atapi",
            "alert", "sampajāno", "sampajano",
            "keen", "prudent", "not negligent",
        ],
        pali="appamāda pamāda appamatto pamatto ātāpī sampajāno viriya",
        english_hint="heedful heedless all fabrications are impermanent accomplish your goals with heedfulness ardent alert mindful diligence strive non-negligence",
    ),
    DictionaryEntry(
        label="Anger / aversion",
        keywords=[
            "overcome anger", "anger management", "when angry", "letting go of anger",
            "burning with anger", "respond to anger", "anger in Buddhism",
            "āghāta", "aghata", "kodha", "dosa anger",
            "hateful thought", "hostile mind", "wish harm",
        ],
        pali="vyāpāda āghāta kodha paṭigha dosa byāpāda",
        english_hint="anger ill will aversion hatred overcome subdue remove burning with anger consuming hurt like a burning coal",
    ),
    DictionaryEntry(
        label="Grief and loss / soka",
        keywords=[
            "grief", "grieving", "sorrow", "lamentation",
            "soka", "parideva", "domanassa",
            "loved one died", "death of a loved one",
            "bereavement", "mourning", "weeping",
            "loss Buddhism", "how to deal with loss",
        ],
        pali="soka parideva dukkha domanassa upāyāsa jarā maraṇa",
        english_hint="grief sorrow lamentation pain despair aging death weeping mourning loved one overcome grief arises ceases",
    ),
    DictionaryEntry(
        label="Fear / bhaya",
        keywords=[
            "fear", "fright", "afraid", "fearful", "terror",
            "fear in meditation", "overcome fear", "fearless",
            "bhaya", "dread", "afraid of death",
            "fear in the forest", "forest dwelling fear",
        ],
        pali="bhaya chambhitatta lomahaṃsa ottappa hirī nibbhaya",
        english_hint="fear fright overcome afraid fearless dread monk forest grove alone dwelling terror hair-raising",
    ),
    DictionaryEntry(
        label="Food and eating / āhāra",
        keywords=[
            "eating in moderation", "right amount of food", "mindful eating",
            "eating one meal", "monks and food", "reflection before eating",
            "food for sustenance", "knowing the right measure",
            "eating not for amusement", "mātrañña",
        ],
        pali="āhāra kabaḷīkāra mātrañña bhojane",
        english_hint="eating with moderation knowing the right measure support of the body not for amusement not for sport not for beautifying",
    ),
    DictionaryEntry(
        label="Conscience and prudence / hirī-ottappa",
        keywords=[
            "hiri", "hirī", "ottappa", "conscience", "moral shame", "moral dread",
            "two bright things", "bright qualities", "prudence",
            "shame at wrongdoing", "fear of wrongdoing",
        ],
        pali="hirī ottappa lajjī lokapāla",
        english_hint="conscience and prudence these two bright qualities protect the world conscience shame at doing evil prudence dread of doing evil without these no distinction of mother aunt sister wife of teacher monks mendicants",
    ),
    DictionaryEntry(
        label="Three grounds for making merit / puññakiriyavatthu",
        keywords=[
            "grounds for merit", "puññakiriyavatthu", "punnakiriyavatthu",
            "three grounds", "making merit", "merit making",
            "generosity virtue meditation merit",
        ],
        pali="puññakiriyavatthu dāna sīla bhāvanā cāga puñña",
        english_hint="three grounds for making merit giving ethical conduct meditation the wise person desiring happiness should train in these works of merit which have great fruit great benefit the wise give generously cultivate virtue develop meditation merit",
    ),
    DictionaryEntry(
        label="Trainee / sekha",
        keywords=[
            "sekha", "trainee", "one in training", "learner",
            "still training", "not yet complete", "in higher training",
        ],
        pali="sekha sikkhā adhisīla adhicitta adhipaññā sotāpanna",
        english_hint="a trainee one in higher training who has not yet reached the goal longing for relief from the yoke a monk practicing to eliminate greed hate delusion will not return to this world",
    ),
    DictionaryEntry(
        label="Elements of escape / nissaraṇadhātu",
        keywords=[
            "elements of escape", "nissarana", "nissaraṇa", "nissaraṇadhātu",
            "escape from sensuality", "escape from form", "renunciation escapes",
            "formless escapes sensuality", "cessation escapes form",
        ],
        pali="nissaraṇadhātu nekkhamma abyāpajjha nirodha nibbāna",
        english_hint="renunciation is the escape from sensuality formlessness is the escape from form cessation is the escape from what is felt as fabricated whatever beings sense some measure of pleasure joy that is the allure the escape is nibbana",
    ),
    DictionaryEntry(
        label="Bhikkhu / monk",
        keywords=[
            "bhikkhu", "bhikkhuni", "bhikkhunī", "monk", "nun", "monastic",
            "mendicant", "gone forth", "homeless life", "ordained",
        ],
        pali="bhikkhu bhikkhunī pabbajita sāmaṇera brahmacariya sīla sikkhā",
        english_hint="a monk a mendicant bhikkhu one gone forth from the home life into homelessness training in the higher virtue higher mind higher wisdom practicing the holy life living the celibate life bound for liberation nibbana",
    ),
]


def _matches(kw: str, q: str) -> bool:
    return bool(re.search(r"\b" + re.escape(kw) + r"\b", q))


def lookup(query: str) -> Optional[str]:
    q = query.lower()
    for entry in _ENTRIES:
        if any(_matches(kw, q) for kw in entry.keywords):
            return entry.pali
    return None


def lookup_english(query: str) -> Optional[str]:
    q = query.lower()
    for entry in _ENTRIES:
        if any(_matches(kw, q) for kw in entry.keywords):
            return entry.english_hint
    return None

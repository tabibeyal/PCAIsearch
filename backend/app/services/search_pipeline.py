from typing import List, Dict, Any, Optional, Set
import asyncio
import os
import re
from concurrent.futures import ThreadPoolExecutor
from openai import AsyncOpenAI
from sentence_transformers import CrossEncoder
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from backend.app.core.indexing import EmbeddingManager
from backend.app.services.retriever import Retriever
from backend.app.services.sutta_relations import SuttaRelations
from backend.app.services.sutta_title_index import SuttaTitleIndex
from backend.app.services.bm25_retriever import BM25Retriever
from backend.app.services.fusion import rrf_fuse, rrf_fuse_multi
from backend.app.services.pali_dictionary import lookup, lookup_english


class ExpansionPrompt:
    """Manages different versions of the query expansion prompt."""

    VERSIONS = {
        "v1": (
            "You are a search query expander for a Pali Canon database. "
            "Given a user query, output 2 keyword-focused search strings that will improve retrieval. "
            "Rules: (1) include relevant Pali terms (e.g. musavada, anicca, dukkha, sila, samadhi); "
            "(2) include concrete English keywords that would appear in the passage itself, not in the question; "
            "(3) do NOT output sutta names or sutta numbers. "
            "Output one string per line, no numbering, no explanation."
        ),
        "v2": (
            "You are a search query expander for a Pali Canon database. "
            "Given a user query, output exactly 2 search strings on separate lines.\n"
            "Line 1 — English passage vocabulary: concrete words likely to appear verbatim in a sutta "
            "verse. Do NOT rephrase the question. Think: what exact words would a monk say in this passage?\n"
            "Line 2 — Pali doctrinal term cluster: the canonical Pali terminology for the concept, "
            "space-separated and transliterated (e.g. avijja sankharā viññāna paticca-samuppāda). "
            "Proper names of communities or persons are allowed (e.g. kālāmā). "
            "Do NOT include sutta numbers.\n"
            "Output exactly two lines, no numbering, no explanation. "
            "The two lines must be maximally distinct from each other and from the original query."
        ),
        "v3": (
            "You are a search query expander for a Pali Canon database. "
            "Given a user query, output exactly 2 search strings on separate lines.\n"
            "Line 1 — English passage vocabulary: concrete words likely to appear verbatim in a sutta "
            "verse. Do NOT rephrase the question. Think: what exact words would a monk say in this passage?\n"
            "Line 2 — Pali doctrinal term cluster: the canonical Pali terminology for the concept, "
            "space-separated and transliterated (e.g. avijja sankharā viññāna paticca-samuppāda). "
            "Proper names of communities or persons are allowed (e.g. kālāmā). "
            "Do NOT include sutta numbers.\n"
            "Output exactly two lines, no numbering, no explanation. "
            "The two lines must be maximally distinct from each other and from the original query.\n\n"
            "Pāḷi reference (use for Line 2):\n"
            "- dependent origination / ignorance: paṭicca-samuppāda avijjā saṅkhārā viññāṇa taṇhā\n"
            "- five aggregates / not-self: khandha rūpa vedanā saññā saṅkhārā viññāṇa anattā anicca\n"
            "- Kālāma sutta / testing teachings: kālāmā anussava parampara itikirā takkahetu\n"
            "- saw simile / patience under attack: kakacūpama khanti abyāpajjha mettā\n"
            "- householder ethics / parents & family: sigālovāda mātāpitaro disa ācariya mitta\n"
            "- four noble truths: cattāri ariyasaccāni dukkha samudaya nirodha magga\n"
            "- noble eightfold path: sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta "
            "sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi\n"
            "- mindfulness / breath: satipaṭṭhāna kāyānupassanā ānāpānasati\n"
            "- jhāna / absorption: jhāna samādhi vitakka vicāra pīti sukha ekaggatā\n"
            "- nibbāna / liberation: nibbāna vimutti asaṅkhata vimokkha\n"
            "- brahmavihārās / good will: good will goodwill mettā karuṇā muditā upekkhā brahmavihāra\n"
            "- precepts / ethics: sīla pāṇātipātā musāvādā adinnādānā\n"
            "- three marks of existence: inconstant inconstancy stress suffering tilakkhaṇa anicca dukkha anattā\n"
            "- kamma / intention / rebirth: kamma cetanā vipāka punabbhava saṃsāra\n"
            "- middle way: majjhimā paṭipadā atitta atilīna"
        ),
        "v4": (
            "You are a search query expander for a Pali Canon database. "
            "Given a user query, output exactly 2 lines. "
            "No labels, no headings, no numbering, no explanation — output only the 2 lines.\n\n"
            "Line 1: Concrete English words that would appear verbatim in the sutta passage. "
            "Not a rephrasing of the question — think what exact words a monk would say.\n"
            "Line 2: Canonical Pali terminology for the concept, space-separated. "
            "Use the reference table below. Do NOT include sutta numbers.\n\n"
            "Example:\n"
            "Query: what is the middle way\n"
            "Output:\n"
            "avoid extremes pleasure pain indulgence asceticism moderation\n"
            "majjhimā paṭipadā atitta atilīna\n\n"
            "Pāḷi reference (use for Line 2):\n"
            "- dependent origination / ignorance: paṭicca-samuppāda avijjā saṅkhārā viññāṇa taṇhā\n"
            "- five aggregates / not-self: khandha rūpa vedanā saññā saṅkhārā viññāṇa anattā anicca\n"
            "- Kālāma sutta / testing teachings: kālāmā anussava parampara itikirā takkahetu\n"
            "- saw simile / patience under attack: kakacūpama khanti abyāpajjha mettā\n"
            "- householder ethics / parents & family: sigālovāda mātāpitaro disa ācariya mitta\n"
            "- four noble truths: cattāri ariyasaccāni dukkha samudaya nirodha magga\n"
            "- noble eightfold path: sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta "
            "sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi\n"
            "- mindfulness / breath: satipaṭṭhāna kāyānupassanā ānāpānasati\n"
            "- jhāna / absorption: jhāna samādhi vitakka vicāra pīti sukha ekaggatā\n"
            "- nibbāna / liberation: nibbāna vimutti asaṅkhata vimokkha\n"
            "- brahmavihārās / good will: good will goodwill mettā karuṇā muditā upekkhā brahmavihāra\n"
            "- precepts / ethics: sīla pāṇātipātā musāvādā adinnādānā\n"
            "- three marks of existence: inconstant inconstancy stress suffering tilakkhaṇa anicca dukkha anattā\n"
            "- kamma / intention / rebirth: kamma cetanā vipāka punabbhava saṃsāra\n"
            "- middle way: majjhimā paṭipadā atitta atilīna"
        ),
        "v5": (
            "You are a search query expander for a Pali Canon database. "
            "Given a user query, output exactly 2 lines. "
            "No labels, no headings, no numbering, no explanation — output only the 2 lines.\n\n"
            "Line 1: Concrete English words that would appear verbatim in the sutta passage. "
            "Not a rephrasing of the question — think what exact words a monk would say.\n"
            "Line 2: Canonical Pali terminology for the concept, space-separated. "
            "Use the reference table below. Do NOT include sutta numbers.\n\n"
            "Example:\n"
            "Query: what is the middle way\n"
            "Output:\n"
            "avoid extremes pleasure pain indulgence asceticism moderation\n"
            "majjhimā paṭipadā atitta atilīna\n\n"
            "Pāḷi reference (English passage hints → Pāḷi terms):\n"
            "- dependent origination / ignorance: with ignorance as condition formations arise consciousness → paṭicca-samuppāda avijjā saṅkhārā viññāṇa taṇhā\n"
            "- five aggregates / not-self: form inconstant stress suffering not-self clinging → khandha rūpa vedanā saññā saṅkhārā viññāṇa anattā anicca\n"
            "- Kālāma sutta / testing teachings: tradition hearsay scripture reasoning teacher → kālāmā anussava parampara itikirā takkahetu\n"
            "- saw simile / patience under attack: two-handled saw bandits limb loving-kindness → kakacūpama khanti abyāpajjha mettā\n"
            "- householder ethics / parents & family: six directions parents teacher friend servant ascetic → sigālovāda mātāpitaro disa ācariya mitta\n"
            "- four noble truths: stress suffering origin cessation path → cattāri ariyasaccāni dukkha samudaya nirodha magga\n"
            "- noble eightfold path: right view resolve speech action livelihood effort mindfulness concentration → sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta "
            "sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi\n"
            "- mindfulness / breath: body feelings mind phenomena → satipaṭṭhāna kāyānupassanā ānāpānasati\n"
            "- jhāna / absorption: first second third fourth seclusion rapture pleasure equanimity → jhāna samādhi vitakka vicāra pīti sukha ekaggatā\n"
            "- nibbāna / liberation: unborn unconditioned deathless → nibbāna vimutti asaṅkhata vimokkha\n"
            "- brahmavihārās / good will: good will goodwill loving-kindness compassion sympathetic joy equanimity → mettā karuṇā muditā upekkhā brahmavihāra\n"
            "- precepts / ethics: abstain killing stealing lying intoxicants → sīla pāṇātipātā musāvādā adinnādānā\n"
            "- three marks of existence: inconstant impermanent stress suffering not-self → tilakkhaṇa anicca dukkha anattā\n"
            "- kamma / intention / rebirth: intention action result rebirth wandering → kamma cetanā vipāka punabbhava saṃsāra\n"
            "- middle way: avoid extremes pleasure pain indulgence asceticism moderation → majjhimā paṭipadā atitta atilīna"
        ),
        "v6": (
            "You are a search query expander for a Pali Canon database. "
            "Given a user query, output exactly 2 lines. "
            "Do NOT write 'Line 1:' or 'Line 2:' or any label — output only the 2 lines of search terms.\n\n"
            "Line 1: Concrete English words that would appear verbatim in the sutta passage. "
            "IMPORTANT: if the topic matches a reference entry, use the English hint words from that entry for Line 1 — "
            "even if they seem unrelated to the question surface. The hint words come from the actual sutta text.\n"
            "Line 2: Canonical Pali terminology. Use the reference table below. Do NOT include sutta numbers.\n\n"
            "Example:\n"
            "Query: should a monk feel anger even if attacked with a saw\n"
            "Output:\n"
            "two-handed saw bandits cut limbs loving-kindness\n"
            "kakacūpama khanti abyāpajjha mettā\n\n"
            "Reference table (English passage hint → Pāḷi terms):\n"
            "- dependent origination / ignorance: with ignorance as condition formations arise consciousness name-form → paṭicca-samuppāda avijjā saṅkhārā viññāṇa taṇhā\n"
            "- five aggregates / not-self: form feeling perception formation consciousness impermanent not-self → khandha rūpa vedanā saññā saṅkhārā viññāṇa anattā anicca\n"
            "- Kālāma sutta / testing teachings: tradition hearsay scripture reasoning teacher [these words appear in text as what NOT to rely on] → kālāmā anussava parampara itikirā takkahetu\n"
            "- saw simile / patience under attack: two-handed saw bandits cut limbs loving-kindness → kakacūpama khanti abyāpajjha mettā\n"
            "- truthfulness / lying / one precept Rahula: speak false untruth Rahula mirror reflect → musāvādā sacca sammā-vācā\n"
            "- householder ethics / parents & family: six directions parents teacher friend servant ascetic → sigālovāda mātāpitaro disa ācariya mitta\n"
            "- four noble truths: stress suffering origin cessation path → cattāri ariyasaccāni dukkha samudaya nirodha magga\n"
            "- noble eightfold path: right view resolve speech action livelihood effort mindfulness concentration → sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta "
            "sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi\n"
            "- mindfulness / breath: body feelings mind phenomena → satipaṭṭhāna kāyānupassanā ānāpānasati\n"
            "- jhāna / absorption: first second third fourth seclusion rapture pleasure equanimity → jhāna samādhi vitakka vicāra pīti sukha ekaggatā\n"
            "- nibbāna / liberation: unborn unconditioned deathless → nibbāna vimutti asaṅkhata vimokkha\n"
            "- brahmavihārās / good will: good will goodwill loving-kindness compassion sympathetic joy equanimity → mettā karuṇā muditā upekkhā brahmavihāra\n"
            "- precepts / ethics: abstain killing stealing lying intoxicants → sīla pāṇātipātā musāvādā adinnādānā\n"
            "- craving / addiction / compulsion: consumed overwhelmed desire sensual pleasure ferment taint clinging not freed → taṇhā rāga āsava kāmacchanda upādāna\n"
            "- three marks of existence: inconstant impermanent stress suffering not-self → tilakkhaṇa anicca dukkha anattā\n"
            "- kamma / intention / rebirth: intention action result rebirth wandering → kamma cetanā vipāka punabbhava saṃsāra\n"
            "- middle way: avoid extremes pleasure pain indulgence asceticism moderation → majjhimā paṭipadā atitta atilīna"
        ),
        "v7": (
            "You are a search query expander for a Pali Canon database. "
            "STEP 0 (silent): If the query is not in English, translate it to English first. "
            "All output must be in English regardless of the query language.\n\n"
            "Given the (possibly translated) query, output exactly 2 lines. "
            "Do NOT write 'Line 1:' or 'Line 2:' or any label — output only the 2 lines of search terms.\n\n"
            "Line 1: Concrete English words that would appear verbatim in the sutta passage. "
            "IMPORTANT: if the topic matches a reference entry, use the English hint words from that entry for Line 1 — "
            "even if they seem unrelated to the question surface. The hint words come from the actual sutta text.\n"
            "Line 2: Canonical Pali terminology. Use the reference table below. Do NOT include sutta numbers.\n\n"
            "Example:\n"
            "Query: should a monk feel anger even if attacked with a saw\n"
            "Output:\n"
            "two-handed saw bandits cut limbs loving-kindness\n"
            "kakacūpama khanti abyāpajjha mettā\n\n"
            "Reference table (English passage hint → Pāḷi terms):\n"
            "- dependent origination / ignorance: with ignorance as condition formations arise consciousness name-form → paṭicca-samuppāda avijjā saṅkhārā viññāṇa taṇhā\n"
            "- five aggregates / not-self: form feeling perception formation consciousness impermanent not-self → khandha rūpa vedanā saññā saṅkhārā viññāṇa anattā anicca\n"
            "- five aggregates similes / lump of foam: lump foam bubble mirage banana trunk illusion vacuous hollow insubstantial Ganges → pheṇapiṇḍa khandha anicca anattā\n"
            "- Kālāma sutta / testing teachings: tradition hearsay scripture reasoning teacher [these words appear in text as what NOT to rely on] → kālāmā anussava parampara itikirā takkahetu\n"
            "- saw simile / patience under attack: two-handed saw bandits cut limbs loving-kindness → kakacūpama khanti abyāpajjha mettā\n"
            "- truthfulness / lying / one precept Rahula: speak false untruth Rahula mirror reflect → musāvādā sacca sammā-vācā\n"
            "- householder ethics / parents & family: six directions parents teacher friend servant ascetic → sigālovāda mātāpitaro disa ācariya mitta\n"
            "- four noble truths: stress suffering origin cessation path → cattāri ariyasaccāni dukkha samudaya nirodha magga\n"
            "- noble eightfold path: right view resolve speech action livelihood effort mindfulness concentration → sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta "
            "sammā-ājīva sammā-vāyāma sammā-sati sammā-samādhi\n"
            "- mindfulness / breath: body feelings mind phenomena → satipaṭṭhāna kāyānupassanā ānāpānasati\n"
            "- jhāna / absorption: first second third fourth seclusion rapture pleasure equanimity → jhāna samādhi vitakka vicāra pīti sukha ekaggatā\n"
            "- nibbāna / liberation: unborn unconditioned deathless → nibbāna vimutti asaṅkhata vimokkha\n"
            "- brahmavihārās / good will: good will goodwill loving-kindness compassion sympathetic joy equanimity → mettā karuṇā muditā upekkhā brahmavihāra\n"
            "- precepts / ethics: abstain killing stealing lying intoxicants → sīla pāṇātipātā musāvādā adinnādānā\n"
            "- craving / addiction / compulsion: consumed overwhelmed desire sensual pleasure ferment taint clinging not freed → taṇhā rāga āsava kāmacchanda upādāna\n"
            "- three marks of existence: inconstant impermanent stress suffering not-self → tilakkhaṇa anicca dukkha anattā\n"
            "- kamma / intention / rebirth: intention action result rebirth wandering → kamma cetanā vipāka punabbhava saṃsāra\n"
            "- middle way: avoid extremes pleasure pain indulgence asceticism moderation → majjhimā paṭipadā atitta atilīna\n"
            "- devas / heavenly beings: deva deity approached sat one side lord blessed → deva devaputta brahmā sakka\n"
            "- Mara / death / temptation: Mara evil one snare trap host armies flowers → māra pāpimā\n"
            "- sense bases / contact: eye ear nose tongue body mind contact feeling → āyatana phassa vedanā salāyatana\n"
            "- raft simile / do not cling to the teaching: near shore far shore raft grass sticks branches leaves carry head cross over → kullūpama\n"
            "- snake/cobra simile / wrong grasp of teachings: cobra coil grasp wrong grasp cleft stick venom bite hand → alagaddūpama\n"
            "- poisoned arrow simile / unanswered questions: arrow thickly smeared poison surgeon extract undeclared cosmos eternal soul body → salla\n"
            "- relay chariots simile / stages of the path: chariots stationed ready Sāvatthī Sāketa mounted dismounted seven stages → rathavinīta\n"
            "- stained cloth simile / purifying the mind: cloth dirty soiled dye blue yellow red magenta pure clean impure corrupt → vattha\n"
            "- elephant's footprint simile / four noble truths encompass all: footprints creatures walk elephant footprint biggest includes four noble truths → hatthipadopama\n"
            "- ancient path/city simile / rediscovering the Dhamma: ancient path ancient route forest person walking old road parks groves lotus ponds capital → nagara\n"
            "- dog on leash simile / running around the aggregates: hound leash tethered post pillar running circling form feeling perception choices consciousness → gaddula\n"
            "- everything is burning simile / fire of the senses: burning fire greed hate delusion eye ear nose tongue body mind contact → āditta\n"
            "- two arrows simile / adding mental suffering to physical pain: struck arrow second arrow two feelings physical mental uninstructed wails laments → dvisalla\n"
            "- handful of leaves simile / what the Buddha teaches vs what he knows: rosewood leaves handful forest tiny amount what I know what I teach → siṃsapā\n"
            "- blind turtle simile / precious human birth: yoke single hole one-eyed turtle hundred years ocean east west north south winds → chiggaḷa\n"
            "- lute string simile / balanced energy: arched harp strings tuned too tight too slack even tension resonant playable Soṇa energy restlessness laziness → vīṇā\n"
            "- against the stream / four types of practitioners: goes with the stream goes against the stream steadfast crossed over far shore sensual pleasures bad deeds → paṭisota\n"
            "- salt in mug vs Ganges / kamma ripens by development: lump of salt mug of water Ganges river salty undrinkable big-hearted small-minded trivial bad deed → kamma cetanā\n"
            "- fire sticks / contact produces feeling: rub two sticks together heat generated fire produced part sticks lay aside contact feeling pleasant painful equanimity → phassa vedanā samphassa\n"
            "- cook simile / mindfulness reads the mind's hints: foolish cook master hint sauce sour bitter pungent sweet salty bland mindfulness immersion corruptions wages → satipaṭṭhāna\n"
            "- bathman soap ball simile / jhāna pervades the body: bathroom attendant bath powder bronze dish kneads ball rapture bliss drench steep fill pervade body seclusion → jhāna pīti sukha\n"
            "- goldsmith purifying mind / refining meditation: native gold crucible blow melt smelt pliable workable radiant dross ornament bracelet coarse fine corruptions → citta samādhi\n"
            "- peg simile / replacing unskillful thoughts: deft mason large peg finer peg knock extract unskillful skillful thoughts desire hate delusion → vitakka\n"
            "- cow udder simile / rational vs irrational practice: pulling horn newly-calved cow udder milk irrational rational wish fruit churning curds butter sesame oil → sammā paṭipadā\n"
            "- acrobat simile / guarding self and others: pole acrobat corpse-workers bamboo pole apprentice shoulders skill display fee safely mutual protection → satipaṭṭhāna\n"
            "- ocean one taste / Dhamma has one taste of liberation: ocean one taste salt titans rivers lose names clans taste of freedom teaching training → dhamma vinaya vimutti\n"
            "- lotus pool simile / jhāna pervades without gap: pool blue water lilies pink white lotuses sprout grow rising above thriving underwater no part body → jhāna pīti sukha\n"
            "- island to yourself / be your own refuge: live as your own island refuge no other refuge teaching island Ānanda passed mendicant → attadīpa satipaṭṭhāna\n"
            "- city with six gates / sense bases and mindfulness: frontier citadel fortified ramparts six gates gatekeeper astute body four principal states consciousness lord of city → āyatana sati\n"
            "- dyed water simile / five hindrances obscure the mind: bowl water mixed dye red lac turmeric boiling bubbling moss aquatic plants stirred wind reflection see clearly → nīvaraṇa"
        ),
    }

    def __init__(self, version: str = "v7"):
        self.version = version

    def get_prompt(self) -> str:
        """Get the prompt for the selected version."""
        if self.version not in self.VERSIONS:
            raise ValueError(f"Unknown expansion prompt version: {self.version!r}. Available: {list(self.VERSIONS)}")
        return self.VERSIONS[self.version]

    @classmethod
    def list_versions(cls) -> list[str]:
        """List available prompt versions."""
        return list(cls.VERSIONS.keys())


def _extract_sutta_id(chunk_id: str) -> Optional[str]:
    """Extract 'DN 15' from a chunk ID like 'DN 15:3'."""
    parts = chunk_id.rsplit(":", 1)
    return parts[0].strip() if len(parts) == 2 else None


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_LABEL_RE = re.compile(r"^(?:Line\s*\d+\s*[-:—]+\s*|Line\s*\d+:\s*)", re.IGNORECASE)


def _strip_thinking(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: List[dict]) -> List[dict]:
        return self.rerank_multi([query], chunks)

    def rerank_multi(self, queries: List[str], chunks: List[dict]) -> List[dict]:
        if not chunks:
            return []
        best = [float("-inf")] * len(chunks)
        texts = [f"{c.get('pali', '')} {c.get('english', '')}" for c in chunks]
        for q in queries:
            scores = self.model.predict([(q, t) for t in texts])
            for i, s in enumerate(scores.tolist()):
                if s > best[i]:
                    best[i] = s
        ranked = sorted(zip(chunks, best), key=lambda x: x[1], reverse=True)
        return [{**chunk, "rerank_score": score} for chunk, score in ranked]


_SYSTEM_PROMPT = (
    "You are a scholarly assistant for the Pali Canon. "
    "Answer questions using only the provided context. "
    "Never invent sutta numbers or modify source text. "
    "No HTML tags. "
    "\n\n"
    "OUT OF SCOPE (check this first, before doing anything else): "
    "If the question has no conceivable connection to the Pali Canon, Buddhist teachings, Dhamma practice, "
    "meditation, or the historical Buddha — respond with exactly this one sentence and nothing else: "
    "'This question is outside the scope of this search engine, which covers the Pali Canon and Buddhist teachings.' "
    "Examples of out-of-scope: arithmetic, cooking, sports, current events, geography unrelated to Buddhism, "
    "any question that could not plausibly be answered by a sutta passage. "
    "Examples of IN-scope: practical life questions about anger, grief, relationships, fear, happiness, "
    "or ethics — even if phrased without Buddhist vocabulary — because the canon addresses these directly. "
    "\n\n"
    "GROUNDING RULE: Every claim must be drawn directly from a specific passage in the context. "
    "Paraphrase or quote what that passage actually says — do not use citations as generic labels for topics. "
    "For example, do not write 'mindfulness helps with addiction [SN x.y]' unless SN x.y explicitly teaches this. "
    "Instead, say what SN x.y actually says, then connect it to the question. "
    "If a passage does not clearly support a claim, do not cite it."
    "\n\n"
    "HONESTY ABOUT LIMITS: If the question asks for a specific count, number, or enumeration and no passage in the "
    "context provides that count explicitly, say so plainly. For example: 'The canon does not record a total count, "
    "but the Devaputta-saṃyutta (SN 2) contains X suttas where devas visit the Buddha, and encounters appear "
    "throughout the Nikāyas.' Do not substitute a vague phrase like 'on many occasions' for a concrete answer "
    "the context cannot actually support — acknowledge the limit instead."
    "\n\n"
    "NEVER DENY EXISTENCE: Never say a sutta does not exist, that the canon does not contain something, or that "
    "the Buddha never taught something, based solely on what is or is not in the retrieved context. "
    "You have access to a sample of retrieved passages, not the entire canon. "
    "If you cannot find something in the provided context, say exactly that: "
    "'I couldn't find this in the retrieved passages' — not 'no such sutta exists' or 'this is not in the canon.'"
    "\n\n"
    "CITATIONS: After every sentence that draws on a source, insert the citation ID in square brackets "
    "directly after the sentence, e.g. '...all conditioned things are impermanent. [SN 22.12:3]' "
    "Use the exact ID string from the context (the part before the word 'Pali:'). "
    "Multiple citations go in one bracket, comma-separated: [SN 22.12:3, AN 6.98:3]. "
    "HARD LIMIT: never put more than 3 citations in a single bracket. "
    "Cite immediately after the sentence — never accumulate citations at the end of a paragraph. "
    "NEVER use parentheses () for citations — square brackets [] only. "
    "\n\n"
    "QUESTION TYPE — adapt your format to the question:\n"
    "- Factual / counting questions (how many, how often, did X happen, yes/no): lead with the most direct "
    "answer the context supports in one sentence, then elaborate. If the context cannot give a precise answer, "
    "say so in that first sentence before explaining what it does say.\n"
    "- Conceptual / doctrinal questions (what is X, how does X work, why): use the full format below.\n"
    "\n"
    "Full format (for conceptual questions):\n"
    "- Write a full introductory paragraph that situates the topic in its doctrinal context (max 5 sentences).\n"
    "- Follow with a bullet-point section that breaks down the key teachings, one idea per bullet. "
    "Each bullet should be a complete sentence or two — not a single word or embedded list.\n"
    "- End with a closing paragraph (max 5 sentences) that draws the threads together and notes any nuance or limitation in the retrieved texts.\n"
    "\n"
    "PARAGRAPH LENGTH (HARD LIMIT): Every paragraph MUST contain AT MOST 5 sentences. "
    "Count sentences as you write. If a paragraph would exceed 5 sentences, break it into two paragraphs separated by a blank line. "
    "This applies to the introductory paragraph, the closing paragraph, and any prose elsewhere. No exceptions.\n"
    "\n"
    "Be thorough but never repeat a point already made. "
    "If you have more to say than fits in 5 sentences, split into multiple short paragraphs rather than writing one long one. "
    "Let there be visual breathing room between sections."
)


def _build_messages(query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    context_text = "\n\n".join(
        f"[{c['id']}] Pali: {c['pali']}\nEnglish: {c['english']}"
        for c in chunks
        if len(c.get("english", "").strip().split()) >= 4
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"},
    ]


class SearchPipeline:
    """
    Implements the RAG pipeline: Query Expansion -> Retrieval -> Synthesis.
    """
    def __init__(
        self,
        qdrant_url: str = os.environ.get("QDRANT_URL", "http://localhost:6333"),
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        llm_model: str = os.environ.get("LLM_MODEL", "meta/llama-3.3-70b-instruct"),
        expansion_model: str = os.environ.get("EXPANSION_MODEL", "google/gemma-3n-e4b-it"),
        sutta_relations: Optional[SuttaRelations] = None,
        expansion_prompt: Optional[ExpansionPrompt] = None,
        title_index: Optional[SuttaTitleIndex] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
    ):
        self._executor = ThreadPoolExecutor(max_workers=4)
        client = AsyncQdrantClient(
            url=qdrant_url,
            api_key=os.environ.get("QDRANT_API_KEY"),
        )
        embedding_mgr = EmbeddingManager(model_name=model_name)
        self.collection_name = "pali_canon"
        self.retriever = Retriever(client, embedding_mgr, self.collection_name, self._executor)
        self.llm_model = llm_model
        self.llm = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ.get("NVIDIA_API_KEY"),
            timeout=60.0,
        )
        self.reranker = Reranker()
        self.sutta_relations = sutta_relations
        self.expansion_prompt = expansion_prompt or ExpansionPrompt("v7")
        self.title_index = title_index
        self.expansion_model = expansion_model
        self.bm25_retriever = bm25_retriever

    def shutdown(self):
        self._executor.shutdown(wait=True)

    async def warmup(self) -> None:
        """Pre-run one inference pass through both ONNX models so the JIT compiler
        fires at startup rather than on the first real user request."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor, self.retriever.embedding_mgr.encode, "warmup"
        )
        await loop.run_in_executor(
            self._executor, self.reranker.model.predict, [("warmup", "warmup")]
        )

    async def expand_query(self, query: str) -> List[str]:
        prompt = self.expansion_prompt.get_prompt()
        message = await self.llm.chat.completions.create(
            model=self.expansion_model,
            max_tokens=256,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
        )
        raw = _strip_thinking(message.choices[0].message.content)
        extras = [_LABEL_RE.sub("", line).strip() for line in raw.splitlines() if line.strip()]
        seen: set = {query}
        variants = [query]
        for v in extras:
            if v not in seen:
                seen.add(v)
                variants.append(v)
        variants = variants[:3]
        pali_hit = lookup(query)
        if pali_hit:
            variants.append(pali_hit)
        english_hit = lookup_english(query)
        if english_hit and english_hit not in seen:
            variants.append(english_hit)
        return variants

    async def search(self, query: str, top_k: int = 10, nikayas: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        queries = await self.expand_query(query)

        # Title boost: if a canonical sutta title matches the query, add its
        # title text as an extra retrieval query so the reranker sees its verses.
        if self.title_index:
            title_hits = self.title_index.search(query, top_n=1)
            if title_hits:
                top_sutta_id, _ = title_hits[0]
                title_text = self.title_index.get_title_text(top_sutta_id)
                if title_text and title_text not in queries:
                    queries = list(queries) + [title_text]

        retrieval_k = max(top_k * 3, 30)
        per_query = await asyncio.gather(*[self.retriever.retrieve(q, retrieval_k, nikayas) for q in queries])

        dense_fused = rrf_fuse_multi(list(per_query))

        if self.bm25_retriever:
            seen_bm25: dict = {}
            for q in queries:
                for item in self.bm25_retriever.retrieve(q, retrieval_k, nikayas):
                    item_id = item["id"]
                    if item_id not in seen_bm25 or item["bm25_score"] > seen_bm25[item_id]["bm25_score"]:
                        seen_bm25[item_id] = item
            bm25_results = sorted(seen_bm25.values(), key=lambda x: x["bm25_score"], reverse=True)
            all_results = rrf_fuse(dense_fused, bm25_results)
        else:
            all_results = dense_fused

        # Rerank against original + English passage hint only. The cross-encoder
        # is trained on English text and doesn't understand Pāḷi — adding the pali_hit
        # introduces noise. The english_hint (verbatim passage text) bridges vocabulary
        # gaps the cross-encoder can actually exploit (e.g. MN 61: 'deliberate lie' ≠
        # 'precept'). Pāḷi terms have already done their job during retrieval.
        rerank_queries: List[str] = [query]
        english_hit_str = lookup_english(query)
        if english_hit_str:
            rerank_queries.append(english_hit_str)
        return self.reranker.rerank_multi(rerank_queries, all_results)[:top_k]

    def get_related_suttas(self, results: List[Dict[str, Any]], top_n: int = 5) -> List[str]:
        """
        Return canonically related sutta IDs not already in the top results.
        """
        if self.sutta_relations is None:
            return []
        retrieved_suttas: Set[str] = set()
        for r in results[:top_n]:
            sid = _extract_sutta_id(r.get("id", ""))
            if sid:
                retrieved_suttas.add(sid)
        related: Set[str] = set()
        for sutta_id in retrieved_suttas:
            for ref in self.sutta_relations.get_related(sutta_id):
                if ref not in retrieved_suttas:
                    related.add(ref)
        return sorted(related)

    async def synthesize(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        message = await self.llm.chat.completions.create(
            model=self.llm_model,
            max_tokens=1024,
            timeout=120.0,
            messages=_build_messages(query, context_chunks),
        )
        return _strip_thinking(message.choices[0].message.content)

    async def stream_synthesize(self, query: str, context_chunks: List[Dict[str, Any]]):
        stream = await self.llm.chat.completions.create(
            model=self.llm_model,
            max_tokens=1024,
            timeout=120.0,
            stream=True,
            messages=_build_messages(query, context_chunks),
        )
        full_text = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text += delta
                yield {"type": "chunk", "text": delta}
        yield {"type": "full", "text": _strip_thinking(full_text)}
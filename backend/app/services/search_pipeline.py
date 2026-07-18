from typing import Any
import asyncio
import itertools
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

from openai import AsyncOpenAI
from sentence_transformers import CrossEncoder
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from backend.app.core.indexing import EmbeddingManager
from backend.app.services.retriever import Retriever
from backend.app.services.sutta_relations import SuttaRelations
from backend.app.services.sutta_title_index import SuttaTitleIndex
from backend.app.services.bm25_retriever import BM25Retriever
from backend.app.services.fusion import rrf_fuse_multi
from backend.app.services.pali_dictionary import lookup, lookup_english

logger = logging.getLogger(__name__)


_EXPANSION_PROMPT_V7 = (
    "You are a search query expander for a Pali Canon database. "
    "STEP 0 (silent): Strip any conversational framing ('Do you know a sutta where...', 'Is there a sutra about...', 'Can you find...', 'Is there more than one...', 'Are there different versions of...') and extract only the core topic or scene being described. "
    "If the query asks about 'versions', 'different definitions', or 'more than one way' of explaining a concept, treat it as: find suttas that give a detailed analysis or exposition of that concept. "
    "If the query is not in English, translate it to English. "
    "All output must be in English regardless of the query language.\n\n"
    "Given the (possibly translated) query, output exactly 2 lines. "
    "Do NOT write 'Line 1:' or 'Line 2:' or any label — output only the 2 lines of search terms.\n\n"
    "Translation note: this corpus uses Thanissaro Bhikkhu's translations. Key divergences from standard English: "
    "'dukkha' is rendered as 'stress' or 'stressful' (not 'suffering'); "
    "'kusala/akusala' as 'skillful/unskillful' (not 'wholesome/unwholesome'); "
    "'saddhā' as 'conviction' (not 'faith'); "
    "'paññā' as 'discernment' (not 'wisdom'); "
    "'āsava' as 'fermentation' (not 'taint'). "
    "When a query uses any of the standard terms, include both the standard term AND Thanissaro's equivalent in Line 1.\n\n"
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
    "- dependent origination / ignorance: ignorance is a requirement for choices consciousness name and form six sense fields contact feeling craving grasping continued existence rebirth → paṭicca-samuppāda avijjā saṅkhārā viññāṇa taṇhā\n"
    "- five aggregates / not-self: form feeling perception formation consciousness impermanent not-self → khandha rūpa vedanā saññā saṅkhārā viññāṇa anattā anicca\n"
    "- five aggregates similes / lump of foam: lump foam bubble mirage banana trunk illusion vacuous hollow insubstantial Ganges → pheṇapiṇḍa khandha anicca anattā\n"
    "- Kālāma sutta / testing teachings: tradition hearsay scripture reasoning teacher [these words appear in text as what NOT to rely on] → kālāmā anussava parampara itikirā takkahetu\n"
    "- saw simile / patience under attack: two-handed saw bandits cut limbs loving-kindness → kakacūpama khanti abyāpajjha mettā\n"
    "- truthfulness / lying / one precept Rahula: speak false untruth Rahula mirror reflect → musāvādā sacca sammā-vācā\n"
    "- householder ethics / parents & family: six directions parents teacher friend servant ascetic → sigālovāda mātāpitaro disa ācariya mitta\n"
    "- four noble truths: stress suffering origin cessation path → cattāri ariyasaccāni dukkha samudaya nirodha magga\n"
    "- noble eightfold path: right view purpose speech action livelihood effort mindfulness immersion → sammā-diṭṭhi sammā-saṅkappa sammā-vācā sammā-kammanta "
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
    "- dyed water simile / five hindrances obscure the mind: bowl water mixed dye red lac turmeric boiling bubbling moss aquatic plants stirred wind reflection see clearly → nīvaraṇa\n"
    "- Ānanda weeps / grief at parinibbāna: weeping leaning door jamb building still in training work left to do total unbinding teacher sympathy Kusinārā devatās tearing hair uplifting arms → parinibbāna Ānanda āyasmant\n"
    "- ten courses of action / kamma paths: ten courses unskillful skillful action killing stealing sexual misconduct lying divisive speech harsh speech idle chatter covetousness ill-will wrong view → kamma cetanā akusala kusala kammapatha\n"
    "- levels of generosity / motivations for giving: gift bears great fruit great benefit motivations giving seeking profit reward rebirth heaven immersion heart liberated highest → dāna cāga cetanā\n"
    "- Mahākassapa austerities / ascetic practices: one-robe practice refuses invitations refuses additional robes austerity forest-dweller elder revered → dhutaṅga Mahākassapa cīvara\n"
    "- analysis of the truths / Sāriputta exposition / definition of suffering stress / different versions of definition / more than one version / who defines the truths / teachers who explain suffering: Analysis of Truths Sāriputta birth stressful aging stressful death stressful sorrow lamentation pain distress despair not getting what is wanted five clinging aggregates Isipatana Wheel of Dhamma → saccavibhanga Sāriputta dukkha ariyasacca"
)


def get_expansion_prompt() -> str:
    """Return the current v7 query-expansion prompt."""
    return _EXPANSION_PROMPT_V7


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_LABEL_RE = re.compile(r"^(?:Line\s*\d+\s*[-:—]+\s*|Line\s*\d+:\s*)", re.IGNORECASE)
_PAREN_CITE_RE = re.compile(r"\(([A-Z]{1,4} [\d.]+:\d+)\)")


def _strip_thinking(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


def _normalize_citations(text: str) -> str:
    # Llama sometimes ignores the "square brackets only" instruction and outputs (MN 1.2:3).
    # Convert to [MN 1.2:3] so the guardrail and frontend renderer can process them.
    return _PAREN_CITE_RE.sub(r"[\1]", text)


# Display band for the frontend "% match". The cross-encoder logits are
# uncalibrated and mostly negative for this domain, so any absolute transform
# (e.g. sigmoid) collapses every result to ~1%. Instead we rank-normalize the
# logits within each result set: the best match sits near the ceiling, the rest
# descend from it, and even the weakest shown passage keeps a non-alarming floor.
_RELEVANCE_FLOOR = 0.5
_RELEVANCE_CEIL = 0.99


def _relevance_scores(rerank_scores: list[float]) -> list[float]:
    if not rerank_scores:
        return []
    lo, hi = min(rerank_scores), max(rerank_scores)
    spread = hi - lo
    if not spread:
        return [_RELEVANCE_CEIL] * len(rerank_scores)
    return [
        _RELEVANCE_FLOOR + (_RELEVANCE_CEIL - _RELEVANCE_FLOOR) * (s - lo) / spread
        for s in rerank_scores
    ]


_RERANKER_CACHE: dict[str, CrossEncoder] = {}


class Reranker:
    """
    Cross-encoder reranker. The underlying model is cached globally because it
    is large (~400 MB) and slow to load; without caching every SearchPipeline()
    in tests reloads it and exhausts memory.
    """
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        if model_name not in _RERANKER_CACHE:
            _RERANKER_CACHE[model_name] = CrossEncoder(model_name)
        self.model = _RERANKER_CACHE[model_name]

    def rerank_multi(self, queries: list[str], chunks: list[dict]) -> list[dict]:
        if not chunks:
            return []
        best = [float("-inf")] * len(chunks)
        texts = [c.get("english", "") for c in chunks]
        for q in queries:
            scores = self.model.predict([(q, t) for t in texts])
            for i, s in enumerate(scores.tolist()):
                if s > best[i]:
                    best[i] = s
        ranked = sorted(zip(chunks, best), key=lambda x: x[1], reverse=True)
        return [{**chunk, "rerank_score": score} for chunk, score in ranked]


_SYSTEM_PROMPT = (
    "You are a guide to the Pali Canon. "
    "Your job is to point people to the right passages — not to teach doctrine. "
    "Answer using ONLY the provided context. "
    "NEVER invent a sutta ID, verse number, or passage text. If you cannot answer from the provided context, say so. "
    "Never modify source text. "
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
    "Paraphrase what that passage actually says in your own words — do not use citations as generic labels for topics. "
    "NEVER quote a passage at length; a short phrase is acceptable, but bulk quotation is forbidden. "
    "For example, do not write 'mindfulness helps with addiction [SN x.y]' unless SN x.y explicitly teaches this. "
    "Instead, say what SN x.y actually says, then connect it to the question. "
    "If a passage does not clearly support a claim, do not cite it. "
    "If a passage does not directly address the question, skip it — do not include it to pad the bullet count."
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
    "Use the exact ID string from the context (the text in square brackets). "
    "Multiple citations go in one bracket, comma-separated: [SN 22.12:3, AN 6.98:3]. "
    "HARD LIMIT: never put more than 3 citations in a single bracket. "
    "If you need to credit more than 3 sources for one claim, split the claim into multiple sentences so each sentence stays under the limit. "
    "Cite immediately after the sentence — never accumulate citations at the end of a paragraph. "
    "NEVER use parentheses () for citations — square brackets [] only. "
    "\n\n"
    "QUESTION TYPE — adapt your format to the question:\n"
    "- Factual / counting questions (how many, how often, did X happen, yes/no): lead with the most direct "
    "answer the context supports in one sentence, then elaborate. If the context cannot give a precise answer, "
    "say so in that first sentence before explaining what it does say.\n"
    "- Comparison / 'more than one version' / 'are there different versions' / 'who else defines' questions: "
    "answer YES or NO first, then contrast the versions. Name which teacher or passage gives which version "
    "and identify exactly what phrases or elements appear in one but not another. "
    "Do NOT merge or consolidate similar passages — the differences between them ARE the answer. "
    "Use bullets, one per version.\n"
    "- Conceptual / doctrinal questions (what is X, how does X work, why): use the full format below.\n"
    "\n"
    "Full format (for conceptual questions):\n"
    "- Open with exactly ONE sentence that orients the topic. No more than one sentence before the bullets. If many passages give the same core definition, state it in that sentence with consolidated citations — so the bullets can focus on what each passage adds beyond it.\n"
    "- Follow with bullet points. Each bullet leads with what a specific passage actually says, then the citation. "
    "The passage does the explaining — not the framing around it. "
    "Each bullet must add something distinct — a different angle, context, or teaching. "
    "Do not repeat the core definition in every bullet. "
    "If two bullets would say essentially the same thing, merge them into one bullet regardless of whether their citation IDs differ. "
    "If the retrieved passages mostly repeat the same teaching, write FEWER bullets — even just 2 or 3 sharp ones — rather than padding with repetition."
    "Each bullet should be a complete sentence or two — not a single word or embedded list.\n"
    "- Aim for 2–5 bullets that each add something genuinely different. Fewer sharp bullets beat many repetitive ones. "
    "Do not write more bullets than there are passages with real content in the context. "
    "If a passage is only a heading or label, it does not count as real content.\n"
    "- When the context includes passages from more than one nikāya, draw from at least 3 different nikāyas.\n"
    "- Do not add a closing paragraph. Let the passages speak for themselves.\n"
)


_CITATION_RE = re.compile(r"\[([^\]]+)\]")


def _enforce_citation_limit(text: str, max_citations: int = 3) -> str:
    """Post-process: trim any bracket that exceeds max_citations.

    Keeps the first max_citations and silently drops the rest.
    This compensates for small models that ignore the 'hard limit'
    instruction in the system prompt.
    """
    def _trim(match: re.Match) -> str:
        inner = match.group(1)
        items = [item.strip() for item in inner.split(",")]
        if len(items) <= max_citations:
            return match.group(0)
        kept = items[:max_citations]
        return f"[{', '.join(kept)}]"
    return _CITATION_RE.sub(_trim, text)


def _build_messages(query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    context_text = "\n\n".join(
        f"[{c['id']}] {c.get('english', '')}"
        for c in chunks
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
        expansion_model: str = os.environ.get("EXPANSION_MODEL", "meta/llama-3.1-8b-instruct"),
        sutta_relations: SuttaRelations | None = None,
        title_index: SuttaTitleIndex | None = None,
        bm25_retriever: BM25Retriever | None = None,
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
        self.expansion_prompt = get_expansion_prompt
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

    async def expand_query(self, query: str) -> list[str]:
        seen: set[str] = {query}
        variants: list[str] = [query]
        try:
            prompt = self.expansion_prompt()
            t0 = time.perf_counter()
            message = await self.llm.chat.completions.create(
                model=self.expansion_model,
                max_tokens=256,
                timeout=10.0,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": query},
                ],
            )
            logger.info("expand_query/nvidia: %.2fs", time.perf_counter() - t0)
            raw = _strip_thinking(message.choices[0].message.content)
            extras = [_LABEL_RE.sub("", line).strip() for line in raw.splitlines() if line.strip()]
            for v in extras:
                if v not in seen:
                    seen.add(v)
                    variants.append(v)
            variants = variants[:3]
        except Exception as exc:
            logger.warning("query expansion failed, using original query: %s", exc)
        pali_hit = lookup(query)
        if pali_hit:
            variants.append(pali_hit)
        english_hit = lookup_english(query)
        if english_hit and english_hit not in seen:
            variants.append(english_hit)
        return variants

    def _bm25_dedup(
        self,
        queries: list[str],
        retrieval_k: int,
        nikayas: list[str] | None,
        exclude_commentary: bool = False,
    ) -> list[dict[str, Any]]:
        """Run BM25 for each query, keep the highest-scoring copy of each verse, sort by score."""
        seen: dict[str, dict[str, Any]] = {}
        for q in queries:
            for item in self.bm25_retriever.retrieve(q, retrieval_k, nikayas, exclude_commentary):
                item_id = item["id"]
                if item_id not in seen or item["bm25_score"] > seen[item_id]["bm25_score"]:
                    seen[item_id] = item
        return sorted(seen.values(), key=lambda x: x["bm25_score"], reverse=True)

    def _apply_title_boost(self, query: str, queries: list[str]) -> list[str]:
        """If a canonical sutta title matches the query, append its title text as an
        extra retrieval query so the reranker sees that sutta's verses."""
        if not self.title_index:
            return queries
        title_hits = self.title_index.search(query, top_n=1)
        if not title_hits:
            return queries
        top_sutta_id, _ = title_hits[0]
        title_text = self.title_index.get_title_text(top_sutta_id)
        if title_text and title_text not in queries:
            return list(queries) + [title_text]
        return queries

    async def _run_pipeline(
        self,
        queries: list[str],
        retrieval_k: int,
        nikayas: list[str] | None,
        prefetched_first: list[dict[str, Any]],
        precomputed_bm25: list[dict[str, Any]] | None,
        exclude_commentary: bool = False,
    ) -> list[dict[str, Any]]:
        """Retrieve → fuse → BM25 for a single nikaya bucket.

        Returns fused candidates (no rerank, no slicing). The caller reranks
        the union of all buckets' candidates in a single pass and partitions
        the scored list back per bucket for round-robin interleaving.
        """
        t0 = time.perf_counter()
        loop = asyncio.get_running_loop()

        extra_queries = queries[1:]
        if extra_queries:
            extra = await asyncio.gather(*[
                self.retriever.retrieve(q, retrieval_k, nikayas, exclude_commentary=exclude_commentary)
                for q in extra_queries
            ])
            dense_fused = rrf_fuse_multi([prefetched_first] + list(extra))
        else:
            dense_fused = rrf_fuse_multi([prefetched_first])

        logger.info("retrieve: %.2fs", time.perf_counter() - t0)
        t1 = time.perf_counter()

        if precomputed_bm25 is not None:
            # Shared BM25 results pre-filtered by nikaya — skip recomputing.
            all_results = rrf_fuse_multi([dense_fused, precomputed_bm25])
        elif self.bm25_retriever:
            bm25_results = await loop.run_in_executor(
                self._executor, self._bm25_dedup, queries, retrieval_k, nikayas, exclude_commentary
            )
            all_results = rrf_fuse_multi([dense_fused, bm25_results])
        else:
            all_results = dense_fused

        logger.info("bm25: %.2fs", time.perf_counter() - t1)
        return all_results

    async def search(
        self,
        query: str,
        top_k: int = 10,
        nikayas: list[str] | None = None,
        exclude_commentary: bool = False,
    ) -> list[dict[str, Any]]:
        t0 = time.perf_counter()
        retrieval_k = max(top_k * 3, 30)

        # Rerank against the original query plus any English passage hint. The
        # cross-encoder is trained on English text and doesn't understand Pāḷi —
        # adding the pali_hit introduces noise. The english_hint (verbatim passage
        # text) bridges vocabulary gaps (e.g. MN 61: 'deliberate lie' ≠ 'precept').
        # Concatenating it with the query keeps the hint vocabulary in a single
        # scoring pass, halving the number of cross-encoder forward calls.
        english_hit_str = lookup_english(query)
        rerank_queries: list[str] = [f"{query} {english_hit_str}" if english_hit_str else query]

        # Normalise nikayas into a list of buckets. No filter and single-nikaya
        # both produce a one-element list — the per-bucket pipeline below is the
        # identity for N=1.
        buckets: list[str | None] = list(nikayas) if nikayas else [None]

        # Overlap expansion with initial per-bucket retrieval so the NVIDIA API
        # wait runs alongside the first Qdrant round-trip per bucket.
        gather_out = await asyncio.gather(
            self.expand_query(query),
            *[
                self.retriever.retrieve(query, retrieval_k, [b] if b else None, exclude_commentary=exclude_commentary)
                for b in buckets
            ],
        )
        queries: list[str] = gather_out[0]
        bucket_initials: list[list[dict[str, Any]]] = list(gather_out[1:])

        logger.info("expand+initial_retrieve: %.2fs", time.perf_counter() - t0)

        queries = self._apply_title_boost(query, queries)

        # Run BM25 once across all nikayas, then split per bucket.
        # Running BM25 inside each _run_pipeline would score 50k verses
        # N_buckets × N_queries times — ~6× redundant work.
        loop = asyncio.get_running_loop()
        if self.bm25_retriever:
            shared_bm25 = await loop.run_in_executor(
                self._executor, self._bm25_dedup, queries, retrieval_k, None, exclude_commentary
            )
            bm25_by_bucket: dict[str | None, list[dict[str, Any]] | None] = {
                b: ([item for item in shared_bm25 if item.get("nikaya") == b] if b else shared_bm25)
                for b in buckets
            }
        else:
            bm25_by_bucket = {b: None for b in buckets}

        logger.info("bm25(shared): %.2fs", time.perf_counter() - t0)

        # Retrieve + fuse per bucket in parallel. Trim each bucket before
        # reranking: the cross-encoder is CPU-bound and scales linearly with the
        # number of candidates. Reranking the full fused list (often 100+ items)
        # dominates search latency, while the round-robin interleave only needs
        # enough high-fusion candidates from each bucket to fill top_k.
        budget_per_bucket = max(retrieval_k * 2, 100)
        bucket_candidates = await asyncio.gather(*[
            self._run_pipeline(
                queries, retrieval_k, ([b] if b else None),
                prefetched_first=initial, precomputed_bm25=bm25_by_bucket[b],
                exclude_commentary=exclude_commentary,
            )
            for b, initial in zip(buckets, bucket_initials)
        ])
        bucket_candidates = [cands[:budget_per_bucket] for cands in bucket_candidates]

        # Union the per-bucket candidates, dedup by id keeping the first occurrence
        # (RRF rank order means earlier = higher fusion rank).
        seen_ids: set[str] = set()
        union: list[dict[str, Any]] = []
        for candidates in bucket_candidates:
            for c in candidates:
                if c["id"] not in seen_ids:
                    seen_ids.add(c["id"])
                    union.append(c)

        # One batched rerank over the union. The cross-encoder scores each
        # (query, chunk) pair independently, so per-chunk scores are identical
        # to what per-bucket rerank would have produced — we just pay the
        # model-load cost once instead of N times.
        t_rerank = time.perf_counter()
        scored = await loop.run_in_executor(
            self._executor,
            lambda: self.reranker.rerank_multi(rerank_queries, union),
        )
        logger.info("rerank: %.2fs", time.perf_counter() - t_rerank)

        # Partition the scored list back per bucket. The retriever doesn't
        # surface the nikaya field, so derive it from the chunk id prefix.
        def _bucket_of(chunk: dict[str, Any]) -> str | None:
            if len(buckets) == 1:
                return buckets[0]
            chunk_id = chunk.get("id", "")
            prefix = chunk_id.split(":", 1)[0].split()[0] if chunk_id else ""
            return prefix if prefix in buckets else None

        scored_by_bucket: dict[str | None, list[dict[str, Any]]] = {b: [] for b in buckets}
        for chunk in scored:
            scored_by_bucket[_bucket_of(chunk)].append(chunk)

        # Round-robin interleave: pick one result from each bucket in turn.
        # Identity for N=1 (one bucket, take the top top_k).
        results: list[dict[str, Any]] = []
        for chunk in itertools.chain(*itertools.zip_longest(*scored_by_bucket.values())):
            if chunk is None or len(results) == top_k:
                continue
            results.append(chunk)

        # The cross-encoder score is the final ranking signal; downstream
        # consumers (frontend match %, synthesis ordering) only read `score`.
        # Rank-normalize within the result set so the displayed percentage is
        # meaningful despite the logits being uncalibrated (see _relevance_scores).
        for chunk, score in zip(
            results, _relevance_scores([c.get("rerank_score", 0.0) for c in results])
        ):
            chunk["score"] = score

        logger.info("search total: %.2fs", time.perf_counter() - t0)
        return results

    def get_related_suttas(self, results: list[dict[str, Any]], top_n: int = 5) -> list[str]:
        """
        Return canonically related sutta IDs not already in the top results.
        """
        if self.sutta_relations is None:
            return []
        retrieved_suttas: set[str] = set()
        for r in results[:top_n]:
            chunk_id = r.get("id", "")
            parts = chunk_id.rsplit(":", 1)
            sid = parts[0].strip() if len(parts) == 2 else None
            if sid:
                retrieved_suttas.add(sid)
        related: set[str] = set()
        for sutta_id in retrieved_suttas:
            for ref in self.sutta_relations.get_related(sutta_id):
                if ref not in retrieved_suttas:
                    related.add(ref)
        return sorted(related)

    @staticmethod
    def prepare_context(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter out near-empty chunks and deduplicate identical English text so
        the model never sees multiple copies of the same phrase. This is the
        "kept context" — synthesis, the Guardrail, the Receipt, and the API
        response must all share this exact list, not the raw retrieved chunks."""
        seen_english: set[str] = set()
        kept: list[dict[str, Any]] = []
        for c in chunks:
            eng = c.get("english", "").strip()
            if len(eng.split()) < 4:
                continue
            if eng in seen_english:
                continue
            seen_english.add(eng)
            kept.append(c)
        return kept

    async def synthesize(self, query: str, context_chunks: list[dict[str, Any]]) -> str:
        kept = self.prepare_context(context_chunks)
        message = await self.llm.chat.completions.create(
            model=self.llm_model,
            max_tokens=1200,
            temperature=0.3,
            timeout=120.0,
            messages=_build_messages(query, kept),
        )
        raw = _normalize_citations(_strip_thinking(message.choices[0].message.content))
        return _enforce_citation_limit(raw)

    async def stream_synthesize(self, query: str, context_chunks: list[dict[str, Any]]):
        kept = self.prepare_context(context_chunks)
        stream = await self.llm.chat.completions.create(
            model=self.llm_model,
            max_tokens=1200,
            temperature=0.3,
            timeout=120.0,
            stream=True,
            messages=_build_messages(query, kept),
        )
        full_text = ""
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text += delta
                yield {"type": "chunk", "text": delta}
        yield {"type": "full", "text": _enforce_citation_limit(_normalize_citations(_strip_thinking(full_text)))}

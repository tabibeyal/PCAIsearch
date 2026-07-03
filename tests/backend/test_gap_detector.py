import pytest
from backend.app.services.gap_detector import FeedbackCandidate, GapDetector


class FakeFeedbackStore:
    def __init__(self, candidates: list[FeedbackCandidate]) -> None:
        self._candidates = candidates
        self.handled: list[tuple] = []

    def fetch_down_votes(self) -> list[FeedbackCandidate]:
        return self._candidates

    def mark_handled(self, feedback_id, issue_url: str) -> None:
        self.handled.append((feedback_id, issue_url))


class FakePipeline:
    def __init__(self, results: list[dict]) -> None:
        self._results = results
        self.queries: list[str] = []

    async def search(self, query: str, top_k: int = 10) -> list[dict]:
        self.queries.append(query)
        return self._results


class FakeIssueTracker:
    def __init__(self) -> None:
        self.created: list[tuple] = []
        self._next_id = 1

    def create_issue(self, title: str, body: str) -> str:
        self.created.append((title, body))
        url = f"https://github.com/tabibeyal/PCAIsearch/issues/{self._next_id}"
        self._next_id += 1
        return url


def _candidate(**overrides) -> FeedbackCandidate:
    defaults = dict(
        id=1,
        query="what did the Buddha say about anger?",
        answer="The Buddha taught patience.",
        category="Not relevant to my question",
        comment=None,
    )
    defaults.update(overrides)
    return FeedbackCandidate(**defaults)


@pytest.mark.asyncio
async def test_qualifying_candidate_files_an_issue():
    store = FakeFeedbackStore([_candidate()])
    tracker = FakeIssueTracker()
    detector = GapDetector(store, FakePipeline([]), tracker)

    filed = await detector.run()

    assert filed == ["https://github.com/tabibeyal/PCAIsearch/issues/1"]


@pytest.mark.asyncio
async def test_non_qualifying_category_produces_no_issue():
    store = FakeFeedbackStore([_candidate(category="Too vague")])
    tracker = FakeIssueTracker()
    detector = GapDetector(store, FakePipeline([]), tracker)

    await detector.run()

    assert tracker.created == []


@pytest.mark.asyncio
async def test_qualifying_candidate_marks_feedback_handled_with_issue_url():
    store = FakeFeedbackStore([_candidate(id=42)])
    tracker = FakeIssueTracker()
    detector = GapDetector(store, FakePipeline([]), tracker)

    await detector.run()

    assert store.handled == [(42, "https://github.com/tabibeyal/PCAIsearch/issues/1")]


@pytest.mark.asyncio
async def test_run_re_runs_the_query_live_through_the_pipeline():
    store = FakeFeedbackStore([_candidate(query="what is anatta?")])
    pipeline = FakePipeline([])
    detector = GapDetector(store, pipeline, FakeIssueTracker())

    await detector.run()

    assert pipeline.queries == ["what is anatta?"]


@pytest.mark.asyncio
async def test_issue_body_includes_live_retrieval_candidates():
    store = FakeFeedbackStore([_candidate()])
    pipeline = FakePipeline([{"id": "MN 27:14", "english": "...", "score": 0.842}])
    tracker = FakeIssueTracker()
    detector = GapDetector(store, pipeline, tracker)

    await detector.run()

    _, body = tracker.created[0]
    assert "MN 27:14" in body


@pytest.mark.asyncio
async def test_run_stops_at_max_issues_per_run_cap():
    store = FakeFeedbackStore([_candidate(id=i) for i in range(3)])
    tracker = FakeIssueTracker()
    detector = GapDetector(store, FakePipeline([]), tracker, max_issues_per_run=2)

    filed = await detector.run()

    assert len(filed) == 2


@pytest.mark.asyncio
async def test_run_returns_no_issues_when_no_candidates_qualify():
    store = FakeFeedbackStore([])
    detector = GapDetector(store, FakePipeline([]), FakeIssueTracker())

    filed = await detector.run()

    assert filed == []

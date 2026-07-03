from backend.app.services.feedback_gap_store import SupabaseFeedbackStore
from backend.app.services.gap_detector import FeedbackCandidate


class FakeSupabaseRestClient:
    def __init__(self, get_result=None):
        self._get_result = get_result or []
        self.get_calls: list[tuple] = []
        self.patch_calls: list[tuple] = []

    def get(self, table, query):
        self.get_calls.append((table, query))
        return self._get_result

    def patch(self, table, query, payload):
        self.patch_calls.append((table, query, payload))


def test_fetch_down_votes_queries_unhandled_down_votes_newest_first():
    client = FakeSupabaseRestClient()
    store = SupabaseFeedbackStore(client)

    store.fetch_down_votes()

    assert client.get_calls == [
        ("feedback", "rating=eq.down&gap_issue_url=is.null&order=created_at.desc")
    ]


def test_fetch_down_votes_maps_rows_to_feedback_candidates():
    client = FakeSupabaseRestClient(get_result=[
        {"id": 7, "query": "what is anatta?", "answer": "...", "category": "Too vague", "comment": "meh"}
    ])
    store = SupabaseFeedbackStore(client)

    candidates = store.fetch_down_votes()

    assert candidates == [
        FeedbackCandidate(id=7, query="what is anatta?", answer="...", category="Too vague", comment="meh")
    ]


def test_mark_handled_patches_the_row_with_the_issue_url():
    client = FakeSupabaseRestClient()
    store = SupabaseFeedbackStore(client)

    store.mark_handled(7, "https://github.com/x/y/issues/1")

    assert client.patch_calls == [
        ("feedback", "id=eq.7", {"gap_issue_url": "https://github.com/x/y/issues/1"})
    ]

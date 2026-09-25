import importlib.util
import io
import json
import urllib.error
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "jev_decide.py"
_spec = importlib.util.spec_from_file_location("jev_decide", _SCRIPT)
jev_decide = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jev_decide)

_RISK_OK = {
    "model": "jev-test",
    "answers": {
        "risk_level": {"type": "score", "score": 0.05, "confidence": 0.95,
                       "probabilities": {"0": 0.95, "1": 0.05, "2": 0.0, "3": 0.0}},
        "contradicts_decision": {"type": "noul", "noul": 0.02},
    },
}


class _FakeResponse:
    def __init__(self, body: dict):
        self._raw = json.dumps(body).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(jev_decide.API_URL, code, "err", {}, io.BytesIO(b"{}"))


def _fake_urlopen(*outcomes):
    """Each call pops the next outcome: an exception to raise, or a body to return."""
    queue = list(outcomes)

    def urlopen(req, timeout):
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return _FakeResponse(outcome)

    return urlopen


def _run(monkeypatch, capsys, argv, stdin=None):
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(stdin)))
    code = jev_decide.main(argv)
    return code, capsys.readouterr().out


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(jev_decide.time, "sleep", lambda s: None)

    def install(*outcomes):
        monkeypatch.setattr(jev_decide.urllib.request, "urlopen", _fake_urlopen(*outcomes))

    return install


def test_closed_decision_string_in_state_merges_with_flag(monkeypatch, capsys):
    _, out = _run(monkeypatch, capsys,
                  ["risk", "--state", "-", "--closed-decision", "second", "--dry-run"],
                  stdin={"closed_decisions": "first"})
    assert json.loads(out)["state"]["closed_decisions"] == ["first", "second"]


def test_overloaded_api_is_retried(api, monkeypatch, capsys):
    api(_http_error(529), _RISK_OK)
    code, _ = _run(monkeypatch, capsys, ["risk", "--change", "fix a typo in README"])
    assert code == jev_decide.EXIT["act"]


def test_rate_limit_that_never_clears_fails_closed_on_risk(api, monkeypatch, capsys):
    api(_http_error(429), _http_error(429), _http_error(429))
    code, _ = _run(monkeypatch, capsys, ["risk", "--change", "fix a typo in README"])
    assert code == jev_decide.EXIT["ask_human"]


def test_validation_error_is_not_retried(api, monkeypatch, capsys):
    api(_http_error(422), _RISK_OK)
    code, _ = _run(monkeypatch, capsys, ["risk", "--change", "fix a typo in README"])
    assert code == jev_decide.EXIT["ask_human"]


def _classify_answer(choice: str, confidence: float) -> dict:
    return {"model": "jev-test",
            "answers": {"ticket_type": {"type": "choice", "choice": choice, "confidence": confidence}}}


def test_unsure_classify_falls_back_to_grilling(api, monkeypatch, capsys):
    api(_classify_answer("task", 0.30))
    _, out = _run(monkeypatch, capsys, ["classify", "--ticket", "Decide how to rank sources"])
    assert json.loads(out)["value"] == "grilling"


def test_grilling_fallback_still_pairs_with_domain_modeling(api, monkeypatch, capsys):
    api(_classify_answer("task", 0.30))
    _, out = _run(monkeypatch, capsys, ["classify", "--ticket", "Decide how to rank sources"])
    assert json.loads(out)["pair_with"] == "domain-modeling"


def test_classify_error_falls_back_to_grilling(api, monkeypatch, capsys):
    api(_http_error(500))
    _, out = _run(monkeypatch, capsys, ["classify", "--ticket", "Decide how to rank sources"])
    assert json.loads(out)["value"] == "grilling"


def test_fog_sends_open_tickets_so_jev_can_spot_duplicates(monkeypatch, capsys):
    _, out = _run(monkeypatch, capsys,
                  ["fog", "--question", "Should BM25 weight titles?", "--open-ticket", "#14 Title boost", "--dry-run"])
    assert json.loads(out)["state"]["open_tickets"] == ["#14 Title boost"]


def test_risk_gate_asks_human_when_low_mean_hides_a_destructive_tail(api, monkeypatch, capsys):
    api({"model": "jev-test", "answers": {
        "risk_level": {"type": "score", "score": 0.75, "confidence": 0.9,
                       "probabilities": {"0": 0.75, "1": 0.0, "2": 0.0, "3": 0.25}},
        "contradicts_decision": {"type": "noul", "noul": 0.02},
    }})
    code, _ = _run(monkeypatch, capsys, ["risk", "--change", "clean up old index files"])
    assert code == jev_decide.EXIT["ask_human"]


def test_risk_gate_acts_on_an_uncertain_split_between_harmless_levels(api, monkeypatch, capsys):
    api({"model": "jev-test", "answers": {
        "risk_level": {"type": "score", "score": 0.5, "confidence": 0.3,
                       "probabilities": {"0": 0.5, "1": 0.5, "2": 0.0, "3": 0.0}},
        "contradicts_decision": {"type": "noul", "noul": 0.02},
    }})
    code, _ = _run(monkeypatch, capsys, ["risk", "--change", "fix a typo in README"])
    assert code == jev_decide.EXIT["act"]

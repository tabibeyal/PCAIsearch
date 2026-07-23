from backend.app.services.share_receipt import generate_receipt, sanitize_context, verify_receipt

SIGNING_KEY = "fake-signing-value-for-tests"

QUERY = "What is dukkha?"
ANSWER = "Dukkha means suffering [MN 10:1]."
CONTEXT = [{"id": "MN 10:1", "english": "Suffering is...", "title": "Mindfulness Meditation", "score": 0.912}]


def test_valid_receipt_round_trips():
    receipt = generate_receipt(QUERY, ANSWER, CONTEXT, SIGNING_KEY)
    assert verify_receipt(QUERY, ANSWER, CONTEXT, receipt, SIGNING_KEY) is True


def test_tampered_query_fails_verification():
    receipt = generate_receipt(QUERY, ANSWER, CONTEXT, SIGNING_KEY)
    assert verify_receipt("What is nibbana?", ANSWER, CONTEXT, receipt, SIGNING_KEY) is False


def test_tampered_answer_fails_verification():
    receipt = generate_receipt(QUERY, ANSWER, CONTEXT, SIGNING_KEY)
    assert verify_receipt(QUERY, "Something else entirely.", CONTEXT, receipt, SIGNING_KEY) is False


def test_tampered_context_entry_fails_verification():
    receipt = generate_receipt(QUERY, ANSWER, CONTEXT, SIGNING_KEY)
    tampered_context = [{**CONTEXT[0], "english": "Different text entirely"}]
    assert verify_receipt(QUERY, ANSWER, tampered_context, receipt, SIGNING_KEY) is False


def test_receipt_ignores_non_canonical_fields_like_score():
    receipt = generate_receipt(QUERY, ANSWER, CONTEXT, SIGNING_KEY)
    reordered_score_context = [{**CONTEXT[0], "score": 0.913}]
    assert verify_receipt(QUERY, ANSWER, reordered_score_context, receipt, SIGNING_KEY) is True


def test_wrong_key_fails_verification():
    receipt = generate_receipt(QUERY, ANSWER, CONTEXT, SIGNING_KEY)
    assert verify_receipt(QUERY, ANSWER, CONTEXT, receipt, "a-different-value") is False


def test_sanitize_context_keeps_split_title_fields():
    context = [{
        **CONTEXT[0],
        "title_pali": "Satipaṭṭhāna Sutta",
        "title_english": "Mindfulness Meditation",
    }]
    [sanitized] = sanitize_context(context)
    assert (sanitized["title_pali"], sanitized["title_english"]) == (
        "Satipaṭṭhāna Sutta",
        "Mindfulness Meditation",
    )

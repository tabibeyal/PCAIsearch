from backend.app.services.pali_dictionary import lookup


def test_lookup_dependent_origination():
    result = lookup("how does ignorance cause suffering step by step")
    assert result is not None
    assert "paṭicca-samuppāda" in result
    assert "avijjā" in result


def test_lookup_kalama_sutta():
    result = lookup("how do you know whether a religious teaching is worth following")
    assert result is not None
    assert "kālāmā" in result


def test_lookup_five_aggregates():
    result = lookup("are the five aggregates permanent or do they lack a self")
    assert result is not None
    assert "khandha" in result
    assert "anattā" in result


def test_lookup_saw_simile():
    result = lookup("should a monk feel anger if attacked with a saw")
    assert result is not None
    assert "kakacūpama" in result


def test_lookup_parents_family():
    result = lookup("how should one treat parents family and friends")
    assert result is not None
    assert "sigālovāda" in result


def test_lookup_lying_precept():
    result = lookup("what is the one precept you should never break")
    assert result is not None
    assert "musāvādā" in result


def test_lookup_case_insensitive():
    lower = lookup("loving kindness meditation")
    upper = lookup("LOVING KINDNESS MEDITATION")
    assert lower is not None
    assert lower == upper


def test_lookup_multi_keyword_fires_on_any():
    result = lookup("eightfold path")
    assert result is not None
    assert "sammā-diṭṭhi" in result

    result2 = lookup("right view and right intention")
    assert result2 is not None
    assert "sammā-diṭṭhi" in result2


def test_lookup_unknown_returns_none():
    assert lookup("what is a good recipe for bread") is None
    assert lookup("how do I exit vim") is None


def test_lookup_returns_string():
    result = lookup("four noble truths")
    assert isinstance(result, str)
    assert len(result) > 0

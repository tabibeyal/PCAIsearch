from backend.app.services.pali_dictionary import lookup, lookup_english


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


def test_lookup_english_kalama_sutta():
    result = lookup_english("how do you know whether a religious teaching is worth following")
    assert result is not None
    assert "oral tradition" in result
    assert "hearsay" in result


def test_lookup_english_five_aggregates():
    result = lookup_english("are the five aggregates permanent or do they lack a self")
    assert result is not None
    assert "form is not-self" in result


def test_lookup_english_lying_precept():
    result = lookup_english("what is the one precept you should never break")
    assert result is not None
    assert "not ashamed to tell a deliberate lie" in result
    assert "bad deed" in result


def test_lookup_english_dependent_origination():
    result = lookup_english("how does ignorance cause suffering step by step")
    assert result is not None
    assert "ignorance is a requirement for choices" in result


def test_lookup_english_no_hint_returns_none():
    # "five precepts" matches the entry but it has no english_hint
    result = lookup_english("five precepts")
    assert result is None


def test_lookup_english_unknown_returns_none():
    assert lookup_english("what is a good recipe for bread") is None


def test_lookup_english_buddha_decision_to_teach():
    result = lookup_english("what did the buddha consider after enlightenment before deciding to teach")
    assert result is not None
    assert "deep" in result
    assert "Brahma" in result


# --- Part 2: standalone Pali keyword coverage ---

def test_lookup_bare_dukkha():
    result = lookup("dukkha")
    assert result is not None
    assert "dukkha" in result


def test_lookup_bare_samadhi():
    result = lookup("samadhi")
    assert result is not None
    assert "samādhi" in result


def test_lookup_bare_panna():
    result = lookup("panna")
    assert result is not None
    assert "paññā" in result


def test_lookup_bare_sati():
    result = lookup("sati")
    assert result is not None
    assert "sati" in result


def test_lookup_bare_tanha():
    result = lookup("tanha")
    assert result is not None
    assert "taṇhā" in result


def test_lookup_bare_raga():
    result = lookup("raga")
    assert result is not None
    assert "rāga" in result


# --- Part 1: english_hint coverage ---

def test_lookup_english_anicca():
    # hits "Three Marks of Existence" — currently no english_hint
    result = lookup_english("anicca")
    assert result is not None
    assert "impermanent" in result


def test_lookup_english_dukkha():
    # hits "Suffering / dukkha" — currently no english_hint
    result = lookup_english("dukkha")
    assert result is not None
    assert "suffering" in result


def test_lookup_english_nibbana():
    # hits "Nibbāna / liberation" — currently no english_hint
    result = lookup_english("nibbana")
    assert result is not None
    assert "unborn" in result


def test_lookup_english_anatta_hits_three_marks():
    # "anatta" hits Three Marks of Existence first (entry #8)
    result = lookup_english("anatta")
    assert result is not None
    assert "not-self" in result


def test_lookup_english_no_self_hits_not_self_entry():
    # "no self" hits "Not-self / anattā" — currently no english_hint
    result = lookup_english("no self")
    assert result is not None
    assert "not-self" in result


def test_lookup_english_kamma():
    # hits "Kamma / rebirth" — currently no english_hint
    result = lookup_english("kamma")
    assert result is not None
    assert "actions" in result


def test_lookup_english_samadhi():
    # hits "Concentration / samādhi" — currently no english_hint
    result = lookup_english("samadhi")
    assert result is not None
    assert "concentrated" in result


def test_lookup_english_sila():
    # hits "Ethical conduct / sīla" — currently no english_hint
    result = lookup_english("sila")
    assert result is not None
    assert "virtue" in result


def test_lookup_english_panna():
    # hits "Wisdom / insight" — currently no english_hint
    result = lookup_english("panna")
    assert result is not None
    assert "discernment" in result


def test_lookup_english_citta():
    # hits "Mind / citta" via its specific keyword — currently no english_hint
    result = lookup_english("mind is the forerunner")
    assert result is not None
    assert "mind is the forerunner" in result


def test_lookup_english_kilesa():
    # hits "Defilements / kilesa" — currently no english_hint
    result = lookup_english("kilesa")
    assert result is not None
    assert "greed" in result


def test_lookup_english_middle_way():
    # hits "Middle Way" — currently no english_hint
    result = lookup_english("middle way")
    assert result is not None
    assert "two extremes" in result


# --- Part 2: keyword additions to existing entries ---

def test_lookup_three_fires():
    # kilesa entry gets "three fires"
    result = lookup("three fires")
    assert result is not None
    assert "kilesa" in result


def test_lookup_fire_of_greed():
    # kilesa entry gets "fire of greed"
    result = lookup("fire of greed")
    assert result is not None
    assert "kilesa" in result


def test_lookup_three_roots():
    # kilesa entry gets "three roots"
    result = lookup("three roots")
    assert result is not None
    assert "kilesa" in result


def test_lookup_keen():
    # appamāda entry gets "keen"
    result = lookup("keen")
    assert result is not None
    assert "appamāda" in result


def test_lookup_prudent():
    # appamāda entry gets "prudent"
    result = lookup("prudent")
    assert result is not None
    assert "appamāda" in result


def test_lookup_good_conduct():
    # skillful/unskillful entry gets "good conduct"
    result = lookup("good conduct")
    assert result is not None
    assert "kusala" in result


def test_lookup_bad_conduct():
    # skillful/unskillful entry gets "bad conduct"
    result = lookup("bad conduct")
    assert result is not None
    assert "kusala" in result


# --- Part 1: six new Itivuttaka entries ---

def test_lookup_two_nibbana_elements():
    result = lookup("nibbana element")
    assert result is not None
    assert "nibbānadhātu" in result


def test_lookup_english_two_nibbana_elements():
    result = lookup_english("nibbana element")
    assert result is not None
    assert "residue" in result


def test_lookup_hiri():
    result = lookup("hiri")
    assert result is not None
    assert "hirī" in result


def test_lookup_english_hiri():
    result = lookup_english("hiri")
    assert result is not None
    assert "conscience" in result


def test_lookup_grounds_for_merit():
    result = lookup("grounds for merit")
    assert result is not None
    assert "puñña" in result


def test_lookup_english_grounds_for_merit():
    result = lookup_english("grounds for merit")
    assert result is not None
    assert "giving" in result


def test_lookup_sekha():
    result = lookup("sekha")
    assert result is not None
    assert "sekha" in result


def test_lookup_english_sekha():
    result = lookup_english("sekha")
    assert result is not None
    assert "trainee" in result


def test_lookup_elements_of_escape():
    result = lookup("elements of escape")
    assert result is not None
    assert "nissaraṇadhātu" in result


def test_lookup_english_elements_of_escape():
    result = lookup_english("elements of escape")
    assert result is not None
    assert "renunciation" in result


def test_lookup_bhikkhu():
    result = lookup("bhikkhu")
    assert result is not None
    assert "bhikkhu" in result


def test_lookup_english_bhikkhu():
    result = lookup_english("bhikkhu")
    assert result is not None
    assert "monk" in result
    assert "mendicant" in result


def test_lookup_monk():
    # bare "monk" routes to bhikkhu entry
    result = lookup("monk")
    assert result is not None
    assert "bhikkhu" in result

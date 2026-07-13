from data.fetch_thanissaro import convert_file, _COMMENTARY

# Minimal HTML mimicking the dhammatalks epub structure: a <div id="sutta">
# holding the body. The fetch step classifies each prose paragraph as canon
# (no marker) or translator commentary (section="commentary"). See issue #101.


def _convert(body_html: str) -> dict:
    html = (
        "<html><head><title>DN 1 Test | Test Sutta</title></head>"
        f"<body><div id=\"sutta\"><div id=\"DN01\">{body_html}</div></div></body></html>"
    )
    return convert_file(html.encode("utf-8"), "DN", "DN1", "Long Discourses 1")


def test_plain_canon_paragraph_has_no_section_marker():
    result = _convert("<p>Thus have I heard that on one occasion the Blessed One was dwelling.</p>")

    body = result["verses"][2]
    assert "section" not in body
    assert body["english"].startswith("Thus have I heard")


def test_italic_wrapped_paragraph_marked_commentary():
    result = _convert("<p><em>This sutta introduces the Buddha as a practitioner.</em></p>")

    body = result["verses"][2]
    assert body["section"] == _COMMENTARY


def test_partially_italic_paragraph_stays_canon():
    # Only part of the paragraph is italic (e.g. an emphasized word in canon),
    # so it must NOT be classified as commentary.
    result = _convert("<p>Thus have I heard the <em>excellent</em> teaching of the Buddha.</p>")

    body = result["verses"][2]
    assert "section" not in body


def test_introduction_heading_marks_italic_paragraph_under_it():
    body_html = (
        '<h3 class="h2 intro">Introduction</h3>'
        "<p><em>Italic intro paragraph.</em></p>"
        '<h3 class="h2">[ I ]</h3>'
        "<p>Thus have I heard the body of the sutta.</p>"
    )
    result = _convert(body_html)

    assert result["verses"][2]["section"] == _COMMENTARY


def test_introduction_heading_marks_non_italic_paragraph_under_it():
    # The second intro paragraph is NOT italic, so only the Introduction-heading
    # rule catches it — the italics rule alone would miss it.
    body_html = (
        '<h3 class="h2 intro">Introduction</h3>'
        "<p>Non-italic intro paragraph that the heading rule must still catch.</p>"
        '<h3 class="h2">[ I ]</h3>'
        "<p>Thus have I heard the body of the sutta.</p>"
    )
    result = _convert(body_html)

    assert result["verses"][2]["section"] == _COMMENTARY


def test_sutta_body_after_intro_heading_is_canon():
    body_html = (
        '<h3 class="h2 intro">Introduction</h3>'
        "<p><em>Italic intro paragraph.</em></p>"
        '<h3 class="h2">[ I ]</h3>'
        "<p>Thus have I heard the body of the sutta.</p>"
    )
    result = _convert(body_html)
    body_verse = result["verses"][3]

    assert "section" not in body_verse


def test_intro_section_does_not_leak_past_higher_level_heading():
    body_html = (
        '<h3 class="h2 intro">Introduction</h3>'
        "<p>Intro paragraph under the heading.</p>"
        '<h2 class="h2">Section</h2>'
        "<p>Canon paragraph after a higher-level heading closes the intro.</p>"
    )
    result = _convert(body_html)
    verses = result["verses"][2:]

    assert verses[0]["section"] == _COMMENTARY
    assert "section" not in verses[1]
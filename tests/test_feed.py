from app.sync.feed import (
    canonicalize_url,
    clean_description,
    clean_html,
)


def test_clean_html():
    assert clean_html(
        "<p>Hello <strong>world</strong></p>"
    ) == "Hello world"


def test_description_four_sentences():
    source = (
        "One. Two. Three. Four. Five. "
        "The post Example appeared first on JunctionNow."
    )

    assert clean_description(source) == (
        "One. Two. Three. Four..."
    )


def test_tracking_query_removed():
    url = (
        "https://junctionnow.com/story/"
        "?utm_source=discord"
        "&foo=bar"
        "&fbclid=123"
        "#section"
    )

    assert canonicalize_url(url) == (
        "https://junctionnow.com/story/"
        "?foo=bar"
    )

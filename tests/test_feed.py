from app.sync.feed import (
    JunctionNowFeedClient,
    canonicalize_url,
    clean_description,
    clean_html,
    clean_title,
)
from app.sync.types import FeedPost


def test_clean_html():
    assert clean_html(
        "<p>Hello <strong>world</strong></p>"
    ) == "Hello world"


def test_title_removes_redundant_site_suffix():
    assert clean_title("Example story - JunctionNow.com") == "Example story"
    assert clean_title("Example story | JUNCTIONNOW.COM") == "Example story"
    assert clean_title("JunctionNow community update") == "JunctionNow community update"


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


async def test_article_metadata_updates_rendered_post():
    class Response:
        text = """
            <meta property="og:title" content="Updated title">
            <meta property="og:description" content="Updated summary.">
            <article><div class="entry-content">Updated article body.</div></article>
        """

        def raise_for_status(self):
            return None

    class Client:
        async def get(self, *args, **kwargs):
            return Response()

    post = FeedPost(
        post_id="article",
        title="Old title",
        body="Old summary...",
        url="https://junctionnow.com/article/",
        image_url=None,
        published_at=None,
        rss_hash="rss",
        page_hash=None,
    )

    await JunctionNowFeedClient().inspect_article(Client(), post)

    assert post.title == "Updated title"
    assert post.body == "Updated summary..."
    assert post.page_hash

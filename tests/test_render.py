from app.sync.render import (
    build_embed,
    render_hash,
)
from app.sync.types import FeedPost


def make_post():
    return FeedPost(
        post_id="test",
        title="Test",
        body="Example...",
        url=(
            "https://junctionnow.com/test/"
        ),
        image_url=None,
        published_at=None,
        rss_hash="rss",
        page_hash="page",
    )


def test_update_changes_render_hash():
    post = make_post()

    assert render_hash(
        post,
        updated=False,
    ) != render_hash(
        post,
        updated=True,
    )


def test_updated_footer():
    embed = build_embed(
        make_post(),
        updated=True,
    )

    assert (
        embed.footer.text
        == "JunctionNow • Updated"
    )

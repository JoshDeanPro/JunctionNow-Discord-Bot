from app.sync.render import content_hash
from app.sync.types import FeedPost


def make_post(
    body: str = "Hello",
) -> FeedPost:
    return FeedPost(
        post_id="jn-test-1",
        title="Test",
        body=body,
        url="https://junctionnow.com/test",
        image_url=None,
        status="published",
        revision=1,
        published_at=None,
        updated_at=None,
    )


def test_hash_is_stable():
    assert content_hash(make_post()) == content_hash(
        make_post()
    )


def test_hash_changes_when_visible_content_changes():
    assert content_hash(
        make_post("A")
    ) != content_hash(
        make_post("B")
    )

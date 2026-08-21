from app.sync.feed import clean_html, json_posts


def test_clean_html():
    assert clean_html(
        "<p>Hello <strong>world</strong></p>"
    ) == "Hello world"


def test_json_feed_parser():
    posts = json_posts(
        {
            "posts": [
                {
                    "id": "123",
                    "revision": 4,
                    "title": "Hello",
                    "body": "<p>World</p>",
                    "url": "https://junctionnow.com/post/123",
                    "status": "published",
                }
            ]
        }
    )

    assert len(posts) == 1
    assert posts[0].post_id == "123"
    assert posts[0].revision == 4
    assert posts[0].body == "World"

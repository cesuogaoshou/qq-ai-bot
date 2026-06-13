from qq_ai_bot.memory.image_cache import RecentImageCache
from qq_ai_bot.onebot.events import ImageAttachment


def test_recent_image_cache_returns_latest_user_image() -> None:
    cache = RecentImageCache(max_entries=3)

    cache.remember(
        group_id=123456,
        user_id=42,
        images=[ImageAttachment(file="first.image", url="http://example.com/first.jpg")],
    )
    cache.remember(
        group_id=123456,
        user_id=42,
        images=[ImageAttachment(file="second.image", url="http://example.com/second.jpg")],
    )

    images = cache.get_latest(group_id=123456, user_id=42)

    assert images == [ImageAttachment(file="second.image", url="http://example.com/second.jpg")]


def test_recent_image_cache_is_scoped_by_group_and_user() -> None:
    cache = RecentImageCache(max_entries=3)
    cache.remember(
        group_id=123456,
        user_id=42,
        images=[ImageAttachment(file="own.image", url="http://example.com/own.jpg")],
    )
    cache.remember(
        group_id=123456,
        user_id=7,
        images=[ImageAttachment(file="other.image", url="http://example.com/other.jpg")],
    )

    assert cache.get_latest(group_id=123456, user_id=42) == [
        ImageAttachment(file="own.image", url="http://example.com/own.jpg")
    ]
    assert cache.get_latest(group_id=999999, user_id=42) == []

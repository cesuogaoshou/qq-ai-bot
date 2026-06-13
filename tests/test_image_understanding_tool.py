import pytest

from qq_ai_bot.onebot.events import ImageAttachment
from qq_ai_bot.tools.image_understanding import (
    DisabledImageUnderstandingClient,
    ImageUnderstandingDisabledError,
)


@pytest.mark.anyio
async def test_disabled_image_understanding_client_raises_clear_error() -> None:
    client = DisabledImageUnderstandingClient()

    with pytest.raises(ImageUnderstandingDisabledError, match="Image understanding is disabled"):
        await client.describe(
            prompt="看图",
            images=[ImageAttachment(file="abc.image", url="http://example.com/a.jpg")],
            model="",
        )

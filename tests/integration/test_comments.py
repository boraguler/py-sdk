import asyncio

import pytest

from polymarket import AsyncPublicClient, Comment, PublicClient

COMMENT_ID = "1000"


@pytest.mark.integration
def test_get_comment_thread_returns_comments() -> None:
    with PublicClient() as client:
        comments = client.get_comment_thread(COMMENT_ID)

        assert comments
        assert all(isinstance(comment, Comment) for comment in comments)


@pytest.mark.integration
def test_async_get_comment_thread_returns_comments() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            comments = await client.get_comment_thread(COMMENT_ID)

            assert comments
            assert all(isinstance(comment, Comment) for comment in comments)

    asyncio.run(run())

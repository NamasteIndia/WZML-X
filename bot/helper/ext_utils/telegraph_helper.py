import asyncio
from secrets import token_hex
from telegraph.aio import Telegraph as TelegraphApi
from telegraph.exceptions import RetryAfterError

from ... import LOGGER
from ...core.config_manager import Config


class Telegraph:
    def __init__(self, author_name=None, author_url=None):
        self._telegraph = TelegraphApi(domain="graph.org")
        self._author_name = author_name
        self._author_url = author_url

    async def create_account(self):
        LOGGER.info("Creating Telegraph Account")
        try:
            await self._telegraph.create_account(
                short_name=token_hex(5),
                author_name=self._author_name,
                author_url=self._author_url,
            )
        except Exception as e:
            LOGGER.error(f"Failed to create Telegraph Account: {e}")

    async def create_page(self, title, content):
        try:
            return await self._telegraph.create_page(
                title=title,
                author_name=self._author_name,
                author_url=self._author_url,
                html_content=content,
            )
        except RetryAfterError as st:
            LOGGER.warning(
                f"Telegraph Flood control exceeded. Sleeping for {st.retry_after} seconds."
            )
            await asyncio.sleep(st.retry_after)
            return await self.create_page(title, content)

    async def edit_page(self, path, title, content):
        try:
            return await self._telegraph.edit_page(
                path=path,
                title=title,
                author_name=self._author_name,
                author_url=self._author_url,
                html_content=content,
            )
        except RetryAfterError as st:
            LOGGER.warning(
                f"Telegraph Flood control exceeded. Sleeping for {st.retry_after} seconds."
            )
            await asyncio.sleep(st.retry_after)
            return await self.edit_page(path, title, content)

    async def edit_telegraph(self, paths, telegraph_contents):
        """
        Edit multiple Telegraph pages with navigation links (Prev | Next).
        """
        num_of_paths = len(paths)
        for index, content in enumerate(telegraph_contents):
            navigation_links = []
            if index > 0:
                prev_link = f'<b><a href="https://telegra.ph/{paths[index - 1]}">Prev</a></b>'
                navigation_links.append(prev_link)
            if index < num_of_paths - 1:
                next_link = f'<b><a href="https://telegra.ph/{paths[index + 1]}">Next</a></b>'
                navigation_links.append(next_link)
            if navigation_links:
                content += " | ".join(navigation_links)
            await self.edit_page(
                path=paths[index], title="WZML-X Torrent Search", content=content
            )

    async def hibernate(self):
        LOGGER.info("Telegraph: Suspending service...")
        await self.suspend()

    async def shutdown(self):
        LOGGER.info("Telegraph: Shutting down service...")
        await self.stop()

    async def suspend(self):
        # Add real suspension logic here if applicable
        await asyncio.sleep(0.1)

    async def stop(self):
        # Add real shutdown logic here if applicable
        await asyncio.sleep(0.1)


telegraph = Telegraph(Config.AUTHOR_NAME, Config.AUTHOR_URL)


if __name__ == "__main__":
    import asyncio

    async def test():
        await telegraph.create_account()
        page = await telegraph.create_page("Test Title", "<p>Test Content</p>")
        print(f"Created page: https://telegra.ph/{page['path']}")

    asyncio.run(test())

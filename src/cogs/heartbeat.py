import aiohttp
from discord.ext import commands, tasks

import settings


class Heartbeat(commands.Cog):
    """Pings an Uptime Kuma push monitor on a timer to prove the bot is alive
    and connected to Discord (Option B: push/heartbeat monitor)."""

    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger
        self.url = settings.UPTIME_KUMA_URL
        if self.url:
            self.send_heartbeat.start()
        else:
            self.logger.info("Heartbeat disabled: UPTIME_KUMA_URL not set")

    def cog_unload(self) -> None:
        self.send_heartbeat.cancel()
        self.logger.info("Heartbeat cog unloaded")

    @tasks.loop(seconds=60)
    async def send_heartbeat(self):
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.url) as response:
                    response.raise_for_status()
                    self.logger.debug("Heartbeat sent to Uptime Kuma")
        except Exception as e:
            self.logger.warning(f"Failed to send heartbeat to Uptime Kuma: {e}")

    @send_heartbeat.before_loop
    async def before_send_heartbeat(self):
        await self.client.wait_until_ready()


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Heartbeat(client))

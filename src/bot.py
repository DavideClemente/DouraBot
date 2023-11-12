import settings
import discord
from discord.ext import commands
from logic.raffles import gifts_order, create_embed_gifts
import asyncio

logger = settings.logging.getLogger("bot")


def run_bot():
    bot = commands.Bot(command_prefix='??', intents=discord.Intents.default())

    @bot.event
    async def on_ready():
        logger.info(f'User: {bot.user} (ID: {bot.user.id})')
        bot.tree.copy_global_to(guild=settings.DISCORD_GUILD)
        await bot.tree.sync(guild=settings.DISCORD_GUILD)

    @bot.tree.command()
    async def test_message(interaction: discord.Interaction,
                           person1: discord.Member = None,
                           msg: str = ""):
        await interaction.response.defer()
        channel1 = await person1.create_dm()
        await channel1.send(msg)
        await interaction.followup.send("Sent")

    @bot.tree.command()
    async def show_logs(interaction: discord.Interaction, lines: int):
        multiline_string = "############## LOGS ##############".center(100) + "\n"

        #await interaction.response.defer()
        with open(settings.LOG_FILE_PATH, "r") as file:

            lines_list = file.readlines()

            last_lines = lines_list[-lines:]
            multiline_string += "'''" + "\n".join(last_lines) + "'''"
        await interaction.response.send_message(multiline_string)

    @bot.tree.command()
    async def secret_santa(interaction: discord.Interaction,
                           person1: discord.Member = None,
                           person2: discord.Member = None,
                           person3: discord.Member = None,
                           person4: discord.Member = None,
                           person5: discord.Member = None,
                           person6: discord.Member = None,
                           person7: discord.Member = None,
                           person8: discord.Member = None,
                           person9: discord.Member = None,
                           person10: discord.Member = None,
                           person11: discord.Member = None,
                           person12: discord.Member = None,
                           person13: discord.Member = None,
                           person14: discord.Member = None):
        await interaction.response.defer()
        persons_dict = locals().copy()
        persons_dict.pop('interaction')
        participants = [i for i in persons_dict.values() if i is not None]
        list_order = gifts_order(participants)
        descr = """
            O jantar será dia 22 de dezembro
            Orçamento da prendo cabe a cada um
            Local - Almazem do edworld
            Ignorem todas as mensagens anteriores. Isto não é um exercício
        """

        for a, b in list_order:
            try:
                embed = create_embed_gifts("🎅 Secret Santa 🎅", descr, "🎄 Merry Christmas 🎄", a, b)
                channel = await a.create_dm()
                await channel.send(embed=embed)
                logger.info(f'Sent message for {str(a)}')
            except Exception:
                logger.error(f'Error sending message to {a}')
                continue
        await interaction.followup.send("Sent messages. Check logs for possible errors")


    bot.run(settings.DISCORD_TOKEN, root_logger=True)


if __name__ == '__main__':
    run_bot()

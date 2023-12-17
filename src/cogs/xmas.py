import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import ROLES
from logic.raffles import gifts_order, create_embed_gifts
from logic.utilities import is_role_allowed

logger = settings.get_logger()


class xmas(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name='secret_santa', description="Ho ho ho!! Who's gonna be your next secret santa? 🎅")
    @is_role_allowed(ROLES['DOURADINHO_GOD'], ROLES['DOURADINHO_MESTRE'])
    async def secret_santa(self, interaction: discord.Interaction,
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
        '''Ho ho ho!! Who's gonna be your next secret santa? 🎅'''
        await interaction.response.defer()
        persons_dict = locals().copy()
        persons_dict.pop('interaction')
        participants = [i for i in persons_dict.values() if i is not None]
        list_order = gifts_order(participants)
        # modal = SecretSantaModal()
        # await interaction.response.send_modal(modal)
        description = """
            O jantar será dia 22 de dezembro
            Orçamento da prendo cabe a cada um
            Local - Almazem do edworld
            Ignorem todas as mensagens anteriores. Isto não é um exercício
        """
        await self.send_individual_messages(interaction, description, list_order)
        await interaction.followup.send("Sent messages. Check logs for possible errors")

    async def send_individual_messages(self, itr: discord.Interaction, description: str, list: list):
        for a, b in list:
            try:
                embed = create_embed_gifts(
                    "🎅 Secret Santa 🎅", description, "🎄 Merry Christmas 🎄", a, b)
                channel = await a.create_dm()
                await channel.send(embed=embed)
                logger.info(f'Sent message for {str(a)}')
            except Exception:
                logger.error(f'Error sending message to {a}')
                continue
        await itr.followup.send("Sent messages. Check logs for possible errors")

    @secret_santa.error
    async def secret_santa(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            self.logger.info(
                f'User {interaction.user.display_name} tried calling show_logs')
            await interaction.response.send_message('Not allowed!', ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(xmas(client))

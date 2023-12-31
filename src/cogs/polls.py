import discord
import settings
from discord.ext import commands
from discord import app_commands
from settings import DOURADINHOS_COLOR, ROLES
from logic.utilities import is_role_allowed


class Polls(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.get_logger()

    @app_commands.command(name='poll', description="Create a poll with up to 10 options")
    async def poll(self, itr: discord.Interaction,
                   question: str,
                   option_a: str = None,
                   option_b: str = None,
                   option_c: str = None,
                   option_d: str = None,
                   option_e: str = None,
                   option_f: str = None,
                   option_g: str = None,
                   option_h: str = None,
                   option_i: str = None,
                   option_j: str = None):
        """Create a poll with up to 10 options

        Args:
            itr (discord.Interaction): _description_
            question (str): Any question you want
            option_a (str, optional): OptionA.
            option_b (str, optional): optionB.
            option_c (str, optional): optionC.
            option_d (str, optional): optionD.
            option_e (str, optional): optionE.
            option_f (str, optional): optionF.
            option_g (str, optional): optionG.
            option_h (str, optional): optionH.
            option_i (str, optional): optionI.
            option_j (str, optional): optionJ.
        """
        await itr.response.defer()
        try:
            all_arguments: dict = locals().copy()
            all_arguments.pop('itr')
            all_arguments.pop('self')
            emojis = {
                'A': '\U0001F1E6',
                'B': '\U0001F1E7',
                'C': '\U0001F1E8',
                'D': '\U0001F1E9',
                'E': '\U0001F1EA',
                'F': '\U0001F1EB',
                'G': '\U0001F1EC',
                'H': '\U0001F1ED',
                'I': '\U0001F1EE',
                'J': '\U0001F1EF'
            }
            items = all_arguments.items()
            options = [o for o in items if o[1] is not None][1:]
            embed = discord.Embed(
                title=f'📊 {question.strip().capitalize()}', color=discord.Color.from_str(DOURADINHOS_COLOR))
            for o in options:
                letter = o[0][-1].upper()
                emoji = emojis[letter]
                embed.add_field(name=f'{emoji} {o[1]}', value='', inline=False)
            msg = await itr.followup.send(embed=embed)
            for o in options:
                letter = o[0][-1].upper()
                emoji = emojis[letter]
                await msg.add_reaction(emoji)
        except:
            await itr.followup.send('Ocurred some error while processing your command')


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Polls(client))

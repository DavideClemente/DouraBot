import io
import discord
from discord.interactions import Interaction
from database import DatabaseManager
from discord.ext import commands
from discord import app_commands
from settings import get_logger, CARD_API
import requests


RANDOM_CARD_URL = CARD_API + '/deck/new/draw/?count=1'


class GameDropDown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="So...", description="52 questions, unlimited conversation"),
            discord.SelectOption(
                label="Default Card", description="A normal playing card")
        ]
        super().__init__(placeholder="Dropdown menu",
                         min_values=1, max_values=1, options=options)

    async def callback(self, itr: Interaction):
        await itr.response.defer()
        if self.values[0] == "So...":
            await itr.followup.send(file=await self.draw_card(self.values[0]))
        elif self.values[0] == "Default Card":
            response = requests.get(RANDOM_CARD_URL)
            json_response = response.json()

            if json_response['success']:
                embed = discord.Embed()
                embed.set_image(url=json_response['cards'][0]['image'])
                await itr.followup.send(embed=embed)
            else:
                await itr.followup.send_message(f'Error drawing card')
        else:
            await itr.followup.send_message(f'Not implemented')

    async def draw_card(self, gameQuery):
        with DatabaseManager().get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM CARDS WHERE game = %s ORDER BY RAND()", (gameQuery,))
                _, _, byte_array = cursor.fetchall()[0]
                return discord.File(fp=io.BytesIO(
                    byte_array), filename='image.jpg')


class GameView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(GameDropDown())


class Cards(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = get_logger()

    @app_commands.command(name="draw_card", description="Draw a card of a game of your choice")
    async def draw_card(self, itr: discord.Interaction):
        await itr.response.send_message(content="Choose the game", view=GameView())

    # def insert_image(self):
    #     with open("C:\\Users\\Davide\Documents\\ferrari.jpg", "rb") as image:
    #         file = image.read()
    #         byte_array = bytearray(file)
    #         with self.db.cursor() as cursor:
    #             cursor.execute("INSERT INTO CARDS VALUES (%s,%s,%s)",
    #                            (str(uuid.uuid4()), 'So...', byte_array))
    #             self.db.commit()


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Cards(client))

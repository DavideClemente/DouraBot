from interactions import Client, Intents, listen, slash_command, slash_option, SlashContext, OptionType,  ComponentContext, component_callback
from dotenv import load_dotenv
from slash_commands.my_test import teste, test_button
from interactions.api.voice.audio import AudioVolume
import os

load_dotenv()

scope_list = [756505500178448505]

bot = Client(intents=Intents.DEFAULT)
# intents are what events we want to receive from discord, `DEFAULT` is usually fine


@listen()  # this decorator tells snek that it needs to listen for the corresponding event, and run this coroutine
async def on_ready():
    # This event is called when the bot is ready to respond to commands
    print("Ready")
    print(f"This bot is owned by {bot.owner}")


@slash_command(name="gay", description="Comando de teste :)", scopes=scope_list)
async def my_command_function(ctx: SlashContext):
    await ctx.send("Afonso is gay")


@slash_command(name="teste", description="teste de options", scopes=scope_list)
@slash_option(
    name="integer_option",
    description="Integer Option",
    required=True,
    opt_type=OptionType.INTEGER
)
async def teste_function(ctx: SlashContext, integer_option: int):
    await teste(ctx, integer_option)


@slash_command(name="buttons", description="teste de butoes", scopes=scope_list)
async def teste_button(ctx: SlashContext):
    await test_button(ctx)


@component_callback("button_1")
async def bt_callback(ctx: ComponentContext):
    await ctx.send(f"You clicked it!")

# @slash_command("play", description="play a song")
# @slash_option("song",
#               description="The song to play",
#               opt_type=OptionType.STRING,
#               required=True)
# async def play(ctx: SlashContext, song: str):
#     if not ctx.voice_state:
#         await ctx.author.voice.channel.connect()

#     audio = AudioVolume(song)
#     await ctx.send(f'Now playing: ** {song} **')
#     await ctx.voice_state.play(audio)

bot.start(os.getenv("TOKEN"))

from interactions.api.voice.audio import AudioVolume
from interactions import SlashContext


async def play(self, ctx: SlashContext, song: str):
    if not ctx.voice_state:
        await ctx.author.voice.channel.connect()

    audio = await AudioVolume(song)
    await ctx.send(f'Now playing: ** {song} **')
    await ctx.voice_state.play(audio)

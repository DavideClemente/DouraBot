import discord
from discord import app_commands
from discord.ext import commands

import settings
from logic import music_sources
from logic.music_player import GuildPlayer, track_embed
from logic.music_sources import SourceError


async def _reply(itr: discord.Interaction, *args, delete_after: float | None = None, **kwargs):
    """Interaction followup with `delete_after` support (webhooks don't have it)."""
    msg = await itr.followup.send(*args, wait=True, **kwargs)
    if delete_after:
        await msg.delete(delay=delete_after)
    return msg



class QueueView(discord.ui.View):
    def __init__(self, player: GuildPlayer, user: discord.abc.User, page_size: int = 10):
        super().__init__(timeout=120)
        self.player = player
        self.user = user
        self.page_size = page_size
        self.page = 0
        self.message: discord.Message | None = None
        self._update_buttons()

    @property
    def total_pages(self) -> int:
        return max(1, -(-len(self.player.upcoming) // self.page_size))

    def _update_buttons(self):
        self.page = max(0, min(self.page, self.total_pages - 1))
        self.prev_page.disabled = self.page == 0
        self.next_page.disabled = self.page >= self.total_pages - 1

    def embed(self) -> discord.Embed:
        player = self.player
        embed = discord.Embed(title='🎚️ Music queue 🎚️',
                              color=discord.Color.from_str(settings.DOURADINHOS_COLOR))
        if player.index > 0:
            prev = player.tracks[player.index - 1]
            embed.add_field(name='PREVIOUS', value=f'[{prev.title}]({prev.link})'[:1024], inline=False)
        if player.current:
            cur = player.current
            embed.add_field(name='CURRENT', value=f'[{cur.title}]({cur.link})'[:1024], inline=False)

        start = self.page * self.page_size
        first_index = player.index + 1 + start
        lines = [f'{first_index + i}. [{t.title}]({t.link})'
                 for i, t in enumerate(player.upcoming[start:start + self.page_size])]
        text = '\n'.join(lines) or '(no more songs queued)'
        if len(text) > 1024:
            text = text[:1021] + '...'
        embed.add_field(name=f'PLAYING NEXT (page {self.page + 1}/{self.total_pages})',
                        value=text, inline=False)
        embed.set_footer(text=f'{len(player.upcoming)} songs queued'
                              f'{" · shuffle on" if player.shuffle_enabled else ""}')
        return embed

    async def _turn_page(self, itr: discord.Interaction, delta: int):
        if itr.user.id != self.user.id:
            await itr.response.send_message('ℹ️ Use /queue to get your own copy ℹ️', ephemeral=True)
            return
        self.page += delta
        self._update_buttons()
        await itr.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label='Prev', style=discord.ButtonStyle.secondary)
    async def prev_page(self, itr: discord.Interaction, button: discord.ui.Button):
        await self._turn_page(itr, -1)

    @discord.ui.button(label='Next', style=discord.ButtonStyle.secondary)
    async def next_page(self, itr: discord.Interaction, button: discord.ui.Button):
        await self._turn_page(itr, 1)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass


class Music(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.get_logger()
        self.players: dict[int, GuildPlayer] = {}

    async def cog_unload(self):
        for player in list(self.players.values()):
            await player.destroy()

    def _get_player(self, guild: discord.Guild) -> GuildPlayer:
        player = self.players.get(guild.id)
        if player is None:
            player = GuildPlayer(self.client, guild, on_destroy=lambda gid: self.players.pop(gid, None))
            self.players[guild.id] = player
        return player

    async def _active_player(self, itr: discord.Interaction) -> GuildPlayer | None:
        """The guild's player if music is going, otherwise tell the user and return None."""
        player = self.players.get(itr.guild_id)
        if player is None or not player.tracks:
            await _reply(itr, 'ℹ️ There are no songs in the queue ℹ️', ephemeral=True)
            return None
        return player

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        player = self.players.get(member.guild.id)
        if player is None:
            return
        # The bot was disconnected (kicked, /leave, channel deleted...)
        if member.id == self.client.user.id and before.channel and not after.channel:
            await player.destroy()
            return
        # Everyone left the bot's channel
        voice = player.voice
        if voice and voice.channel and before.channel == voice.channel != after.channel:
            if not any(not m.bot for m in voice.channel.members):
                await player.destroy()

    @app_commands.command(name='join', description="join vc")
    async def join(self, itr: discord.Interaction):
        if not itr.user.voice:
            await itr.response.send_message('⚠️ You need to be connected to a voice channel ⚠️')
            return
        await itr.response.defer()
        player = self._get_player(itr.guild)
        player.text_channel = itr.channel
        try:
            await player.connect(itr.user.voice.channel)
        except Exception as e:
            self.logger.exception('Music: could not join voice')
            await _reply(itr, f'⚠️ Could not connect to the channel: {e} ⚠️')
            await player.destroy()
            return
        await _reply(itr, f'🎉 DouraBot has joined {itr.user.voice.channel} 🎉')

    @app_commands.command(name='leave', description="leave voice channel")
    async def leave(self, itr: discord.Interaction):
        player = self.players.get(itr.guild_id)
        if player is None:
            await itr.response.send_message('ℹ️ **DouraBot** is not in a voice channel ℹ️')
            return
        await player.destroy()
        await itr.response.send_message('ℹ️ **DouraBot** has left the voice channel ℹ️')

    @app_commands.command(name='play', description="play a song or playlist (YouTube or Spotify)")
    @app_commands.describe(search='Song name, YouTube link or Spotify track/album/playlist link',
                           shuffle_music='Shuffle the songs before adding them')
    async def play(self, itr: discord.Interaction, search: str = None, shuffle_music: bool = False):
        if not itr.user.voice:
            await itr.response.send_message('⚠️ You need to be connected to a voice channel ⚠️')
            return
        await itr.response.defer()
        self.logger.info(f'User {itr.user.display_name} called play/{search}')

        player = self._get_player(itr.guild)
        player.text_channel = itr.channel

        # No search: resume
        if search is None:
            if player.is_paused:
                player.toggle_pause()
                await player.update_now_playing()
                await _reply(itr, '▶️ Resumed', silent=True, delete_after=5)
            elif not player.upcoming:
                await _reply(itr, '❌ There are no songs to be played in the queue ❌')
            else:
                await _reply(itr, '▶️ Already playing', silent=True, delete_after=5)
            return

        try:
            tracks = await music_sources.search(search, itr.user)
        except SourceError as e:
            self.logger.warning(f'Music: {search!r} failed: {e}')
            await _reply(itr, f'❌ {e} ❌')
            if not player.tracks:
                await player.destroy()
            return

        try:
            await player.connect(itr.user.voice.channel)
        except Exception as e:
            self.logger.exception('Music: could not join voice')
            await _reply(itr, f'⚠️ Could not connect to the voice channel: {e} ⚠️')
            await player.destroy()
            return

        if shuffle_music:
            from random import shuffle
            shuffle(tracks)
        was_idle = not player.is_busy
        player.enqueue(tracks)

        if len(tracks) == 1:
            title = '▶️ Playing' if was_idle else f'📜 Added to queue (#{len(player.tracks) - 1})'
            await _reply(itr, embed=track_embed(title, tracks[0]), silent=True,
                                    delete_after=None if not was_idle else 10)
        else:
            await _reply(itr, f'📜 Added {len(tracks)} songs to the queue 📜', silent=True)

    @app_commands.command(name='queue', description="display the current queue")
    async def queue(self, itr: discord.Interaction):
        await itr.response.defer()
        player = await self._active_player(itr)
        if player is None:
            return
        view = QueueView(player, itr.user)
        view.message = await _reply(itr, embed=view.embed(), view=view, silent=True)

    @app_commands.command(name='clear_queue', description="clear the current queue")
    async def clear_queue(self, itr: discord.Interaction):
        await itr.response.defer()
        player = await self._active_player(itr)
        if player is None:
            return
        player.clear_upcoming()
        await _reply(itr, '🗑️ Queue cleared! 🗑️', silent=True, delete_after=5)

    @app_commands.command(name='skip_to', description="skip to a specific song in the queue")
    @app_commands.describe(index='Song number as shown in /queue')
    async def skip_to(self, itr: discord.Interaction, index: int):
        await itr.response.defer()
        player = await self._active_player(itr)
        if player is None:
            return
        if not 0 <= index < len(player.tracks):
            await _reply(itr, f'❌ Invalid index. Must be between 0 and {len(player.tracks) - 1} ❌')
            return
        if index == player.index and player.is_busy:
            await _reply(itr, 'ℹ️ That song is already playing ℹ️')
            return
        player.jump(index)
        await _reply(itr, f'⏭️ Skipped to song #{index}: **{player.tracks[index].title}**',
                                delete_after=5)

    @app_commands.command(name='move_song', description="move a song to a different position in the queue")
    @app_commands.describe(from_index='Current song number as shown in /queue',
                           to_index='New song number')
    async def move_song(self, itr: discord.Interaction, from_index: int, to_index: int):
        await itr.response.defer()
        player = await self._active_player(itr)
        if player is None:
            return
        last = len(player.tracks) - 1
        if not 0 <= from_index <= last:
            await _reply(itr, f'❌ Invalid source index. Must be between 0 and {last} ❌')
            return
        if not 0 <= to_index <= last:
            await _reply(itr, f'❌ Invalid destination index. Must be between 0 and {last} ❌')
            return
        if from_index == to_index:
            await _reply(itr, 'ℹ️ Source and destination indices are the same ℹ️')
            return
        if from_index == player.index:
            await _reply(itr, '❌ Cannot move the currently playing song ❌')
            return
        track = player.move(from_index, to_index)
        await _reply(itr, f'🔄 Moved "{track.title}" from position {from_index} to {to_index}',
                                delete_after=5)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Music(client))

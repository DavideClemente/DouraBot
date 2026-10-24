import asyncio
import shlex
from random import shuffle

import discord

import settings
from logic.music_sources import SourceError, Track, resolve_stream

# One GuildPlayer per guild. A single asyncio task (`_run`) owns playback:
# it picks the next index, resolves the stream, plays it and waits for it to
# finish. Controls never call `voice.play()` themselves - they set the next
# index and stop the current track, and the loop does the rest. This keeps
# all the state changes in one place and avoids racing the `after` callback.

logger = settings.get_logger()

IDLE_TIMEOUT_SECONDS = 5 * 60

FFMPEG_BEFORE_OPTIONS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin'
FFMPEG_OPTIONS = '-vn -filter:a volume=0.5'


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return '?'
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f'{hours}:{minutes:02}:{secs:02}' if hours else f'{minutes}:{secs:02}'


def track_embed(title: str, track: Track, up_next: Track | None = None) -> discord.Embed:
    embed = discord.Embed(title=title,
                          description=f'[{track.title}]({track.link})',
                          color=discord.Color.from_str(settings.DOURADINHOS_COLOR))
    if track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    embed.add_field(name='Duration', value=format_duration(track.duration))
    if up_next:
        embed.add_field(name='Up next', value=up_next.title[:1024])
    embed.set_footer(text=f'Song added by: {track.requester.display_name}',
                     icon_url=track.requester.display_avatar.url)
    return embed


class GuildPlayer:
    def __init__(self, client: discord.Client, guild: discord.Guild, on_destroy):
        self.client = client
        self.guild = guild
        self.voice: discord.VoiceClient | None = None
        self.text_channel: discord.abc.Messageable | None = None
        self.tracks: list[Track] = []
        self.index = -1  # index of the current (or last played) track
        self.shuffle_enabled = False
        self._unshuffled: list[Track] | None = None
        self._jump_to: int | None = None
        self._wakeup = asyncio.Event()
        self._track_done = asyncio.Event()
        self._now_playing_msg: discord.Message | None = None
        self._on_destroy = on_destroy
        self._destroyed = False
        self._busy = False  # resolving or playing a track (vs idle waiting for one)
        self._task = client.loop.create_task(self._run())

    # ------------------------------------------------------------- state --

    @property
    def current(self) -> Track | None:
        if 0 <= self.index < len(self.tracks) and self._busy:
            return self.tracks[self.index]
        return None

    @property
    def upcoming(self) -> list[Track]:
        return self.tracks[self.index + 1:]

    @property
    def is_busy(self) -> bool:
        """A track is playing, paused or about to start."""
        return self._busy

    @property
    def is_active(self) -> bool:
        return bool(self.voice and (self.voice.is_playing() or self.voice.is_paused()))

    @property
    def is_paused(self) -> bool:
        return bool(self.voice and self.voice.is_paused())

    # ----------------------------------------------------------- voice --

    async def connect(self, channel: discord.VoiceChannel):
        if self.voice and self.voice.is_connected():
            if self.voice.channel != channel:
                await self.voice.move_to(channel)
            return
        self.voice = await channel.connect(self_deaf=True, timeout=30)

    async def destroy(self):
        """Stop everything, leave voice and forget this player."""
        if self._destroyed:
            return
        self._destroyed = True
        self._on_destroy(self.guild.id)
        if self._task is not asyncio.current_task():
            self._task.cancel()
        if self.voice and self.voice.is_connected():
            try:
                await asyncio.wait_for(self.voice.disconnect(force=True), 10)
            except Exception as e:
                logger.warning(f'Music: error disconnecting: {e!r}')
        await self._clear_now_playing()

    # -------------------------------------------------------- controls --

    def enqueue(self, tracks: list[Track]):
        if self.shuffle_enabled:
            tracks = tracks.copy()
            shuffle(tracks)
            if self._unshuffled is not None:
                self._unshuffled.extend(tracks)
        self.tracks.extend(tracks)
        self._wakeup.set()

    def jump(self, index: int):
        """Play tracks[index] next, interrupting the current one."""
        self._jump_to = index
        if self.is_active:
            self.voice.stop()  # the `after` callback lets the loop move on
        self._wakeup.set()

    def skip(self):
        self.jump(self.index + 1)

    def previous(self):
        self.jump(max(self.index - 1, 0))

    def toggle_pause(self) -> bool:
        """Returns True if now paused."""
        if not self.voice:
            return False
        if self.voice.is_paused():
            self.voice.resume()
            return False
        if self.voice.is_playing():
            self.voice.pause()
            return True
        return False

    def toggle_shuffle(self) -> bool:
        """Shuffle/unshuffle the upcoming tracks. Returns True if now enabled."""
        self.shuffle_enabled = not self.shuffle_enabled
        head = self.tracks[:self.index + 1]
        if self.shuffle_enabled:
            self._unshuffled = self.upcoming
            upcoming = self.upcoming
            shuffle(upcoming)
            self.tracks = head + upcoming
        else:
            if self._unshuffled is not None:
                upcoming = self.upcoming
                remaining = set(map(id, upcoming))
                known = set(map(id, self._unshuffled))
                self.tracks = (head + [t for t in self._unshuffled if id(t) in remaining]
                               + [t for t in upcoming if id(t) not in known])
            self._unshuffled = None
        return self.shuffle_enabled

    def clear_upcoming(self):
        del self.tracks[self.index + 1:]
        if self._unshuffled is not None:
            self._unshuffled = []

    def move(self, from_index: int, to_index: int) -> Track:
        track = self.tracks.pop(from_index)
        self.tracks.insert(to_index, track)
        if from_index < self.index <= to_index:
            self.index -= 1
        elif to_index <= self.index < from_index:
            self.index += 1
        return track

    # ------------------------------------------------------ playback loop --

    def _next_index(self) -> int:
        if self._jump_to is not None:
            target, self._jump_to = self._jump_to, None
            return target
        return self.index + 1

    async def _run(self):
        try:
            while True:
                target = self._next_index()
                if target >= len(self.tracks):
                    if not await self._wait_for_tracks():
                        return
                    continue

                self.index = target
                self._busy = True
                track = self.tracks[target]
                try:
                    stream = await resolve_stream(track)
                except SourceError as e:
                    logger.warning(f'Music: skipping {track.title!r}: {e}')
                    await self._send(f'⚠️ Skipping **{track.title}**: {e}', delete_after=15)
                    continue
                if self._jump_to is not None:
                    continue  # user skipped while we were resolving
                if not (self.voice and self.voice.is_connected()):
                    return

                before_options = FFMPEG_BEFORE_OPTIONS
                if track.user_agent:
                    before_options += f' -user_agent {shlex.quote(track.user_agent)}'
                self._track_done.clear()
                self.voice.play(
                    discord.FFmpegOpusAudio(stream, before_options=before_options,
                                            options=FFMPEG_OPTIONS),
                    after=self._after_track)
                logger.info(f'Music: playing {track.title!r} ({track.url})')
                await self.update_now_playing(repost=True)
                self.client.loop.create_task(self._prefetch(target + 1))
                await self._track_done.wait()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Music: player loop crashed')
            await self._send('❌ The music player crashed, leaving the voice channel ❌')
        finally:
            if not self._destroyed:
                self.client.loop.create_task(self.destroy())

    def _after_track(self, error: Exception | None):
        # Called from the audio thread
        if error:
            logger.error(f'Music: playback error: {error}')
        self.client.loop.call_soon_threadsafe(self._track_done.set)

    async def _wait_for_tracks(self) -> bool:
        """Idle until something is queued. False if we timed out and should leave."""
        self._busy = False
        await self._clear_now_playing()
        self._wakeup.clear()
        # Re-check: something may have been queued while clearing the message
        if self._jump_to is not None or self.index + 1 < len(self.tracks):
            return True
        try:
            await asyncio.wait_for(self._wakeup.wait(), IDLE_TIMEOUT_SECONDS)
            return True
        except asyncio.TimeoutError:
            await self._send('👋 Nothing left to play, leaving the voice channel', delete_after=30)
            return False

    async def _prefetch(self, index: int):
        """Resolve the next stream early so the gap between songs is short."""
        if index >= len(self.tracks):
            return
        try:
            await resolve_stream(self.tracks[index])
        except SourceError:
            pass  # reported when we actually get to it

    # ------------------------------------------------------- messages --

    async def _send(self, content: str, **kwargs):
        if not self.text_channel:
            return None
        try:
            return await self.text_channel.send(content, silent=True, **kwargs)
        except discord.HTTPException as e:
            logger.warning(f'Music: could not send message: {e}')
            return None

    async def update_now_playing(self, repost: bool = False):
        """Refresh the now playing message. `repost` sends a new one (with the
        control buttons) at the bottom of the chat instead of editing in place."""
        track = self.current
        if not track or not self.text_channel:
            return
        title = '⏸️ Paused' if self.is_paused else '▶️ Now playing'
        upcoming = self.upcoming
        embed = track_embed(title, track, upcoming[0] if upcoming else None)
        if self.shuffle_enabled:
            embed.add_field(name='Shuffle', value='🔀 on')
        if self._now_playing_msg and not repost:
            try:
                await self._now_playing_msg.edit(embed=embed)
                return
            except discord.HTTPException:
                pass  # deleted by someone, post a new one
        await self._clear_now_playing()
        try:
            self._now_playing_msg = await self.text_channel.send(
                embed=embed, view=PlayerControls(self), silent=True)
        except discord.HTTPException as e:
            logger.warning(f'Music: could not send now playing message: {e}')

    async def _clear_now_playing(self):
        msg, self._now_playing_msg = self._now_playing_msg, None
        if msg:
            try:
                await msg.delete()
            except discord.HTTPException:
                pass


class PlayerControls(discord.ui.View):
    def __init__(self, player: GuildPlayer):
        super().__init__(timeout=None)
        self.player = player

    async def interaction_check(self, itr: discord.Interaction) -> bool:
        voice = self.player.voice
        if not (voice and itr.user.voice and itr.user.voice.channel == voice.channel):
            await itr.response.send_message('❌ You need to be in my voice channel to do that ❌',
                                            ephemeral=True)
            return False
        return True

    @discord.ui.button(emoji='⏮️', style=discord.ButtonStyle.secondary)
    async def previous_button(self, itr: discord.Interaction, button: discord.ui.Button):
        await itr.response.defer()
        self.player.previous()

    @discord.ui.button(emoji='⏯️', style=discord.ButtonStyle.secondary)
    async def play_pause_button(self, itr: discord.Interaction, button: discord.ui.Button):
        paused = self.player.toggle_pause()
        await itr.response.defer()
        await self.player.update_now_playing()
        await self.player._send(f'⏯️ Audio {"paused" if paused else "resumed"} by {itr.user.display_name}',
                                delete_after=5)

    @discord.ui.button(emoji='⏭️', style=discord.ButtonStyle.secondary)
    async def next_button(self, itr: discord.Interaction, button: discord.ui.Button):
        await itr.response.defer()
        if not self.player.upcoming:
            await itr.followup.send('ℹ️ There is no next song in the queue ℹ️', ephemeral=True)
            return
        self.player.skip()

    @discord.ui.button(emoji='🔀', style=discord.ButtonStyle.secondary)
    async def shuffle_button(self, itr: discord.Interaction, button: discord.ui.Button):
        enabled = self.player.toggle_shuffle()
        await itr.response.defer()
        await self.player.update_now_playing()
        await self.player._send(f'{"🔀 Shuffle enabled" if enabled else "➡️ Shuffle disabled"} '
                                f'by {itr.user.display_name}', delete_after=5)

    @discord.ui.button(emoji='⏹️', style=discord.ButtonStyle.danger)
    async def stop_button(self, itr: discord.Interaction, button: discord.ui.Button):
        await itr.response.defer()
        await self.player._send(f'⏹️ Stopped by {itr.user.display_name}', delete_after=10)
        await self.player.destroy()

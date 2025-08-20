import asyncio
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib import parse, request

import discord
from discord import app_commands
from discord.ext import commands
from yt_dlp import YoutubeDL

from random import shuffle
import settings
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import subprocess

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=settings.SPOTIFY_CLIENT_ID,
    client_secret=settings.SPOTIFY_CLIENT_SECRET
))

ytdl_format_options = {
    #'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'noplaylist': False,
    'no_warnings': True,
    'default_search': 'auto',
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
}

FAST_PLAYLIST_OPTS = {
    **ytdl_format_options,
    "noplaylist": False,              # allow playlist container
    "extract_flat": "in_playlist",    # <-- key speedup: don't resolve each entry
    "skip_download": True,
}

SINGLE_OPTS = {
    **ytdl_format_options,
    "noplaylist": True,               # only a single video
    "format": "bestaudio/best",
}


ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 256k'
}

def _yt_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"

def _yt_thumb(video_id: str) -> str:
    # safe default if yt-dlp entry lacks thumbnails
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

def _get_sp_playlist_id(url: str) -> str:
    return url.split("/")[-1].split("?")[0]

def _get_sp_album_id(url: str) -> str:
    return url.split("/")[-1].split("?")[0]


def _pick_thumbnail(info: dict) -> str | None:
    if info.get("thumbnail"):
        return info["thumbnail"]
    thumbs = info.get("thumbnails") or []
    if thumbs:
        best = max(thumbs, key=lambda t: (t.get("width") or 0, t.get("height") or 0))
        return best.get("url")
    vid = info.get("id")
    return _yt_thumb(vid) if vid else None


def _pick_best_stream(info: dict) -> str | None:
    fmts = info.get("formats") or []
    if not fmts:
        return None
    # Prefer audio-only
    audio_only = [f for f in fmts if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
    # 1) Opus/WebM
    opus = [f for f in audio_only if f.get("acodec") == "opus" or f.get("ext") == "webm"]
    if opus:
        return max(opus, key=lambda f: (f.get("abr") or 0, f.get("tbr") or 0)).get("url")
    # 2) M4A/MP4 (HLS audio like itag 233/234)
    m4a = [f for f in audio_only if f.get("ext") in ("m4a", "mp4")]
    if m4a:
        return max(m4a, key=lambda f: (f.get("abr") or 0, f.get("tbr") or 0)).get("url")
    # 3) Any audio-only
    if audio_only:
        return max(audio_only, key=lambda f: (f.get("abr") or 0, f.get("tbr") or 0)).get("url")
    # 4) Any A/V that includes audio
    av = [f for f in fmts if f.get("acodec") not in (None, "none")]
    if av:
        return max(av, key=lambda f: (f.get("tbr") or 0, f.get("abr") or 0)).get("url")
    return None

def _is_playlist_url(url: str) -> bool:
    # treat "pure" playlist links as playlists; 'watch?v=...' stays a single video
    return ("youtube.com/playlist?list=" in url) or (
        "list=" in url and "watch?v=" not in url
    )

def create_playing_embed(title, author: discord.User, song):
    if not song:  # Check if the song list is empty
        raise ValueError("The song list is empty. Cannot create an embed.")
    if type(song) is list:
        song = song[0]
    embed = discord.Embed(title=title,
                          description=f'[{song["title"]}]({song["link"]})',
                          color=discord.Color.from_str(
                              settings.DOURADINHOS_COLOR)
                          )
    embed.set_thumbnail(url=song["thumbnail"])
    embed.set_footer(
        text=f'Song added by: {str(author)}', icon_url=author.avatar.url)
    return embed


async def add_reactions(msg: discord.Message):
    await asyncio.gather(
        msg.add_reaction('⏮️'),
        msg.add_reaction('⏯️'),
        msg.add_reaction('⏭️')
    )


async def delete_message(msg: discord.Message):
    await asyncio.sleep(5)
    await msg.delete()


def is_spotify_url(url):
    return "open.spotify.com" in url or "spotify.com" in url


def get_spotify_track_info(url):
    track = sp.track(url)
    title = track['name']
    artist = track['artists'][0]['name']
    return f"{title} {artist}"


def is_spotify_playlist(url):
    return "playlist" in url


def is_spotify_album(url):
    return "album" in url


def get_spotify_url_data(url):
    """Convert Spotify URL to YouTube URL

    Args:
        url (str): Spotify URL

    Returns:
        str: YouTube URL
    """

    if is_spotify_playlist(url):
        playlist_id = url.split("/")[-1].split("?")[0]
        raw_results = sp.playlist_items(playlist_id, market='PT')
        results = [f"{track['track']['name']} {track['track']['artists'][0]['name']}" for track in raw_results['items']]
    elif is_spotify_album(url):
        album_id = url.split("/")[-1].split("?")[0]
        album_tracks = sp.album_tracks(album_id)
        results = [
            f"{track['name']} {track['artists'][0]['name']}" for track in album_tracks['items']
        ]
    else:
        results = [get_spotify_track_info(url)]
    return results


class Music(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.get_logger()
        self.queue = []
        self.queue_index = 0
        self.is_playing = False
        self.is_connected = False
        self.voice_client: discord.VoiceClient = None
        self.executor = ThreadPoolExecutor()
        self.last_played_msg = None
        self.me_id = self.client.user.id
        self.inactivity_timer: threading.Timer = None

    async def clear(self):
        self.is_playing = False
        self.queue = []
        self.queue_index = 0

    async def disconnect(self):
        self.is_playing = False
        self.queue = []
        self.queue_index = 0
        await self.voice_client.disconnect()
        self.voice_client = None

    def in_voice_channel(self):
        return self.voice_client is not None

    def exists_next_song_in_queue(self):
        return self.queue_index + 1 < len(self.queue)

    def not_me(self, member: discord.Member):
        return member.id != self.client.user.id

    def start_inactivity_timer(self, minutes: int):
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        self.inactivity_timer = threading.Timer(minutes * 60, self.run_disconnect_coroutine)
        self.inactivity_timer.start()

    def run_disconnect_coroutine(self):
        asyncio.run_coroutine_threadsafe(self.disconnect(), self.client.loop)

    def reset_inactivity_timer(self):
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
            self.inactivity_timer = None

    def clean_queue(self):
        # Remove the song if it is 3 places down the queue
        if self.queue_index > 2:
            self.queue.pop(self.queue_index - 3)
            self.queue_index -= 1  # Adjust index to keep it in sync

    def get_current_song_from_queue(self):
        return self.queue[self.queue_index]['song']

    def get_previous_song(self):
        return self.queue[
            self.queue_index - 1]['song'] if len(self.queue) > 1 and self.queue_index >= 1 else None

    def is_queue_empty(self):
        return len(self.queue) == 0

    def clear_queue_impl(self):
        current_music = self.get_current_song_from_queue()
        if self.queue_index > 0:
            self.queue = [current_music]
            self.queue_index = 0

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        # Check if disconnected from discord
        if member == self.client.user and before.channel and not after.channel:
            await self.clear()
        if self.not_me(member) and before.channel is not None and after.channel != before.channel:
            remaining_member = before.channel.members
            if len(remaining_member) == 1 and remaining_member[0].id == self.me_id and self.voice_client.is_connected():
                await self.disconnect()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user != self.client.user:
            # Next
            channel = self.client.get_channel(reaction.message.channel.id)
            if reaction.emoji == '⏭️':
                await self.reaction_next(channel, reaction, user)
            # Previous
            elif reaction.emoji == '⏮️':
                await self.reaction_previous(channel, reaction, user)
            # Play/Pause
            elif reaction.emoji == '⏯️':
                await self.reaction_play_pause(channel, reaction, user)

    async def reaction_next(self, channel: discord.TextChannel, reaction: discord.Reaction, user: discord.User):
        msg = None
        if not self.in_voice_channel():
            msg = await channel.send("❌ You need to be in a voice channel to you this command ❌")
        elif not self.exists_next_song_in_queue():
            msg = await channel.send("ℹ️ There is no next song in the queue. Replaying current song ℹ️")
            self.voice_client.pause()
            await self.play_music(reaction.message.channel.id, user)
            self.reset_inactivity_timer()
        else:
            self.queue_index += 1
            self.voice_client.pause()
            played = await self.play_music(reaction.message.channel.id, user)
            if not played:
                msg = await channel.send('⚠️ There are no songs to be played in the queue ⚠️')
            else:
                self.clean_queue()
                self.reset_inactivity_timer()
        if msg:
            await delete_message(msg)

    async def reaction_previous(self, channel: discord.TextChannel, reaction: discord.Reaction, user: discord.User):
        msg = None
        if not self.voice_client:
            msg = await channel.send("❌ You need to be in a voice channel to use this command ❌")
        elif self.queue_index <= 0:
            msg = await channel.send("ℹ️ There is no previous song in the queue. Replaying current song ℹ️")
            self.voice_client.pause()
            await self.play_music(reaction.message.channel.id, user)
            self.reset_inactivity_timer()
        else:
            self.queue_index -= 1
            self.voice_client.pause()
            played = await self.play_music(reaction.message.channel.id, user)
            if not played:
                msg = await channel.send('⚠️ There are no songs to be played in the queue ⚠️')
        if msg:
            await delete_message(msg)

    async def reaction_play_pause(self, channel: discord.TextChannel, reaction: discord.Reaction, user: discord.User):
        msg = None
        if not self.voice_client:
            msg = await channel.send("⚠️ There is no audio to be paused at the moment ⚠️")
        elif self.is_playing:
            msg = await channel.send(f"⏯️ Audio Paused by {user.display_name}")
            self.is_playing = False
            self.voice_client.pause()
            self.start_inactivity_timer(5)
        else:
            msg = await channel.send(f"⏯️ Audio Resumed by {user.display_name}")
            self.is_playing = True
            self.voice_client.resume()
            self.reset_inactivity_timer()
        await reaction.message.clear_reactions()
        await add_reactions(reaction.message)
        if msg:
            await delete_message(msg)

    async def join_voice_channel(self, text_channel, voice_channel):
        """Join a voice channel

        Args:
            :param voice_channel: Channel to send messages to
            :param text_channel: Channel to join
        """
        # Check if already connected to a channel
        if self.voice_client is None or not self.voice_client.is_connected():
            # Try to connect to the channel
            self.voice_client = await voice_channel.connect()
            if self.voice_client is None:
                channel = self.client.get_channel(text_channel)
                await channel.send('⚠️ Could not connect to the channel ⚠️')
        else:
            # Move to channel
            await self.voice_client.move_to(voice_channel)

    async def pause(self, itr: discord.Interaction):
        if not self.voice_client:
            await itr.response.send_message('❌ There is no audio playing at the moment ❌')
        elif self.is_playing:
            self.is_playing = False
            self.voice_client.pause()

    async def play_next(self, user: discord.User):
        """Plays the next song asynchronously"""

        if not self.is_playing:
            return

        if self.exists_next_song_in_queue():
            self.is_playing = True
            self.queue_index += 1

            song = self.get_current_song_from_queue()
            message = create_playing_embed("▶️ Now playing", user, song)

            channel = self.client.get_channel(self.last_played_msg.channel.id)

            # Delete the last message asynchronously
            if self.last_played_msg:
                try:
                    await self.last_played_msg.delete()
                except Exception as e:
                    print(f"Error deleting last message: {e}")

            # Send new playing message
            try:
                self.last_played_msg = await channel.send(embed=message, silent=True)
            except Exception as e:
                print(f"Error sending playing message: {e}")

            # Add reactions asynchronously
            try:
                await add_reactions(self.last_played_msg)
            except Exception as e:
                print(f"Error adding reactions: {e}")

            self.clean_queue()
            # Play next song
            self.play_audio(user, song)

        else:
            self.queue_index += 1
            self.is_playing = False

    async def _sp_fetch_playlist_page(self, playlist_id: str, offset: int, limit: int = 100, market: str = "PT"):
        loop = asyncio.get_event_loop()

        def run():
            # Only the fields we need = faster + smaller payload
            return sp.playlist_items(
                playlist_id, market=market, limit=limit, offset=offset,
                fields="items(track(name,artists(name))),total,next"
            )

        return await loop.run_in_executor(self.executor, run)

    async def _sp_fetch_album_page(self, album_id: str, offset: int, limit: int = 50, market: str = "PT"):
        loop = asyncio.get_event_loop()

        def run():
            return sp.album_tracks(
                album_id, market=market, limit=limit, offset=offset
            )

        return await loop.run_in_executor(self.executor, run)

    async def _yt_url_from_query(self, query: str) -> str | None:
        """Use your existing search_youtube() to get a single watch URL."""
        res = await self.search_youtube(query)
        return res[0] if res else None

    async def enqueue_spotify_playlist_progressive(self, url: str, user_channel, channel_to_notify,
                                                   shuffle_music: bool = False) -> int:
        """
        Enqueue first Spotify track now (mapped to YouTube), then resolve the rest in the background.
        Works for both playlist and album URLs.
        """
        is_playlist = is_spotify_playlist(url)
        is_album = is_spotify_album(url)

        if not (is_playlist or is_album):
            return 0

        # ---- 1) Fetch first track only
        if is_playlist:
            pid = _get_sp_playlist_id(url)
            head = await self._sp_fetch_playlist_page(pid, offset=0, limit=1)
            items = head.get("items") or []
            if not items or not items[0].get("track"):
                await channel_to_notify.send("❌ Could not read this Spotify playlist ❌")
                return 0
            t0 = items[0]["track"]
        else:
            aid = _get_sp_album_id(url)
            head = await self._sp_fetch_album_page(aid, offset=0, limit=1)
            items = head.get("items") or []
            if not items:
                await channel_to_notify.send("❌ Could not read this Spotify album ❌")
                return 0
            t0 = items[0]

        q0 = f'{t0["name"]} {t0["artists"][0]["name"]}'
        yt0 = await self._yt_url_from_query(q0)
        if not yt0:
            await channel_to_notify.send(f"❌ Could not find a YouTube match for **{q0}** ❌")
            return 0

        # Build first song (no pre-resolved source to avoid URL expiry)
        vid0 = yt0.split("v=")[-1].split("&")[0] if "v=" in yt0 else yt0.rsplit("/", 1)[-1]
        first_song = {
            "link": yt0,
            "thumbnail": _yt_thumb(vid0),
            "original_url": yt0,
            "source": None,  # resolve right before playback
            "title": q0,  # use Spotify title/artist now; YouTube title will be resolved on play
        }
        self.queue.append({"song": first_song, "channel": user_channel})

        # ---- 2) Background task: map the remaining tracks to YouTube and append
        async def fetch_rest_spotify():
            try:
                added = 0
                if is_playlist:
                    total = head.get("total") or 0
                    offset = 1
                    page_size = 100
                    while offset < total:
                        page = await self._sp_fetch_playlist_page(pid, offset=offset, limit=page_size)
                        entries = page.get("items") or []
                        queries = [f'{it["track"]["name"]} {it["track"]["artists"][0]["name"]}'
                                   for it in entries if it and it.get("track")]
                        batch_songs = await self._resolve_queries_to_songs(queries, shuffle_music)
                        for s in batch_songs:
                            self.queue.append({"song": s, "channel": user_channel})
                        added += len(batch_songs)
                        offset += page_size
                else:
                    total = head.get("total") or 0
                    offset = 1
                    page_size = 50
                    while offset < total:
                        page = await self._sp_fetch_album_page(aid, offset=offset, limit=page_size)
                        entries = page.get("items") or []
                        queries = [f'{it["name"]} {it["artists"][0]["name"]}' for it in entries if it]
                        batch_songs = await self._resolve_queries_to_songs(queries, shuffle_music)
                        for s in batch_songs:
                            self.queue.append({"song": s, "channel": user_channel})
                        added += len(batch_songs)
                        offset += page_size

                if added:
                    await channel_to_notify.send(f"📜 Added +{added} more from Spotify.")
            except Exception as ex:
                self.logger.exception("Background Spotify mapping failed: %s", ex)

        self.client.loop.create_task(fetch_rest_spotify())
        return 1

    async def _resolve_queries_to_songs(self, queries: list[str], shuffle_music: bool) -> list[dict]:
        """Map a list of 'title artist' queries to song dicts using your YouTube search, with modest concurrency."""
        # Concurrency limiter to be nice to YouTube and your host
        sem = asyncio.Semaphore(6)

        async def process(q: str) -> dict | None:
            async with sem:
                try:
                    yt_url = await self._yt_url_from_query(q)
                    if not yt_url:
                        return None
                    vid = yt_url.split("v=")[-1].split("&")[0] if "v=" in yt_url else yt_url.rsplit("/", 1)[-1]
                    return {
                        "link": yt_url,
                        "thumbnail": _yt_thumb(vid),
                        "original_url": yt_url,
                        "source": None,  # resolve at play time
                        "title": q,  # keep Spotify title/artist label; avoids extra extraction per item
                    }
                except Exception as e:
                    self.logger.warning("Failed mapping '%s': %s", q, e)
                    return None

        # Process in chunks to avoid giant gather on huge playlists
        out: list[dict] = []
        CHUNK = 25
        for i in range(0, len(queries), CHUNK):
            chunk = queries[i:i + CHUNK]
            results = await asyncio.gather(*(process(q) for q in chunk))
            items = [r for r in results if r]
            if shuffle_music:
                from random import shuffle as _shuffle
                _shuffle(items)
            out.extend(items)
        return out

    async def resolve_stream(self, watch_url: str) -> str | None:
        loop = asyncio.get_event_loop()

        def run():
            from yt_dlp import YoutubeDL
            with YoutubeDL({**ytdl_format_options, "noplaylist": True, "format": "bestaudio/best"}) as yt:
                return yt.extract_info(watch_url, download=False)

        try:
            info = await loop.run_in_executor(self.executor, run)
        except Exception as e:
            self.logger.warning(f"resolve_stream failed: {e}")
            return None
        if not info:
            return None
        # Try top-level url, else pick a format
        fmts = info.get("formats") or []
        if info.get("url"):
            return info["url"]
        # fall back to any audio-only format
        audio_only = [f for f in fmts if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
        if audio_only:
            best = max(audio_only, key=lambda f: (f.get("abr") or 0, f.get("tbr") or 0))
            return best.get("url")
        return None

    def play_audio(self, user, song):
        def play_next_callback(e):
            asyncio.run_coroutine_threadsafe(self.play_next(user), self.client.loop)

        async def play_audio_thread():
            source_url = song['source']
            if source_url is None:
                source_url = await self.resolve_stream(song['original_url'])
                if not source_url:
                    self.logger.warning("Could not resolve stream for %s", song['original_url'])
                    return
            self.voice_client.play(discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(source_url, **ffmpeg_options), volume=0.5
            ), after=play_next_callback)

        self.client.loop.create_task(play_audio_thread())

    async def play_music(self, channel_id, user):
        """Plays a song

        Args:
            channel_id (_type_): Channel where to send messages to
            user (_type_): User who played the song

        Returns:
            _type_: _description_
        """
        if self.queue_index < len(self.queue):
            self.is_playing = True
            channel = self.client.get_channel(channel_id)
            await self.join_voice_channel(channel, self.queue[self.queue_index]['channel'])
            song = self.get_current_song_from_queue()

            if self.last_played_msg:
                await self.last_played_msg.delete()

            embed = create_playing_embed("▶️ Now playing", user, song)
            msg = await channel.send(embed=embed, silent=True)
            self.last_played_msg = msg
            await add_reactions(msg)

            self.play_audio(user, song)
            return True
        else:
            self.queue_index += 1
            self.is_playing = False
            return False

    @app_commands.command(name='join', description="join vc")
    async def join(self, itr: discord.Interaction):
        """Join your voice channel

        Args:
            itr (discord.Interaction): Discord interaction
        """
        if itr.user.voice:
            user_channel = itr.user.voice.channel
            await self.join_voice_channel(itr, user_channel)
            await itr.response.send_message(f'🎉 DouraBot has joined {user_channel} 🎉')
        else:
            await itr.response.send_message('⚠️ You need to be connected to a voice channel ⚠️')

    @app_commands.command(name='leave', description="leave voice channel")
    async def leave(self, itr: discord.Interaction):
        """Leave your voice channel

        Args:
            itr (discord.Interaction): Discord interaction
        """
        if self.in_voice_channel():
            await self.disconnect()
            self.voice_client = None
            await itr.response.send_message('ℹ️ **DouraBot** has left the voice channel ℹ️')
        else:
            await itr.response.send_message('ℹ️ **DouraBot** is not in a voice channel ℹ️')

    async def _ydl_flat(self, url: str, playlist_items: str | None = None):
        loop = asyncio.get_event_loop()

        def run():
            opts = {
                **ytdl_format_options,
                "extract_flat": "in_playlist",  # <-- the speedup
                "noplaylist": False,
                "skip_download": True,
                "quiet": True,
                "no_warnings": True,
            }
            if playlist_items:
                opts["playlist_items"] = playlist_items  # e.g., "1" or "2-"
            from yt_dlp import YoutubeDL
            with YoutubeDL(opts) as yt:
                return yt.extract_info(url, download=False)

        try:
            return await loop.run_in_executor(self.executor, run)
        except Exception as e:
            self.logger.error(f"_ydl_flat error: {e}")
            return None

    async def enqueue_playlist_progressive(self, playlist_url: str, user_channel,
                                           channel_to_notify: discord.abc.Messageable,
                                           shuffle_music: bool = False) -> int:
        """Enqueue first track now; fetch remaining items in the background."""
        # 1) Get only the first playlist entry (flat, instant)
        head = await self._ydl_flat(playlist_url, playlist_items="1")
        if not head or not head.get("entries"):
            await channel_to_notify.send("❌ Could not read this playlist ❌")
            return 0

        first = head["entries"][0]
        vid = first.get("id")
        link = first.get("webpage_url") or first.get("url")
        if not (link and link.startswith("http")):
            link = _yt_watch_url(vid) if vid else playlist_url

        first_song = {
            "link": link,
            "thumbnail": _pick_thumbnail(first) or _yt_thumb(vid or ""),
            "original_url": link,
            "source": None,  # resolve right before playback (your play_audio already does this)
            "title": first.get("title"),
        }
        self.queue.append({"song": first_song, "channel": user_channel})
        added_count = 1

        # 2) Background task: fetch the rest ("2-" means from 2 to end) and append
        async def fetch_rest():
            try:
                rest = await self._ydl_flat(playlist_url, playlist_items="2-")
                entries = (rest or {}).get("entries") or []
                items = []
                for e in entries:
                    if not e:
                        continue
                    vid2 = e.get("id")
                    l2 = e.get("webpage_url") or e.get("url")
                    if not (l2 and l2.startswith("http")):
                        l2 = _yt_watch_url(vid2) if vid2 else playlist_url
                    items.append({
                        "link": l2,
                        "thumbnail": _pick_thumbnail(e) or _yt_thumb(vid2 or ""),
                        "original_url": l2,
                        "source": None,  # resolve later
                        "title": e.get("title"),
                    })

                if shuffle_music:
                    from random import shuffle as _shuffle
                    _shuffle(items)

                # Extend queue on the event loop
                for s in items:
                    self.queue.append({"song": s, "channel": user_channel})

                if items:
                    await channel_to_notify.send(
                        f"📜 Added +{len(items)} more from the playlist (total now {len(items) + 1}).")
            except Exception as ex:
                self.logger.exception("Background playlist fetch failed: %s", ex)

        self.client.loop.create_task(fetch_rest())
        return added_count

    async def search_youtube(self, q: str):
        if "youtube.com/" in q or "youtu.be/" in q or "playlist?list=" in q:
            return [q]
        loop = asyncio.get_event_loop()

        def run():
            from yt_dlp import YoutubeDL
            with YoutubeDL({"quiet": True, "noplaylist": True}) as yt:
                return yt.extract_info(f"ytsearch1:{q}", download=False)

        info = await loop.run_in_executor(self.executor, run)
        e = (info.get("entries") or [None])[0] if info else None
        return [e.get("webpage_url")] if e else []

    # async def search_youtube(self, search: str):
    #     """Searches YouTube for results based on url or search params
    #
    #     Args:
    #         search (str): Url/ Search Params
    #
    #     Returns:
    #         _type_: YouTube results
    #     """
    #     loop = asyncio.get_event_loop()
    #
    #     # If it's a valid Youtube URL, return it
    #     if "youtube.com/watch?v=" in search or "youtu.be/" in search:
    #         return [search]
    #
    #     # If it's a playlist, return directly
    #     if "youtube.com/playlist?list=" in search:
    #         return [search]
    #
    #     # Otherwise, search for the song
    #     query_string = parse.urlencode({'search_query': search})
    #     content = await loop.run_in_executor(self.executor,
    #                                          request.urlopen, f'https://www.youtube.com/results?{query_string}')
    #     content = content.read().decode()
    #
    #     # Detect video and playlist results
    #     video_results = re.findall(r'/watch\?v=(.{11})', content)
    #     playlist_results = re.findall(r'/playlist\?list=([a-zA-Z0-9_-]+)', content)
    #
    #     results = []
    #     if video_results:
    #         results.append(f"https://www.youtube.com/watch?v={video_results[0]}")
    #     if playlist_results:
    #         results.append(f"https://www.youtube.com/playlist?list={playlist_results[0]}")
    #
    #     return results[:1]

    async def extract_youtube(self, url: str):
        loop = asyncio.get_event_loop()

        def run_fast_or_single():
            # Treat pure playlist URLs as playlists; watch URLs stay single
            is_playlist = ("playlist?list=" in url) or ("list=" in url and "watch?v=" not in url)
            opts = FAST_PLAYLIST_OPTS if is_playlist else SINGLE_OPTS
            from yt_dlp import YoutubeDL
            with YoutubeDL(opts) as yt:
                return yt.extract_info(url, download=False)

        try:
            info = await loop.run_in_executor(self.executor, run_fast_or_single)
        except Exception as e:
            self.logger.error(f"Error extracting YouTube info: {e}")
            return None
        if not info:
            return None

        # Playlist: flat entries — super fast; defer stream resolution
        if "entries" in info or info.get("_type") == "playlist":
            items = []
            for e in info.get("entries") or []:
                if not e:
                    continue
                # Flat entries may give id/ie_key; build a stable watch URL
                page_url = e.get("webpage_url") or e.get("url")
                if page_url and page_url.startswith("http"):
                    link = page_url
                else:
                    vid = e.get("id") or page_url
                    link = f"https://www.youtube.com/watch?v={vid}"
                items.append({
                    "link": link,
                    "thumbnail": _pick_thumbnail(e),
                    "original_url": link,
                    "source": None,  # resolve later (right before play)
                    "title": e.get("title"),
                })
            return items or None

        # Single video: resolve a playable URL now
        v = info
        stream = v.get("url") or _pick_best_stream(v)
        if not stream:
            # fallback: try "best"
            def run_best():
                from yt_dlp import YoutubeDL
                with YoutubeDL({**SINGLE_OPTS, "format": "best"}) as yt:
                    return yt.extract_info(v.get("webpage_url") or url, download=False)

            alt = await loop.run_in_executor(self.executor, run_best)
            if alt:
                stream = alt.get("url") or _pick_best_stream(alt)
                if stream:
                    v = alt
        if not stream:
            self.logger.warning("No playable stream found")
            return None

        return [{
            "link": v.get("webpage_url") or url,
            "thumbnail": _pick_thumbnail(v),
            "original_url": v.get("original_url") or v.get("webpage_url") or url,
            "source": stream,
            "title": v.get("title"),
        }]

    @app_commands.command(name='play', description="play a song or playlist")
    async def play(self, itr: discord.Interaction, search: str = None, shuffle_music: bool = False):
        """Plays a requested song or playlist (YouTube/Spotify).
        Progressive mode: starts first track immediately and fetches the rest in background.
        """
        await itr.response.defer()
        channel = itr.channel
        self.logger.info(f'User {itr.user.display_name} called play/{search}')

        # must check BEFORE using itr.user.voice.channel
        if not itr.user.voice:
            await itr.followup.send('⚠️ You need to be connected to a voice channel ⚠️')
            return
        user_channel = itr.user.voice.channel

        # No search: (re)play from queue or resume
        if search is None:
            if self.is_queue_empty():
                await itr.followup.send('❌ There are no songs to be played in the queue ❌')
                return
            if not self.is_playing:
                played = await self.play_music(itr.channel.id, itr.user)
                if not played:
                    await itr.followup.send('❌ There are no songs to be played in the queue ❌')
            else:
                self.is_playing = True
                self.voice_client.resume()
            return

        # We have a search / URL
        song_info: list[dict] = []
        already_enqueued_first = False

        # ---- Spotify (playlist/album progressive)
        if is_spotify_playlist(search) or is_spotify_album(search):
            self.logger.info(f'Spotify URL found: {search}')
            added_now = await self.enqueue_spotify_playlist_progressive(
                search, user_channel, channel, shuffle_music
            )
            if added_now == 0:
                await itr.followup.send('❌ Could not read this Spotify URL ❌')
                return
            # First track was already enqueued by the progressive method
            song_info = [self.queue[-1]['song']]
            already_enqueued_first = True

        # ---- Spotify single track (map to YouTube)
        elif is_spotify_url(search):
            query = get_spotify_track_info(search)  # "Title Artist"
            yt_urls = await self.search_youtube(query)
            if not yt_urls:
                msg = await itr.followup.send('❌ Could not find the song ❌')
                await delete_message(msg)
                return
            url0 = yt_urls[0]
            vid0 = url0.split("v=")[-1].split("&")[0] if "v=" in url0 else url0.rsplit("/", 1)[-1]
            song_info = [{
                "link": url0,
                "thumbnail": _yt_thumb(vid0),
                "original_url": url0,
                "source": None,  # resolve just-in-time at play
                "title": query,
            }]

        else:
            # ---- YouTube: search or URL
            search_results = await self.search_youtube(search)
            self.logger.info(f'Youtube Search results: {search_results}')
            if not search_results:
                msg = await itr.followup.send('❌ Could not find the song ❌')
                await delete_message(msg)
                return

            yt_url = search_results[0]

            # YouTube playlist → progressive
            if _is_playlist_url(yt_url):
                added_now = await self.enqueue_playlist_progressive(
                    yt_url, user_channel, channel, shuffle_music
                )
                if added_now == 0:
                    await itr.followup.send('❌ Could not read this playlist ❌')
                    return
                song_info = [self.queue[-1]['song']]
                already_enqueued_first = True

            # Single YouTube video → extract now
            else:
                song_info = await self.extract_youtube(yt_url)
                if not song_info:
                    await itr.followup.send('❌ Could not play the song ❌')
                    return

        # ---- Add to queue (avoid double-add for progressive branches)
        if shuffle_music:
            from random import shuffle as _shuffle
            _shuffle(song_info)

        if not already_enqueued_first:
            for s in song_info:
                self.queue.append({'song': s, 'channel': user_channel})

        await channel.send(f'📜 Added {len(song_info)} song{"s" if len(song_info) != 1 else ""} to the queue 📜')

        # ---- Start playback if idle
        if not self.is_playing:
            if self.voice_client and self.voice_client.is_paused():
                embed = create_playing_embed("📜 Added to queue 📜", itr.user, song_info)
                msg2 = await itr.followup.send(embed=embed, silent=True)
                await delete_message(msg2)
            else:
                tmp_msg = await itr.followup.send("▶️ Connected and playing...")
                await delete_message(tmp_msg)
                played = await self.play_music(itr.channel.id, itr.user)
                if not played:
                    await itr.followup.send('❌ There are no songs to be played in the queue ❌')
        else:
            embed = create_playing_embed("📜 Added to queue 📜", itr.user, song_info)
            msg2 = await itr.followup.send(embed=embed, silent=True)
            await delete_message(msg2)

    @app_commands.command(name='queue', description="display the current queue")
    async def queue(self, itr: discord.Interaction):
        """Display the current queue

        Args:
            itr (discord.Interaction): Discord interaction
        """
        await itr.response.defer()
        embed = discord.Embed(title="🎚️ Music queue 🎚️")

        previous = self.get_previous_song()
        current = self.get_current_song_from_queue()

        if previous is not None:
            embed.add_field(
                name="PREVIOUS",
                value=f'[{previous["title"]}]({previous["link"]})',
                inline=False)

        embed.add_field(
            name="CURRENT",
            value=f'[{current["title"]}]({current["link"]})',
            inline=False)

        try:
            next_songs = self.queue[self.queue_index + 1:self.queue_index + 10]
            song_list = [
                f'{i + 1}. [{song["song"]["title"]}]({song["song"]["link"]})'
                for i, song in enumerate(next_songs)
            ]
            songs_text = "\n".join(song_list)
            if len(songs_text) > 1024:
                songs_text = songs_text[:1021] + "..."  # Ensure it doesn't exceed 1024

            embed.add_field(name="PLAYING NEXT", value=songs_text, inline=False)
        except Exception as e:
            pass
        await itr.followup.send(embed=embed, silent=True)

    @app_commands.command(name='clear_queue', description="clear the current queue")
    async def clear_queue(self, itr: discord.Interaction):
        """Clear the current queue

        Args:
            itr (discord.Interaction): Discord interaction
        """
        await itr.response.defer()
        self.clear_queue_impl()
        msg = await itr.followup.send('🗑️ Queue cleared! 🗑️', silent=True)
        await delete_message(msg)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Music(client))

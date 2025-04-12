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
    'format': 'bestaudio/best',
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
    'source_address': '0.0.0.0',
    'extract_flat': True
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 256k'
}


def create_playing_embed(title, author: discord.User, song):
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

    def play_audio(self, user, song):
        def play_next_callback(e):
            asyncio.run_coroutine_threadsafe(self.play_next(user), self.client.loop)

        async def play_audio_thread():
            source_url = song['source']
            if source_url is None:
                info = await self.extract_youtube(song['original_url'])
                source_url = info[0]['source']
            self.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(
                source_url, **ffmpeg_options), volume=0.5), after=play_next_callback)

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

    async def search_youtube(self, search: str):
        """Searches YouTube for results based on url or search params

        Args:
            search (str): Url/ Search Params

        Returns:
            _type_: YouTube results
        """
        loop = asyncio.get_event_loop()

        # If it's a valid Youtube URL, return it
        if "youtube.com/watch?v=" in search or "youtu.be/" in search:
            return [search]

        # If it's a playlist, return directly
        if "youtube.com/playlist?list=" in search:
            return [search]

        # Otherwise, search for the song
        query_string = parse.urlencode({'search_query': search})
        content = await loop.run_in_executor(self.executor,
                                             request.urlopen, f'https://www.youtube.com/results?{query_string}')
        content = content.read().decode()

        # Detect video and playlist results
        video_results = re.findall(r'/watch\?v=(.{11})', content)
        playlist_results = re.findall(r'/playlist\?list=([a-zA-Z0-9_-]+)', content)

        results = []
        if video_results:
            results.append(f"https://www.youtube.com/watch?v={video_results[0]}")
        if playlist_results:
            results.append(f"https://www.youtube.com/playlist?list={playlist_results[0]}")

        return results[:1]

    async def extract_youtube(self, url):
        loop = asyncio.get_event_loop()
        with YoutubeDL(ytdl_format_options) as yt:
            try:
                info = await loop.run_in_executor(self.executor, yt.extract_info, url, False)
            except Exception as e:
                return None

            if '_type' not in info or info['_type'] == 'video':
                return [{
                    'link': 'https://www.youtube.com/watch?v=' + url,
                    'thumbnail': info['thumbnails'][0]['url'],
                    'original_url:': info['original_url'],
                    'source': info['url'],
                    'title': info['title']
                }]

                # If it's a playlist, return all entries
            if info['_type'] == 'playlist':
                # If it's a playlist, return all entries
                if info['_type'] == 'playlist':
                    return [
                        {
                            'link': entry['url'],
                            'thumbnail': entry['thumbnails'][0]['url'],
                            'original_url': entry['url'],
                            'source': None,
                            'title': entry['title']
                        }
                        for entry in info['entries'] if entry
                    ]

    @app_commands.command(name='play', description="play a song")
    async def play(self, itr: discord.Interaction, song: str = None, shuffle_music: bool = False):
        """Plays a requested song


        Args:
            :param itr: Discord interaction
            :param song:  The song you want to play
            :param shuffle_music: Shuffle the playlist (if any)
        """
        await itr.response.defer()
        channel = itr.channel
        self.logger.info(f'User {itr.user.display_name} called play/{song}')
        if not itr.user.voice:
            await itr.followup.send('⚠️ You need to be connected to a voice channel ⚠️')

        # Play the musics in the queue
        if song is None:
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

        # Url or search params found
        else:
            song_info = []
            if is_spotify_url(song):
                results = get_spotify_url_data(song)

                async def process_song(query):
                    search_results_local = await self.search_youtube(query)
                    if not search_results_local:
                        return None
                    si = await self.extract_youtube(search_results_local[0])
                    return si[0] if si else None

                tasks = [process_song(query) for query in results]
                song_info_list = await asyncio.gather(*tasks)
                song_info = [s for s in song_info_list if s is not None]
            else:
                # Check if music found
                search_results = await self.search_youtube(song)
                if not search_results:
                    msg = await itr.followup.send('❌ Could not find the song ❌')
                    await delete_message(msg)
                    return

                song_info = await self.extract_youtube(search_results[0])
                if not song_info:
                    await itr.followup.send('❌ Could not play the song ❌')
                    return

            user_channel = itr.user.voice.channel
            # Add music to queue
            if shuffle_music:
                shuffle(song_info)
            for song in song_info:
                self.queue.append({'song': song, 'channel': user_channel})
            await channel.send(f'📜 Added {len(song_info)} songs to the queue 📜')

            # If not active playing, play the music
            if not self.is_playing:
                # If paused, just add to queue
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
            # Otherwise, just add it to the queue
            else:
                embed = create_playing_embed(
                    "📜 Added to queue 📜", itr.user, song_info)
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

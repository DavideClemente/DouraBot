import asyncio
from asyncio import run_coroutine_threadsafe
import discord
import settings
from discord.ext import commands
from discord import app_commands
from yt_dlp import YoutubeDL
from urllib import parse, request
from concurrent.futures import ThreadPoolExecutor
import re
import threading

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    # 'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
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

    async def clear(self):
        self.is_playing = False
        self.queue = []
        self.queue_index = 0

    async def disconnect(self):
        self.is_playing = False
        self.queue = []
        self.queue_index = 0
        await self.voice_client.disconnect()

    def in_voice_channel(self):
        return self.voice_client is not None

    def exists_next_song_in_queue(self):
        return self.queue_index + 1 < len(self.queue)

    def not_me(self, member: discord.Member):
        return member.id != self.client.user.id

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
        msg = ""
        if not self.in_voice_channel():
            msg = await channel.send("You need to be in a voice channel to you this command")
        elif not self.exists_next_song_in_queue():
            msg = await channel.send("There is no next song in the queue. Replaying current song")
            self.voice_client.pause()
            await self.play_music(reaction.message.channel.id, user)
        else:
            self.queue_index += 1
            self.voice_client.pause()
            played = await self.play_music(reaction.message.channel.id, user)
            if not played:
                msg = await channel.send('There are no songs to be played in the queue')
        await delete_message(msg)

    async def reaction_previous(self, channel: discord.TextChannel, reaction: discord.Reaction, user: discord.User):
        if not self.voice_client:
            msg = await channel.send("You need to be in a voice channel to use this command")
        elif self.queue_index <= 0:
            msg = await channel.send("There is no previous song in the queue. Replaying current song")
            self.voice_client.pause()
            await self.play_music(reaction.message.channel.id, user)
        else:
            self.queue_index -= 1
            self.voice_client.pause()
            played = await self.play_music(reaction.message.channel.id, user)
            if not played:
                msg = await channel.send('There are no songs to be played in the queue')
        await delete_message(msg)

    async def reaction_play_pause(self, channel: discord.TextChannel, reaction: discord.Reaction, user: discord.User):
        if not self.voice_client:
            msg = await channel.send("There is no audio to be paused at the moment")
        elif self.is_playing:
            msg = await channel.send(f"Audio Paused by {user.display_name}")
            self.is_playing = False
            self.voice_client.pause()
        else:
            msg = await channel.send(f"Audio Resumed by {user.display_name}")
            self.is_playing = True
            self.voice_client.resume()
        await reaction.message.clear_reactions()
        await add_reactions(reaction.message)
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
                await channel.send('Could not connect to the channel')
        else:
            # Move to channel
            await self.voice_client.move_to(voice_channel)

    async def pause(self, itr: discord.Interaction):
        if not self.voice_client:
            await itr.response.send_message('There is no audio playing at the moment')
        elif self.is_playing:
            self.is_playing = False
            self.voice_client.pause()

    def play_next(self, user: discord.User):
        """Plays the next song

        Args:
            lastMessage (discord.Message): Last 'Playing' message sent
            user (discord.User): User that played the song
        """
        if not self.is_playing:
            return

        if self.exists_next_song_in_queue():
            self.is_playing = True
            self.queue_index += 1

            song = self.get_current_song_from_queue()
            message = create_playing_embed("Now playing", user, song)

            channel = self.client.get_channel(self.last_played_msg.channel.id)
            cor = run_coroutine_threadsafe(
                self.last_played_msg.delete(), self.client.loop)
            res = cor.result()

            coro = channel.send(embed=message)
            future = run_coroutine_threadsafe(coro, self.client.loop)
            try:
                res = future.result()
                self.last_played_msg = res
            except:
                pass
            run_coroutine_threadsafe(add_reactions(res), self.client.loop)
            self.play_audio(user, song)
        else:
            self.queue_index += 1
            self.is_playing = False

    def play_audio(self, user, song):
        def play_next_callback(e):
            self.play_next(user)

        def play_audio_thread():
            self.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(
                song['source'], **ffmpeg_options), volume=0.5), after=play_next_callback)

        thread = threading.Thread(target=play_audio_thread)
        thread.start()

    def get_current_song_from_queue(self):
        return self.queue[self.queue_index]['song']

    def get_previous_song(self):
        return self.queue[
            self.queue_index - 1]['song'] if len(self.queue) > 1 and self.queue_index >= 1 else None

    def is_queue_empty(self):
        return len(self.queue) == 0

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

            embed = create_playing_embed("Now playing", user, song)
            msg = await channel.send(embed=embed)
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
            await itr.response.send_message(f'DouraBot has joined {user_channel}')
        else:
            await itr.response.send_message('You need to be connected to a voice channel')

    @app_commands.command(name='leave', description="leave voice channel")
    async def leave(self, itr: discord.Interaction):
        """Leave your voice channel

        Args:
            itr (discord.Interaction): Discord interaction
        """
        if self.in_voice_channel():
            await self.disconnect()
            self.voice_client = None
            await itr.response.send_message('DouraBot has left the voice channel')
        else:
            await itr.response.send_message('DouraBot is not in a voice channel')

    async def search_youtube(self, search: str):
        """Searches YouTube for results based on url or search params

        Args:
            search (str): Url/ Search Params

        Returns:
            _type_: YouTube results
        """
        loop = asyncio.get_event_loop()
        query_string = parse.urlencode({'search_query': search})
        content = await loop.run_in_executor(self.executor,
                                             request.urlopen, f'https://www.youtube.com/results?{query_string}')
        content = content.read().decode()
        results = re.findall('/watch\?v=(.{11})', content)
        return results[0:10]

    async def extract_youtube(self, url):
        loop = asyncio.get_event_loop()
        with YoutubeDL(ytdl_format_options) as yt:
            try:
                info = await loop.run_in_executor(self.executor, yt.extract_info, url, False)
            except Exception:
                return None
            return {
                'link': 'https://www.youtube.com/watch?v=' + url,
                'thumbnail': 'https://i.ytimg.com/vi/' + url + '/hqdefault.jpg?sqp=-oaymwEcCOADEI4CSFXyq4qpAw4IARUAAIhCGAFwAcABBg==&rs=AOn4CLD5uL4xKN-IUfez6KIW_j5y70mlig',
                'source': info['url'],
                'title': info['title']
            }

    @app_commands.command(name='play', description="play a song")
    async def play(self, itr: discord.Interaction, song: str = None):
        """Plays a requested song


        Args:
            :param itr: Discord interaction
            :param song:  The song you want to play
        """
        await itr.response.defer()
        self.logger.info(f'User {itr.user.display_name} called play/{song}')
        if not itr.user.voice:
            await itr.followup.send('You need to be connected to a voice channel')

        # Play the musics in the queue
        if song is None:
            if self.is_queue_empty():
                await itr.followup.send('There are no songs to be played in the queue')
                return
            if not self.is_playing:
                played = await self.play_music(itr.channel.id, itr.user)
                if not played:
                    await itr.followup.send('There are no songs to be played in the queue')
            else:
                self.is_playing = True
                self.voice_client.resume()

        # Url or search params found
        else:
            # Check if music found
            search_results = await self.search_youtube(song)
            if not search_results:
                await itr.followup.send('Could not find the song')
                return

            song_info = await self.extract_youtube(search_results[0])
            if not song_info:
                await itr.followup.send('Could not play the song.')
                return

            user_channel = itr.user.voice.channel
            # Add music to queue
            self.queue.append({'song': song_info, 'channel': user_channel})

            # If not active playing, play the music
            if not self.is_playing:
                # If paused, just add to queue
                if self.voice_client and self.voice_client.is_paused():
                    embed = create_playing_embed("Added to queue", itr.user, song)
                    msg2 = await itr.followup.send(embed=embed)
                    await delete_message(msg2)
                else:
                    played = await self.play_music(itr.channel.id, itr.user)
                    if not played:
                        await itr.followup.send('There are no songs to be played in the queue')
            # Otherwise, just add it to the queue
            else:
                embed = create_playing_embed(
                    "Added to queue", itr.user, song)
                msg2 = await itr.followup.send(embed=embed)
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
                name="PREVIOUS", value=f'[{previous["title"]}]({previous["link"]})', inline=False)
        embed.add_field(
            name="CURRENT", value=f'[{current["title"]}]({current["link"]})', inline=False)
        try:
            if self.queue[self.queue_index + 1]:
                songs = "\n".join(
                    f'[{song["song"]["title"]}]({song["song"]["link"]})' for song in self.queue[self.queue_index + 1:])
                embed.add_field(name="PLAYING NEXT", value=songs, inline=False)
        except Exception:
            pass
        await itr.followup.send(embed=embed)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Music(client))

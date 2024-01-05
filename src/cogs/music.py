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

    async def clear(self):
        self.is_playing = False
        self.queue = []
        self.queue_index = 0

    async def disconnect(self):
        self.is_playing = False
        self.queue = []
        self.queue_index = 0
        await self.voice_client.disconnect()

    def create_playing_embed(self, title, author: discord.User, song):
        embed = discord.Embed(title=title,
                              description=f'[{song["title"]}]({song["link"]})',
                              color=discord.Color.from_str(
                                  settings.DOURADINHOS_COLOR)
                              )
        embed.set_thumbnail(url=song["thumbnail"])
        embed.set_footer(
            text=f'Song added by: {str(author)}', icon_url=author.avatar.url)
        return embed

    # @commands.Cog.listener()
    # async def on_message(self, message: discord.Message):
    #     print('Trigger')
    #     if message.author.id == self.client.user.id and message.content.endswith('to queue'):
    #         await asyncio.sleep(2)
    #         await message.delete()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Check if disconnected from discord
        if member == self.client.user and before.channel and not after.channel:
            await self.clear()
        if member.id != self.client.user.id and before.channel != None and after.channel != before.channel:
            remaining_member = before.channel.members
            if len(remaining_member) == 1 and remaining_member[0].id == self.client.user.id and self.voice_client.is_connected():
                await self.disconnect()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        # Next
        channel = self.client.get_channel(reaction.message.channel.id)
        if reaction.emoji == '⏭️' and user != self.client.user:
            if self.voice_client == None:
                msg = await channel.send("You need to be in a voice channel to you this command")
            elif self.queue_index >= len(self.queue) - 1:
                msg = await channel.send("There is no next song in the queue. Replaying current song")
                self.voice_client.pause()
                await self.play_music(reaction.message.channel.id, user)
            elif self.voice_client != None and self.voice_client:
                self.queue_index += 1
                self.voice_client.pause()
                played = await self.play_music(reaction.message.channel.id, user)
                if not played:
                    msg = await channel.send('There are no songs to be played in the queue')
            await self.delete_message(msg)
        # Previous
        elif reaction.emoji == '⏮️' and user != self.client.user:
            if self.voice_client == None:
                msg = await channel.send("You need to be in a voice channel to you this command")
            elif self.queue_index <= 0:
                msg = await channel.send("There is no previous song in the queue. Replaying current song")
                self.voice_client.pause()
                await self.play_music(reaction.message.channel.id, user)
            elif self.voice_client != None and self.voice_client:
                self.queue_index -= 1
                self.voice_client.pause()
                played = await self.play_music(reaction.message.channel.id, user)
                if not played:
                    msg = await channel.send('There are no songs to be played in the queue')
            await self.delete_message(msg)

        elif reaction.emoji == '⏯️' and user != self.client.user:
            if not self.voice_client:
                msg = await channel.send("There is no audio to be paused at the moment")
            elif self.is_playing:
                msg = await channel.send("Audio Paused")
                self.is_playing = False
                self.voice_client.pause()
            elif not self.is_playing:
                msg = await channel.send("Audio Resumed")
                self.is_playing = True
                self.voice_client.resume()
            await reaction.message.clear_reactions()
            await self.add_reactions(reaction.message)
            await self.delete_message(msg)

    async def add_reactions(self, msg: discord.Message):
        await msg.add_reaction('⏮️')
        await msg.add_reaction('⏯️')
        await msg.add_reaction('⏭️')

    def search_youtube(self, search:  str):
        """Searches youtube for results based on url or search params

        Args:
            search (str): Url/ Search Params

        Returns:
            _type_: Youtube results
        """
        query_string = parse.urlencode({'search_query': search})
        content = request.urlopen(
            'https://www.youtube.com/results?' + query_string)
        results = re.findall('/watch\?v=(.{11})', content.read().decode())
        return results[0:10]

    def extract_youtube(self, url):
        with YoutubeDL(ytdl_format_options) as yt:
            try:
                info = yt.extract_info(url, download=False)
            except:
                return {}
            return {
                'link': 'https://www.youtube.com/watch?v=' + url,
                'thumbnail': 'https://i.ytimg.com/vi/' + url + '/hqdefault.jpg?sqp=-oaymwEcCOADEI4CSFXyq4qpAw4IARUAAIhCGAFwAcABBg==&rs=AOn4CLD5uL4xKN-IUfez6KIW_j5y70mlig',
                'source': info['url'],
                'title': info['title']
            }

    async def delete_message(self, msg: discord.Message):
        await asyncio.sleep(5)
        await msg.delete()

    async def join_voice_channel(self, textChannel, channel):
        """Join a voice channel

        Args:
            textChannel (_type_): Channel to send messages to
            channel (_type_): Channel to join
        """
        # Check if already connected to a channel
        if self.voice_client == None or not self.voice_client.is_connected():
            # Try to connect to the channel
            self.voice_client = await channel.connect()
            if self.voice_client == None:
                c = self.client.get_channel(textChannel)
                await c.send('Could not connect to the channel')
        else:
            # Move to channel
            await self.voice_client.move_to(channel)

    async def pause(self, itr: discord.Interaction):
        if not self.voice_client:
            await itr.response.send_message('There is no audio to be pause at the moment')
        elif self.is_playing:
            self.is_playing = False
            self.voice_client.pause()

    def play_next(self, lastMessage: discord.Message, user: discord.User):
        """Play the next song

        Args:
            lastMessage (discord.Message): Last 'Playing' message sent
            user (discord.User): User how played the song
        """
        print('Play next')
        if not self.is_playing:
            return

        if self.queue_index + 1 < len(self.queue):
            self.is_playing = True
            self.queue_index += 1

            song = self.queue[self.queue_index]['song']
            message = self.create_playing_embed("Now playing", user, song)

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
            run_coroutine_threadsafe(self.add_reactions(res), self.client.loop)
            self.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(
                song['source'], **ffmpeg_options), volume=0.5), after=lambda e: self.play_next(user))
        else:
            self.queue_index += 1
            self.is_playing = False

    async def play_music(self, channel_id, user):
        """Play a song

        Args:
            channel_id (_type_): Channel where to send messages to
            user (_type_): User who played the song

        Returns:
            _type_: _description_
        """
        if self.queue_index < len(self.queue):
            # await itr.response.send_message("Playing...")
            self.is_playing = True
            channel = self.client.get_channel(channel_id)
            await self.join_voice_channel(channel, self.queue[self.queue_index]['channel'])
            song = self.queue[self.queue_index]['song']

            if self.last_played_msg != None:
                await self.last_played_msg.delete()

            embed = self.create_playing_embed("Now playing", user, song)
            msg = await channel.send(embed=embed)
            self.last_played_msg = msg
            await self.add_reactions(msg)

            self.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(
                song['source'], **ffmpeg_options), volume=0.5), after=lambda e: self.play_next(user))
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
        if self.voice_client != None:
            await self.disconnect()
            self.voice_client = None
            await itr.response.send_message('DouraBot has left the voice channel')
        else:
            await itr.response.send_message('DouraBot is not in a voice channel')

    @app_commands.command(name='play', description="play a song")
    async def play(self, itr: discord.Interaction, search: str = None):
        """Play a song

        Args:
            itr (discord.Interaction): Discord interaction
            search (str, optional): The song you want to play
        """
        await itr.response.defer()
        if not itr.user.voice:
            await itr.followup.send('You need to be connected to a voice channel')
        # Play the musics in the queue
        if search == None:
            # Check if queue is empty
            if len(self.queue) == 0:
                await itr.followup.send('There are no songs to be played in the queue')
                return
            # If bot is not playing
            elif not self.is_playing:
                # Play next music in queue
                if self.queue == None or self.voice_client == None:
                    # Play music
                    msg = await itr.followup.send("Playing...")

                    played = await self.play_music(itr.channel.id, itr.user)
                    if not played:
                        await itr.followup.send('There are no songs to be played in the queue')
                    await self.delete_message(msg)
                # There are musics in the queue and bot is connected, just resume
                else:
                    self.is_playing = True
                    self.voice_client.resume()
            else:
                return

        # Url or search params found
        else:
            # Get song from youtube (For now just the first one)
            # TODO: Choose which music to play in a dropdown
            song = self.extract_youtube(self.search_youtube(search)[0])
            # Check if music found
            if song == {}:
                await itr.followup.send('Could not play the song.')
            else:
                user_channel = itr.user.voice.channel
                # Add music to queue
                self.queue.append({'song': song, 'channel': user_channel})
                # If not playing, play the music
                if not self.is_playing:
                    if self.voice_client.is_paused():
                        embed = self.create_playing_embed(
                            "Added to queue", itr.user, song)
                        msg2 = await itr.followup.send(embed=embed)
                        await self.delete_message(msg2)
                    else:
                        msg = await itr.followup.send("Playing...")
                        played = await self.play_music(itr.channel.id, itr.user)
                        if not played:
                            await itr.followup.send('There are no songs to be played in the queue')
                        await self.delete_message(msg)
                # Otherwise, just add it to the queue
                else:
                    embed = self.create_playing_embed(
                        "Added to queue", itr.user, song)
                    msg2 = await itr.followup.send(embed=embed)
                    await self.delete_message(msg2)

    # @app_commands.command(name='previous', description="join vc")
    # async def previous(self, itr: discord.Interaction):
    #     await itr.response.defer()
    #     msg = await itr.followup.send("Playing previous...")
    #     if self.voice_client == None:
    #         await itr.followup.send("You need to be in a voice channel to you this command")
    #     elif self.queue_index <= 0:
    #         await itr.followup.send("There is no previous song in the queue. Replaying current song")
    #         self.voice_client.pause()
    #         await self.play_music(itr.channel.id, itr.user)
    #     elif self.voice_client != None and self.voice_client:
    #         self.queue_index -= 1
    #         self.voice_client.pause()
    #         await self.play_music(itr.channel.id, itr.user)
    #     await self.delete_message(msg)

    # @app_commands.command(name='skip', description="join vc")
    # async def skip(self, itr: discord.Interaction):
    #     await itr.response.defer()
    #     msg = await itr.followup.send("Skipping...")

    #     if self.voice_client == None:
    #         await itr.response.send_message("You need to be in a voice channel to you this command")
    #     elif self.queue_index >= len(self.queue) - 1:
    #         await itr.response.send_message("There is no next song in the queue. Replaying current song")
    #         self.voice_client.pause()
    #         await self.play_music(itr.channel.id, itr.user)
    #     elif self.voice_client != None and self.voice_client:
    #         self.queue_index += 1
    #         self.voice_client.pause()
    #         played = await self.play_music(itr.channel.id, itr.user)
    #         await self.delete_message(msg)
    #         if not played:
    #             await itr.response.send_message('There are no songs to be played in the queue')


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Music(client))

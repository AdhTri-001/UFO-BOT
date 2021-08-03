from datetime import datetime
import discord, async_timeout, re
from discord.ext import commands
import wavelink, asyncio
from random import shuffle

IS_URL= re.compile(r'^(?:https?:)?(?:\/\/)?(?:youtu\.be\/|(?:www\.|m\.)?youtube\.com\/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|\/))([a-zA-Z0-9\_-]{7,15})(?:[\?&][a-zA-Z0-9\_-]+=[a-zA-Z0-9\_-]+)*$')
PLAYTIME= re.compile(r'(^(\d{1,}:)?(([0-5]?[0-9]|60):)?([0-5]?[0-9]|60)$)|^\d{1,}$')

class Queue(asyncio.Queue):
    def shuffle(self):
        shuffle(self._queue)

class Track(wavelink.Track):
    __slots__ = ('requester', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.requester = kwargs.get('requester')

class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skip_votes= []
        self.pause_votes= []
        self.shuffle_votes= []
        self.listners= []
        self.now_playing= None
        self.queue= Queue(maxsize= 10)
        self.bound_ch_id= None
        self.waiting= False

    def reset_votes(self):
        self.skip_votes= []
        self.pause_votes= []
        self.shuffle_votes= []

    async def play_next(self):
        if self.waiting:
            return
        await self.set_volume(100)
        if self.is_playing:
            await self.stop()
        try:
            self.waiting= True
            with async_timeout.timeout(300):
                track= await self.queue.get()
        except:
            self.waiting= False
            await self.teardown()
            await self.set_eq(wavelink.Equalizer.flat())
            return
        self.reset_votes()
        await self.play(track=track, replace= True)
        await self.set_eq(wavelink.Equalizer.flat())
        self.now_playing: Track= track
        await self.send_embed()
        self.waiting= False

    async def send_embed(self):
        channel= self.bot.get_channel(self.bound_ch_id)
        embed= discord.Embed(
            description= self.now_playing.title,
            timestamp= datetime.utcnow(),
            color= channel.guild.me.color
        )
        embed.set_author(name= str(self.now_playing.requester), url= self.now_playing.uri, icon_url= self.now_playing.requester.avatar_url)
        embed.add_field(name= 'Duration', value= f'{self.bot.timeconv(self.now_playing.length//1000)}')
        embed.set_thumbnail(url= self.now_playing.thumb) if self.now_playing.thumb else None
        embed.add_field(name= 'Requested by', value= f'{self.now_playing.requester}')
        await channel.send(embed= embed)

    def add_track(self, track):
        self.queue.put_nowait(track)

    async def pause(self):
        self.pause_votes= []
        await self.set_pause(pause= True)

    async def unpause(self):
        self.pause_votes= []
        await self.set_pause(pause= False)

    async def vote_pause(self, userid):
        if self.is_paused:
            return 'There is no song playing right now. What you doing?'
        if not userid in self.pause_votes:
            self.pause_votes.append(userid)
            if len(self.pause_votes) >= (len(self.listners) / 2):
                await self.pause(self)
                return f'Pused the current song 👌. Use `vote resume` or `force resume` to resume the song.'
            require= round((len(self.listners) / 2) - len(self.pause_votes))
            return f'<@{userid}> Voted to pause the current song. Total votes right now are **{len(self.pause_votes)}** (require **{require}** more)'
        else:
            return 'You already voted to pause the current playing song..'

    async def vote_resume(self, userid):
        if not self.is_paused:
            return 'The song isn\'t paused, what you doing?'
        if not userid in self.pause_votes:
            self.pause_votes.append(userid)
            if len(self.pause_votes) >= (len(self.listners) / 2):
                await self.pause(self)
                return f'Resumed the current song 👌.'
            require= round((len(self.listners) / 2) - len(self.pause_votes))
            return f'<@{userid}> Voted to resume the current song. Total votes now are **{len(self.pause_votes)}** (require **{require}** more)'
        else:
            return 'You already voted to resume the song..'

    async def vote_shuffle(self, userid):
        if not len(self.queue._queue) >= 2:
            return 'There is "Nothing" in the queue to shuffle..'
        if not userid in self.shuffle_votes:
            self.shuffle_votes.append(userid)
            if len(self.shuffle_votes) >= (len(self.listners) / 2):
                self.queue.shuffle()
                self.shuffle_votes= []
                return f'Shuffled the queue. To see the new queue use `queue` command'
            require= round((len(self.listners) / 2) - len(self.shuffle_votes))
            return f'<@{userid}> voted to shuffle the queue. Total votes now are **{len(self.shuffle_votes)}** (require **{require}** more)'
        else:
            return 'You already voted to shuffle the queue..'

    async def vote_skip(self, userid):
        if not userid in self.skip_votes:
            self.skip_votes.append(userid)
            if len(self.skip_votes) >= (len(self.listners) / 2):
                await self.play_next()
                return None
            require= round((len(self.listners) / 2) - len(self.skip_votes))
            return f'<@{userid}> voted to skip the current song. Total votes now are **{len(self.skip_votes)}** (require **{require}** more)'
        else:
            return 'You already voted to skip the current song..'

    async def teardown(self):
        await self.disconnect()
        self.reset_votes()
        self.bound_ch_id= None


# THE MAIN MUSIC COG /////////////////////////////
#cd "C:\Program Files\Java\jdk-16.0.1\bin"
#java -jar lavalink.jar
class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, client) -> None:
        self.client= client
        self.wavelinkClient= wavelink.Client(bot= self.client)
        self.client.loop.create_task(self.start_nodes())

    print('Music.py has been loaded\n-----------------------------------')

    # Checking for disabled commands and Blacklisted channels
    async def cog_check(self, ctx):
        if not ctx.guild:
            return False
        discmds= await self.client.db.fetchrow(f'SELECT discmds, blackch FROM guildsettings WHERE guild_id= {ctx.guild.id}')
        if not discmds: return True
        blackch, discmds= discmds['blackch'], discmds['discmds']
        if not discmds and not blackch:
            return True
        else:
            return not ctx.command.name in discmds and not ctx.channel.id in blackch

    def skip_to(self, time:str):
        timelist= time.split(':')
        if len(timelist) == 1:
            return int(timelist[0])
        if len(timelist) == 2:
            timetoreturn= int(timelist[0]) * 60 + int(timelist[1])
            return timetoreturn
        if len(timelist) == 3:
            timetoreturn= int(timelist[0]) * 3600 + int(timelist[1]) * 60 + int(timelist[2])
            return timetoreturn

    async def start_nodes(self):
        await self.client.wait_until_ready()
        nodes= [{
                'host': '127.0.0.1',
                'port': 2333,
                'password': 'yoyome9104',
                'identifier': 'Main',
                'region': 'us_central',
                'rest_uri': 'http://127.0.0.1:2333'
            }]
        for node in nodes:
            try:
                await self.wavelinkClient.initiate_node(**node)
            except:
                print('Failed to connect to the node: ', node['identifier'])

    async def has_requested(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id)
        if ctx.author.id== player.now_playing.requester.id:
            return True
        else:
            return False
    async def has_modrole(self, ctx):
        modrole= await ctx.bot.db.fetchval('SELECT modrole_id FROM guildsettings WHERE guild_id = $1::numeric', ctx.guild.id)
        if modrole== None:
            return False
        try:
            return await commands.has_role(int(modrole)).predicate(ctx)
        except:
            return False
    async def can_mod_channel(self, channel: discord.VoiceChannel, author):
        permissions= channel.permissions_for(author)
        if permissions.move_members or permissions.deafen_members or permissions.manage_channels:
            return True
        else:
            return False

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node):
        print(f'Lavalink node \'{node.identifier}\' is now available. Noice!')

    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.play_next()

    # Checking for disabled commands and Blacklisted channels
    async def check_command_enable(self, ctx):
        if not ctx.guild:
            return False
        discmds= self.client.cache.get(ctx.guild.id, {"discmds":[], "blackch":[]})
        blackch, discmds= discmds['blackch'],discmds['discmds']
        if not discmds and not blackch:
            return True
        else:
            return not ctx.command.name in discmds and not ctx.channel.id in blackch

    async def cog_check(self, ctx):
        if await self.check_command_enable(ctx):
            player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
            if ctx.guild:
                if player.is_connected and ctx.channel.id == player.bound_ch_id and ctx.command.name != 'summon':
                    return True
                elif not player.is_connected and ctx.command.name in ['summon', 'play']:
                    return True
                else:
                    return False
            else:
                return False
        else: return False

    async def cog_before_invoke(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        vc= player.channel_id
        if not vc:
            return
        elif player.is_connected:
            vc= ctx.guild.get_channel(vc)
            player.listners= list(vc.voice_states.keys())
            player.listners.remove(822448143508963338)

    # Connect aka Join command.
    @commands.command(aliases= ['join', 'j'],
        help= 'Connect to a vc and the bot will join your current vc when the command invoked.')
    async def summon(self, ctx):
        try:
            vc= ctx.author.voice.channel
            if not isinstance(vc, discord.VoiceChannel):
                raise Exception
        except:
            await ctx.send('Connect to a vc and then try use the command.')
            raise commands.MissingPermissions('manage_channel')
        embed= discord.Embed(
            description= f'Connected to {vc.mention} and bound to {ctx.channel.mention}',
            color= ctx.me.color
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        if not player.is_connected:
            player.bound_ch_id= ctx.channel.id
            await player.connect(vc.id)
            await ctx.send(embed= embed)
        else:
            await ctx.send(f'I m already connected to: {ctx.me.voice.channel.mention}')

    # Play aka Get the song.
    @commands.command(aliases= ['p', 'sing'],
        help= 'Play a song or add to the queue if already playing.')
    async def play(self, ctx, *, query):
        if IS_URL.match(query):
            tracks= await self.wavelinkClient.get_tracks(query= query, retry_on_failure= False)
        else:
            tracks= await self.wavelinkClient.get_tracks(query= f'ytsearch:{query}', retry_on_failure= False)
        tracks= tracks[0:7]
        if not tracks or isinstance(tracks, wavelink.TrackPlaylist):
            await ctx.send('No song was found with that query. Pls try using YT url instead.')
            return
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        if not player.is_connected:
            await ctx.invoke(self.summon)
        async def add(track):
            track= Track(track.id, track.info, requester=ctx.author)
            try:
                player.add_track(track)
            except:
                await ctx.send('The queue has reached the limit of 10 tracks..')
            if len(player.queue._queue) != 0 or player.is_playing:
                embed= discord.Embed(
                    title= track.title,
                    color= ctx.me.color,
                    description= f'Added the track to the queue at position {len(player.queue._queue)}'
                )
                embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
                embed.set_thumbnail(url= track.thumb) if track.thumb else None
                if player.is_playing:
                    await ctx.send(embed= embed)
            else:
                return
        if len(tracks) == 1:
            return await add(tracks[0])
        desc= ''
        i= 1
        for track in tracks:
            desc+= f'**{i}.**  `{track.title}`\n'
            i+= 1
        embed= discord.Embed(
            title= 'Choose the song to add!',
            description= desc
        )
        embed.set_footer(text= 'Type which number in front of song u want me to add.\nType ``c`` to cancel.')
        query= await ctx.reply(embed= embed)
        def check(m):
            if not ctx.author== m.author and ctx.channel== m.channel:
                return False
            return m.content in list(map(str, range(1, i))) or m.content.lower() == 'c'
        try:
            choice= await self.client.wait_for('message', timeout= 30, check= check)
        except:
            await query.delete()
            return
        await query.delete()
        if choice.content.lower() == 'c':
            return
        choice= int(choice.content)
        await add(tracks[choice-1])
        if not player.is_playing:
            await player.play_next()

    # Queue command.
    @commands.command(aliases= ['que', 'q'],
        help= 'UWU\'UEUE')
    async def queue(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        queue= player.queue._queue
        desc= ''
        i= 1
        for track in queue:
            track: wavelink.Track= track
            desc+= f'```asciidoc\n= {track.title}\n\tDuration :: {self.client.timeconv(track.length//1000)}```'
        embed= discord.Embed(
            title= 'Queue',
            description= desc,
            timestamp= datetime.utcnow(),
            color= ctx.me.color
        )
        await ctx.reply(embed= embed)

    # For socialists
    @commands.group(aliases= ['v'], usage= '<SubCommand>',
        help= 'Vote to apply actions in the current song.')
    async def vote(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        if not ctx.author.id in player.listners:
            await ctx.send('You are not joined to the voice channel I m connected to.')
            raise commands.MissingRole('Musician')
        else:
            pass
    @vote.command(aliases= ['ski'],
        help= 'Current song was not an imposter')
    async def skip(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        desc= await player.vote_skip(ctx.author.id)
        if not desc:
            return
        embed= discord.Embed(
            title= 'Skipper!',
            color= ctx.me.color,
            description= desc
        )
        await ctx.reply(mention_author= False, embed= embed)
    @vote.command(aliases= ['shuf'],
        help= 'Shuffle the queue.')
    async def shuffle(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        embed= discord.Embed(
            title= 'Shuffler!',
            color= ctx.me.color,
            description= await player.vote_shuffle(ctx.author.id)
        )
        await ctx.reply(mention_author= False, embed= embed)
    @vote.command(aliases= ['pau'],
        help= 'Pause the song |>')
    async def pause(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        embed= discord.Embed(
            title= 'Pauser!',
            color= ctx.me.color,
            description= await player.vote_pause(ctx.author.id)
        )
        await ctx.reply(mention_author= False, embed= embed)
    @vote.command(aliases= ['res'],
        help= 'Resume the song ||')
    async def resume(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        embed= discord.Embed(
            title= 'Resumer!',
            color= ctx.me.color,
            description= await player.vote_resume(ctx.author.id)
        )
        await ctx.reply(mention_author= False, embed= embed)

    # For communists
    @commands.group(aliases= ['f'],
        help= 'Force the current music. You require some special powers to use this command',
        description= 'to be a forcer one must have modrole, or had requested the song, or has permission to manage the voice channel.')
    async def force(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        if not ctx.author.id in player.listners:
            raise commands.MissingAnyRol('Your are not Listner')
        if await self.has_requested(ctx) or await self.has_modrole(ctx) or await self.can_mod_channel(ctx.guild.get_channel(player.channel_id), ctx.author):
            pass
        else:
            await ctx.send('You are not forcer, to be a forcer one must have modrole, or had requested the song, or has permission to manage the voice channel.')
            raise commands.MissingAnyRole('You are not allowed to force the party.')
    @force.command(name= 'skip', aliases= ['ski'],
        help= 'Skip the current song without any votes, if you got some force.')
    async def _skip(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        await player.play_next()
    @force.command(name= 'resume', aliases= ['res'],
        help= 'Resumes the pause song.')
    async def _resume(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        if not player.is_paused:
            await ctx.send('The song is\'t paused..')
        else:
            player.set_pause(pause= False)
            embed= discord.Embed(
                title= 'Resumed!',
                description= 'Resumed the song.',
                color= ctx.me.color
            )
            embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
            await ctx.send(embed= embed)
    @force.command(name= 'pause',aliases= ['pau'],
        help= 'pause the current playing song.')
    async def _pause(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        await player.set_pause(pause= True)
        embed= discord.Embed(
            title= 'Paused!',
            color= ctx.me.color,
            description= 'Paused the song. Use `force/vote resume` command to resume.'
        )
        await ctx.reply(mention_author= False, embed= embed)
    @force.command(name= 'bassboost',aliases= ['bboost'],
        help= 'This equalizer emphasizes Punchy Bass and Crisp Mid-High tones. Not suitable for tracks with Deep/Low Bass.')
    async def _bassboost(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        await player.set_equalizer(wavelink.Equalizer.boost())
        embed= discord.Embed(
            title= 'Bass boosted!',
            color= ctx.me.color,
            description= 'Enjoy the "evilness" of the bass, hold your heart.'
        )
        embed.set_footer(text= 'The effects will go away on the start of next song.')
        await ctx.reply(mention_author= False, embed= embed)
    @force.command(name= 'noeq',aliases= ['flat'],
        help= 'Removes all equalized effects.')
    async def _noeq(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        await player.set_equalizer(wavelink.Equalizer.flat())
        embed= discord.Embed(
            title= 'Flatten!',
            color= ctx.me.color,
            description= 'You will hear without any effects applied now.'
        )
        await ctx.reply(mention_author= False, embed= embed)
    @force.command(name= 'cleaned',aliases= ['pitchy'],
        help= 'Suitable for Piano tracks, or tacks with an emphasis on Female Vocals. Could also be used as a Bass Cutoff.')
    async def _cleaned(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        await player.set_equalizer(wavelink.Equalizer.piano())
        embed= discord.Embed(
            title= 'Flatten!',
            color= ctx.me.color,
            description= 'Feel the pitch of the songs, hold your ears tight.'
        )
        embed.set_footer(text= 'The effects will go away on the start of next song.')
        await ctx.reply(mention_author= False, embed= embed)
    @force.command(aliases= ['goto'],
        help= 'Seek the current playing song.')
    async def seek(self, ctx, timeToSeek):
        if not PLAYTIME.match(timeToSeek):
            await ctx.send('Type the time to seek to like- `1:30` `70` `1:5:15` `3:2`')
            return
        pos= self.skip_to(timeToSeek)
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        if pos> player.now_playing.length//1000:
            pos= player.now_playing.length//1000
        await player.seek(position= pos*1000)
        embed= discord.Embed(
            title= "Seek!",
            description= f'Seeked {pos} seconds ahead.',
            color= ctx.me.color
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)
    @force.command(aliases= ['vol'],
        help= 'Set the volume of the current playing song. Recommanded 5-10 - if greater be ready for earape')
    async def voume(self, ctx, volume: int):
        if not volume in range(0,101):
            await ctx.send('Tell me a number between 0 and 101')
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        await player.set_volume(volume*10)
        await ctx.send(f'Set the volume to {player.volume}')

    @commands.command(aliases= ['np'],  
        help= 'This command is obvious, tell u the current song.')
    async def nowplaying(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        if not player.now_playing:
            await ctx.send('I m playing nothing right now.')
            return
        track: Track= player.now_playing
        embed= discord.Embed(
            title= track.title,
            color= ctx.me.color,
            description= f'Requested by **{track.requester}**'
        )
        embed.set_thumbnail(url= track.thumb) if track.thumb else None
        embed.add_field(name= 'Duration', value= self.client.timeconv(track.length//1000))
        embed.set_author(name= str(track.requester), icon_url= track.requester.avatar_url)
        await ctx.reply(embed= embed, mention_author= False)

    @commands.command(aliases= ['clqueue', 'clearqueue'],
        help= 'Clear all the song in the queue, you need power to use this one.')
    async def cleanqueue(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        if await self.has_modrole(ctx) or await self.can_mod_channel(ctx.guild.get_channel(player.channel_id), ctx.author):
            player.queue._queue= []
            await ctx.send('Cleared the queue. It wasn\'t fun doing it.')

    @commands.command(aliases= ['shh', 'shhh'], help= 'Disconnects from the voice channel.')
    async def leave(self, ctx):
        player: Player= self.wavelinkClient.get_player(ctx.guild.id, cls= Player)
        if not player.is_connected:
            return
        if not player.is_playing and player.queue.empty():
            return await player.disconnect()
        if await self.has_modrole(ctx) or await self.can_mod_channel(ctx.guild.get_channel(player.channel_id), ctx.author):
            return await player.disconnect()
        if len(player.listners) <= 3:
            return await player.disconnect()

def setup(client):
    client.add_cog(Music(client))
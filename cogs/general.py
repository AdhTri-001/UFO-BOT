from datetime import datetime
from numpy.random import choice, randint
import discord, sys, tracemalloc
from discord.ext import commands, tasks
from time import time
from typing import Union
import json, os, re
from cleantext import clean
from fancy_text import fancy
from UFO_Bot import Ufo_bot
import asyncio

owo_vowels = ['a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U']
owo_emotes = ['^w^', '>w< ', 'UwU ', '(・`ω\\´・)', 
    '(´・ω・\\`)', 'OwO', '◔w◔ ', '( ͡o ω ͡o )', '(O꒳O)', 
    '( °ω° )', '( ͡o ꒳ ͡o )', 'ღ(O꒳Oღ)', 
    '*𝓷𝓾𝔃𝔃𝓵𝓮𝓼 𝔂𝓸𝓾𝓻 𝓬𝓱𝓮𝓼𝓽*', '‿︵*𝓇𝒶𝓌𝓇*‿︵ ʘwʘ', 
    '✼ ҉♡ (。O⁄ ⁄ω⁄ ⁄ O。) ҉♡ ✼', '✧･ﾟ: *✧･ﾟ:*(OwO)*:･ﾟ✧*:･ﾟ✧', 
    'ᎧᏇᎧ', '♡w♡', 'ÒwÓ', '≧◡≦', '✧(˘•ω•˘)ง', '~(˶‾᷄ꈊ‾᷅˵)~', 
    'ᕙ(⇀w↼‶)ᕗ', '༼ ༎ຶ w ༎ຶ༽', '( ͡° w ͡°)', '(•w•)', '♤w♤', '♧w♧', 
    '(๑و•̀ω•́)و', '(˶‾᷄ ⁻̫ ‾᷅˵)', '꒰๑´•.̫ • `๑꒱', '・ω・', '>ω^', 
    '{・ω-*}', 'ˁ(⦿@ᴥ⦿*)ˀ', 'ʕ✿๑•́ ᴥ •̀๑✿ʔ', '(•̯͡.•̯͡)', '꒰◍ᐡᐤᐡ◍꒱', 
    '༼ (´・ω・`) ༽', '♥(⇀ᆽ↼ﾐ)∫', '✿(≗ﻌ≗^)', '( ͒ ඉ .̫ ඉ ͒)', 
    '( ^◡^)', '^•ﻌ•^', '{ @❛ꈊ❛@ }', '^•ﻌ•^ฅ', '(✿^U^)/', 
    '(≗ﻌ≗^)']

class General(commands.Cog):
    def __init__(self, client):
        self.client: Ufo_bot= client
    
    async def loopstarter(self):
        while True:
            if self.client.inited:
                self.remind_checker.start()
                break
        print(f'Starting Loops in {self.__class__.__name__}...')

    print("General.py has been loaded\n-----------------------------------")

    # Checking for disabled commands and Blacklisted channels
    async def cog_check(self, ctx):
        if not ctx.guild:
            return False
        discmds= self.client.cache.get(ctx.guild.id, {"discmds":[], "blackch":[]})
        blackch, discmds= discmds['blackch'],discmds['discmds']
        if not discmds and not blackch:
            return True
        else:
            return not ctx.command.name in discmds and not ctx.channel.id in blackch
    
    def convert(self, time):
        time_regex = re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
        time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}
        time = time.lower()
        matches = re.findall(time_regex, time)
        time = 0
        for key, value in matches:
            try:
                time += time_dict[value] * float(key)
            except KeyError:
                raise commands.BadArgument(f"{value} is an invalid time key! h|m|s|d are valid arguments")
            except ValueError:
                raise commands.BadArgument(f"{key} is not a number!")
        return round(time)

    # Loop that run every 30 seconds for checking reminders.
    @tasks.loop(seconds= 30)
    async def remind_checker(self):
        reminders= await self.client.db.fetch(f'SELECT * FROM timers WHERE timestamp< {int(time())}')
        if not reminders:
            return
        rem_id= []
        for row in reminders:
            try:
                rem_id.append(row['reminder_id'])
                channel= self.client.get_channel(row['channel_id'])
                if not channel:
                    continue
                timer= self.client.timeconv(time()-row['timestamp'])
                embed= discord.Embed(
                    color= discord.Color.blurple(),
                    title= 'Reminder!',
                    description= f'Hey <@{channel.recipient.id}>! u asked me to remind u.'
                )
                embed.set_thumbnail(url= 'https://upload.wikimedia.org/wikipedia/commons/7/7a/Alarm_Clock_GIF_Animation_High_Res.gif')
                embed.add_field(name= 'Back in', value= timer)
                embed.add_field(name= 'Reason', value= row['reason'])
                await channel.send(f"<@{channel.recipient.id}>", embed= embed)
            except Exception as error:
                raise error
        await self.client.db.execute(f'DELETE FROM timers WHERE reminder_id= any($1::INTEGER[])', rem_id)

    # Ping command
    @commands.command(aliases= ['latency'], help= 'Check the latency of the bot',
        description= 'If too high pls report in support guild `invite` command.')
    async def ping(self, ctx):
        embed= discord.Embed(
            title= '🏓 Pong!', color= discord.Color.blurple()
        )
        embed.add_field(name= 'Websocket', value= f'`{round(self.client.latency*1000, 1)}` ms', inline= False)
        start= datetime.utcnow().timestamp()
        await self.client.db.execute('SELECT 1;')
        dblat= round((datetime.utcnow().timestamp()-start)*1000, 1)
        embed.add_field(name= 'Database', value= f'`{dblat}` ms', inline= False)
        start= datetime.utcnow().timestamp()
        await ctx.trigger_typing()
        retTrip= round((datetime.utcnow().timestamp()- start)*1000, 1)
        embed.add_field(name= 'Return Trip', value= f'`{retTrip}` ms', inline= False)
        await ctx.send(embed= embed)

    # Invite the bot command.
    @commands.command(aliases= ['support', 'links'],
        help= 'Invite the bot to your server if u found this bot amazing.')
    async def invite(self, ctx):
        embed= discord.Embed(
            title= 'UFO bot invite!',
            description= 'Hey! You can invite me to your server too :)',
            timestamp= datetime.utcnow(),
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color
        )
        embed.add_field(name= 'Invite me:',
            value= '[with full admin permissions](https://discord.com/api/oauth2/authorize?client_id=822448143508963338&permissions=8&redirect_uri=https%3A%2F%2Fdiscord.com%2Finvite%2FdaKb96xNPR&scope=applications.commands%20bot)\n[with custom permissions](https://discord.com/api/oauth2/authorize?client_id=822448143508963338&permissions=2147479550&redirect_uri=https%3A%2F%2Fdiscord.com%2Finvite%2FdaKb96xNPR&scope=applications.commands%20bot)')
        embed.add_field(name= 'Support server:',
            value= '[Click here](https://discord.gg/daKb96xNPR)')
        await ctx.send(embed= embed)

    # stats of the bot.
    @commands.command(aliases= ['info'], help= 'Get UFO bot\'s stats.')
    async def stats(self, ctx):
        tracemalloc.start()
        pyvers= str(sys.version)
        creator= await commands.UserConverter().convert(ctx, '577471505265590273')
        guilds= len(self.client.guilds)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        embed= discord.Embed(
            title= 'UFO bot stats',
            description= f"I'm currently {self.client.timeconv(time() - 1616157317, y= True)} old.\nA total of `{self.client.commandused}` commands used this shift.",
            timestamp= datetime.utcnow(),
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
            thumbnail= self.client.user.avatar_url
        )
        embed.add_field(name= '⌛Uptime', value= self.client.timeconv(time()-self.client.start_time))
        embed.add_field(name= '<:discord:847345404621881364>DiscordPy version', value= discord.__version__)
        embed.add_field(name= '🐍Python version', value= pyvers[0:5])
        embed.add_field(name= '<:saturnstress:838768214112469005>Creator', value= f'`{creator}`')
        embed.add_field(name= '👨🏾‍🤝‍👨🏼Guilds', value= guilds)
        embed.add_field(name= '📁RAM(Curren/Peek)', value= f'`{current / 10**6}`MB / `{peak / 10**6}`MB')
        await ctx.send(embed=embed)

    # Say hi
    @commands.command(aliases= ['hello', 'bonjour', 'namaste', 'hey'],
        help= 'Well hello :p')
    async def hi(self, ctx):
        greet= choice(['hay!', 'hello!', 'bonjour!', 'namaste!', 'hey!', 'hmm?', 'yes?', 'I\'m alive', 'howdy?', 'Konnichiwa',
            'What’s crackin’?', 'Yo', 'Whaddup.', 'I like your face'],p= [0.08928571428571427, 0.08928571428571427, 0.08928571428571427,
            0.08928571428571427, 0.08928571428571427, 0.08928571428571427, 0.08928571428571427, 0.05357142857142857, 0.05357142857142857,
            0.05357142857142857, 0.05357142857142857, 0.05357142857142857, 0.05357142857142857, 0.05357142857142857])
        greet+= choice(['', '🙏', '😎', '👋', '✌', '🤟'], p= [0.5, 0.1, 0.1, 0.1, 0.1, 0.1])
        await ctx.send(greet)

    # Say goodbye
    @commands.command(aliases= ['tata', 'goodbye', 'cya', 'seeya'],
        help= 'Goodbyeya')
    async def bye(self, ctx):
        greet= choice(['After a while, crocodile.', 'See you later, alligator!', 'Gotta go, buffalo.', 'Okay...bye, fry guy!',
            'Peace out!', 'Out to the door, dinosaur.', 'See you soon, racoon.', 'Adios, hippos.', 'As you wish, jellyfish!',
            'See you later, aggregator!', 'Adios, amigos.', 'Take care, polar bear!', 'After two, kangaroo!', 'After three, chimpanzee!',
            'After four, dinosaur.'])
        greet+= choice(['', '🙏', '😎', '👋', '✌', '🤟'], p= [0.75, 0.05, 0.05, 0.05, 0.05, 0.05])
        await ctx.send(greet)

    # Mr.WhoIs
    @commands.command(aliases= ['userinfo', 'whois'],
        help= 'Give the user\'s id/name(case matters)/mention',
        description= 'This command gives u partial or full info about a user depends on who was mentioned.')
    @commands.guild_only()
    async def user(self, ctx, *, user: Union[discord.Member, discord.User]= None):
        user= user or ctx.author
        acctype= 'Bot' if user.bot else 'Human User'
        embed= discord.Embed(
            title= 'User Info!',
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
            description= f'**{user}** is a {acctype}',
            timestamp= datetime.utcnow()
        )
        createdat= user.created_at
        embed.set_thumbnail(url= user.avatar_url)
        embed.add_field(name= 'Created at', value= f'`{createdat.ctime()}`')
        embed.add_field(name= 'Account age', value= f'`{self.client.timeconv(time() - createdat.timestamp(), y= True)}`')
        embed.add_field(name= 'Avatar url', value= f'\`\`[Click for pfp]({user.avatar_url})\`\`')
        embed.add_field(name= 'User id', value= f'`{user.id}`')
        if isinstance(user, discord.Member):
            try:
                embed.add_field(name= 'Activity', value= f'{str(user.activity.type).split(".")[-1]} {user.activity.name}')
            except:
                embed.add_field(name= 'Activity', value= 'They doing nothing')
            if user.color != discord.Colour.default():
                embed.add_field(name= 'Color', value= f'`{user.color}`')
            if user.nick != None:
                embed.add_field(name= 'Nickname', value= user.nick)
            if user.joined_at != None:
                embed.add_field(name= 'User joined', value= f'{self.client.timeconv(time()-user.joined_at.timestamp(), y= True)} ago')
        await ctx.send(embed=embed)

    # Guild info command
    @commands.command(aliases=['serverinfo', 'guild'],
        help= 'Just run the command and bot gives the guild info.')
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.guild_only()
    async def server(self, ctx):
        guild= ctx.guild
        embed= discord.Embed(
            title= 'Server Info!',
            description= f'**{guild.name}** has {guild.member_count}',
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
            timestamp= datetime.utcnow()
        )
        embed.set_thumbnail(url= guild.icon_url)
        embed.add_field(name= 'Owner of empicness', value= f'{guild.owner}')
        embed.add_field(name= 'Guild created at', value= guild.created_at.ctime())
        embed.add_field(name= 'Guild age', value= f'{self.client.timeconv(time() - guild.created_at.timestamp(), y= True)} old')
        reg= guild.region if isinstance(guild.region, str) else f'{guild.region}'.split('.')[-1]
        embed.add_field(name= 'Region', value= reg)
        try:
            embed.add_field(name= 'Bans🔨', value= str(len(await ctx.guild.bans())))
        except:
            pass
        roles= guild.roles
        embed.add_field(name= 'Roles/Top role', value= f'{len(roles)}/{roles[-1].mention}')
        embed.add_field(name= 'Member count', value= ctx.guild.member_count)
        if guild.premium_tier:
            embed.add_field(name= 'Boosts/Boost role', value= f'<:boost:847681752646025226>{guild.premium_tier}/{guild.premium_subscriber_role.mention}')
        if guild.mfa_level:
            embed.add_field(name= '2FA level', value= str(guild.mfa_level))
        if guild.verification_level != discord.VerificationLevel.none:
            embed.add_field(name= 'Verification level', value= f'{guild.verification_level}'.split('.')[-1])
        if guild.emojis:
            embed.add_field(name= 'Emjies count', value= len(guild.emojis))
        if guild.rules_channel:
            embed.add_field(name='Channel count/Rules', value= f'{len(guild.channels)}/<#{guild.rules_channel.id}>')
        else:
            embed.add_field(name= 'Channel count', value= len(guild.channels))
        await ctx.send(embed= embed)

    # Aha nice fact.
    @commands.command(aliases= ['fact'],
        help= 'Just run the command and bot replies with awesome fact. cool?')
    @commands.guild_only()
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def funfact(self, ctx):
        with open('{}/data/facts.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')), encoding='utf-8') as facts:
            factslist= json.load(facts)
            embed= discord.Embed(
                title= "Fact!",
                description= choice(factslist),
                color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
                timestamp= datetime.utcnow()
            )
            embed.set_author(name= f'{ctx.author}', icon_url= ctx.author.avatar_url)
            await ctx.send(embed= embed)
    
    # roles of the guild
    @commands.command(aliases= ['roles'],
        help= 'Just run the command and bot gives u the list of the roles in the server')
    @commands.guild_only()
    @commands.has_permissions(change_nickname= True)
    @commands.cooldown(3, 50, commands.BucketType.guild)
    async def rolelist(self, ctx):
        roles= ctx.guild.roles
        pag= commands.Paginator(prefix= '', suffix= '', linesep= ' • ')
        for role in roles:
            pag.add_line(line=role.mention)
        for page in pag.pages:
            embed= discord.Embed(
                title= f'{ctx.guild.name} roles!',
                color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
                description= page[2:-2],
                timestamp= datetime.utcnow()
            )
            await ctx.send(embed= embed)

    # User avatar
    @commands.command(aliases= ['pfp'],
        help= 'Usage is same as `userinfo` command.', description= 'Bot gives u the avatar of the mentioned user')
    @commands.guild_only()
    @commands.cooldown(3, 50, commands.BucketType.guild)
    async def avatar(self, ctx, *, user: Union[discord.Member, discord.User]= None):
        if not user:
            user= ctx.author
        embed= discord.Embed(
            title= f'{user.name}\'s PFP',
            timestamp= datetime.utcnow()
        )
        embed.set_image(url= user.avatar_url)
        await ctx.send(embed= embed)
    
    # Insult urself or someone.
    @commands.command(aliases= ['offend', 'discredit'],
        help= 'This command is good to insult urself or someone else.',
        description= 'Just user the command with a reply to some message and bot just sends the insult to that message.')
    @commands.guild_only()
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def insult(self, ctx):
        try:
            msg= ctx.message.reference.resolved
            try:
                await ctx.message.delete()
            except:
                pass
        except:
            msg= ctx.message
        with open('{}/data/insults.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')), encoding='utf-8') as insults:
            insultlist= json.load(insults)
            embed= discord.Embed(
                description= choice(insultlist),
                color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
                timestamp= datetime.utcnow()
            )
            embed.set_author(name= f'{ctx.author}', icon_url= ctx.author.avatar_url)
            await msg.reply(embed= embed, mention_author=False)
    
    # Snipe a message in channel
    @commands.command(aliases= ['assault'],
        help= 'A command that will help u to snipe the deleted message.',
        description= 'WARNING: Bot ignores the message deleted by bots or the message that contain embeds(can be an image or video too).')
    @commands.guild_only()
    @commands.cooldown(2, 30, commands.BucketType.channel)
    async def snipe(self, ctx, *, channel: discord.TextChannel = None):
        channel= channel or ctx.channel
        values= await self.client.db.fetchrow(f'SELECT * FROM snipes WHERE channel_id= $1', channel.id)
        if not values:
            await ctx.send(f'Nothing to snipe in {channel.mention}')
            return
        embed= discord.Embed(
            description= values['message_content'],
            timestamp= datetime.utcfromtimestamp(float(values['timestamp'])),
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color
        )
        embed.add_field(name= 'Sent by', value= f'<@{values["user_id"]}>')
        await ctx.send(embed= embed)

    # Reminder and timer
    @commands.group(aliases= ['remindme', 'timer'], invoke_without_command=True,
        help= 'Use the format like 4d3h30m30s where dhms are respective units of time. U can\'t have timer below 2m or above 14d.',
        description= 'This command lets you set/remove a reminder that u wish the bot to remind u. You can only have upto `10` reminders per time')
    async def reminder(self, ctx):
        await ctx.send_help(ctx.command)
    @reminder.command(aliases= ['create'], help= 'Adds a reminder, send time in format d|h|m|s with respective values, like `3d12h30m30s` or `1d30m`',
        usage= '<time> [reason]')
    async def add(self, ctx, timep, *, reason= None):
        timep= self.convert(timep)
        if timep> 1209600:
            await ctx.send('Timer more then 14 days not accepted')
            return
        elif timep< 120:
            await ctx.send('timers below 2 mins are considered as troll timers. Sorry')
            return
        if not ctx.author.dm_channel:
            channel= await ctx.author.create_dm()
        else:
            channel= ctx.author.dm_channel
        totalTimers= await self.client.db.fetchval(f'SELECT COUNT(reminder_id) FROM timers WHERE channel_id= {channel.id}')
        if totalTimers>= 10:
            await ctx.send('You have crossed the limit of reminders `10`')
            return
        timest= int(time() + timep)
        rem_id= await self.client.db.fetchval('INSERT INTO timers(channel_id, reason, timestamp) VALUES ($1, $2, $3) RETURNING reminder_id',
            channel.id,
            reason,
            timest
        )
        embed= discord.Embed(
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
            title= 'Reminder set!',
            description= f'**{ctx.author}** i will remind u after `{self.client.timeconv(timep)}`'
        )
        embed.set_footer(icon_url= 'https://upload.wikimedia.org/wikipedia/commons/7/7a/Alarm_Clock_GIF_Animation_High_Res.gif',
            text= f'Reminder ID : {rem_id}')
        embed.set_author(icon_url= ctx.author.avatar_url, name= str(ctx.author))
        await ctx.send(embed=embed)
    @reminder.command(aliases= ['delete'], help= 'Removes a reminder of given reminder id, use `reminders` command to get reminder id')
    async def remove(self, ctx, reminderID: int):
        timers= await self.client.db.fetch(f'SELECT reminder_id FROM timers WHERE user_id= {ctx.auhtor.id} AND reminder_id= {reminderID}')
        if not timers:
            await ctx.send(f'No timers found with ID `{reminderID}`` and user **{ctx.author}**.')
            return
        await self.client.db.execute('DELETE FROM timers WHERE reminder_id= {reminderID}')
        await ctx.send(f'Removed the timer `{reminderID}`')

    # Reminder listing
    @commands.command(aliases= ['timers', 'reminds'])
    @commands.guild_only()
    async def reminders(self, ctx):
        pag= commands.Paginator(prefix='', suffix='', max_size=1500)
        desc= 'U currently have no reminders. Start adding them with `reminder` command'
        try:
            rows= await self.client.db.fetch(f"SELECT reminder_id, reason, timestamp FROM timers WHERE channel_id= {ctx.author.dm_channel.id or 'NULL'}")
        except:
            return await ctx.send(desc)
        if not rows:
            await ctx.send(desc)
            return
        for row in rows:
            timetogo= row['timestamp']- time()
            desc= f"ID: {row['reminder_id']} ({row['reason'] or 'No reason was given'})\nGoes off in: `{self.client.timeconv(timetogo)}`"
            pag.add_line(desc)
        for page in pag.pages:
            embed= discord.Embed(
                title= 'Reminders!',
                description= page,
                color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
                timestamp= datetime.utcnow()
            )
            embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
            await ctx.send(embed= embed)

    # Decancer a text
    @commands.command(aliases= ['dcan'],
        help= 'Decancer a text, but if a person is mentioned and user and bot has proper permissions then the bot changes the user\'s name.',
        description= 'Bot don\'t accept long texts bc the library bot uses isn\'t that fast in cleaning text. Sorry for that.')
    @commands.guild_only()
    async def decancer(self, ctx, *, text: Union[discord.Member, str]):
        dcantext= text if isinstance(text, str) else text.display_name
        if len(dcantext) > 50:
            await ctx.send('Message too long, not more then 50 words pls, python isn\'t as fast in decancering text as js.')
            return
        dcantext= clean(dcantext, lower= False)
        if isinstance(text, discord.Member):
            if ctx.author.guild_permissions.manage_nicknames:
                await text.edit(nick= dcantext)
                await ctx.send(f'**{text}**\'s nickname changed to: `{dcantext}`')
            else:
                await ctx.send(f'Dcancer version of **{text}** name is: `{dcantext}`')
        else:
            await ctx.send(f'Dcancer version of given text is: `{dcantext}`')

    # Member count
    @commands.command(aliases= ['members', 'membercount'],
        help= 'Display the member count of the server')
    @commands.guild_only()
    @commands.cooldown(2, 90, commands.BucketType.guild)
    async def serversize(self, ctx):
        embed= discord.Embed(
            title= f'{ctx.guild.member_count} Members',
            color= ctx.me.color if not ctx.me.color == discord.Color.default() else discord.Color.blurple()
        )
        embed.set_author(name= str(ctx.guild), icon_url= ctx.guild.icon_url)
        await ctx.send(embed= embed)

    # I choose what i ~like~
    @commands.command(aliases= ['coo', 'choice'], help= 'I choose ~~||what i like||~~ like seriously randomly.',
        descripiton= 'You can provide your choices like `stay "do the homework" lie die sleep "escape home"`')
    @commands.guild_only()
    async def choose(self, ctx, *choices):
        await ctx.send(f'I choose :) {choice(list(choices))}')

    # Heads or Tails
    @commands.command(aliases= ['headtail', 'ht', 'coin', 'flip', 'toss'], help= 'Flip a coin.')
    @commands.guild_only()
    async def coinflip(self, ctx):
        toss= randint(0,2)
        embed= discord.Embed(
            title= f'Its {"HEADS" if toss == 0 else "TAILS"}',
            color= discord.Color.dark_theme()
        )
        if toss== 0:
            embed.set_thumbnail(url= 'https://cdn.discordapp.com/attachments/823847654010257418/857848100135239680/5845e69dfb0b0755fa99d7ef.png')
        else:
            embed.set_thumbnail(url= 'https://cdn.discordapp.com/attachments/823847654010257418/857852110879457290/quote-form-pinkushikaworks-dog-tail-png-280_340.png')
        await ctx.send(embed= embed)

    # I again mention "Me no furry"
    @commands.command(aliases= ['owo', 'owoify'], help= 'ˁ(⦿@ᴥ⦿*)ˀ OwOifies Youw Text༼ (´・ω・`) ༽ ✿(≗ﻌ≗^)',
        description= 'I M NOT **FURRY**, I added this cowommand bc owhy nowot', usage= '[LevelofOWO=2] <Dwop_Youw_owo_hewe_ÒwÓ>')
    async def owoifier(self, ctx, level: Union[int, str]= 2, *, owo_string= None):
        if isinstance(level, int):
            if not level in [1,2,3]:
                return await ctx.send('o...owo?! the level awgument must be between 1 and thwee (1 and 3 incwuded!). You can just pass the text without level and it will default to 2')
        elif isinstance(level, str):
            owo_string= f'{level} {owo_string if owo_string else ""}'
            level= 2
        if not owo_string:
            return await ctx.send('What to owo at?')
        async def aio_replace(main_str, first_str, second_str):
            return main_str.replace(first_str, second_str)
        
        owo_string = await aio_replace(owo_string, 'r', 'w')
        owo_string = await aio_replace(owo_string, 'R', 'W')
        owo_string = await aio_replace(owo_string, 'l', 'w')
        owo_string = await aio_replace(owo_string, 'L', 'W')
        owo_string = await aio_replace(owo_string, 'b', 'bw')
        owo_string = await aio_replace(owo_string, 'B', 'BW')
        if level == 3:
            owo_string = await aio_replace(owo_string, 'o', 'owo')
            owo_string = await aio_replace(owo_string, 'O', 'OwO')
            owo_string = await aio_replace(owo_string, '!', f'! {choice(owo_emotes)}{choice(owo_emotes)}')
            owo_string = await aio_replace(owo_string, '?', f'? {choice(owo_emotes)}{choice(owo_emotes)}')
            owo_string = await aio_replace(owo_string, '.', f'{choice(owo_emotes)}{choice(owo_emotes)}')
        if level == 2:
            owo_string = await aio_replace(owo_string, '!', f'! {choice(owo_emotes)}')
            owo_string = await aio_replace(owo_string, '?', f'? {choice(owo_emotes)}')
            owo_string = await aio_replace(owo_string, '.', f'{choice(owo_emotes)}')

        for vowel in owo_vowels:
            if f'n{vowel}' in owo_string:
                owo_string = await aio_replace(owo_string, f'n{vowel}', f'ny{vowel}')
            elif f'N{vowel}' in owo_string:
                owo_string = await aio_replace(owo_string, f'N{vowel}', f'NY{vowel}')
            
        for vowel in owo_vowels:
            if f'b{vowel}' in owo_string:
                owo_string = await aio_replace(owo_string, f'b{vowel}', f'bw{vowel}')
            elif f'B{vowel}' in owo_string:
                owo_string = await aio_replace(owo_string, f'B{vowel}', f'BW{vowel}')
        
        if level == 2:
            owo_string = f'{choice(owo_emotes)} {owo_string} {choice(owo_emotes)}'
        elif level == 3:
            owo_string = f'{choice(owo_emotes)} {choice(owo_emotes)} {owo_string} {choice(owo_emotes)} {choice(owo_emotes)}'
        await ctx.send(owo_string)

    # Changes the font of your text
    @commands.command(help= '𝕮𝖍𝖆𝖓𝖌𝖊𝖘 𝖙𝖍𝖊 𝖋𝖔𝖓𝖙 𝖔𝖋 𝖞𝖔𝖚𝖗 𝖙𝖊𝖝𝖙.')
    async def changefont(self, ctx, *, text):
        todo= randint(4)
        if not todo:
            await ctx.send(fancy.bold(text))
        elif todo== 1:
            await ctx.send(fancy.box(text))
        elif todo== 2:
            await ctx.send(fancy.light(text))
        elif todo== 3:
            await ctx.send(fancy.sorcerer(text))

    # Chanck how many times moderator have YEETED your or someone if YOU ARE MOD
    @commands.command(aliases= ['yeets'], help= 'So basically this simply helps you how many times you were yeeted by mods.')
    async def warnings(self, ctx, member: discord.Member= None):
        async def get_warns(member):
            async with self.client.db.acquire() as conn:
                await conn.set_type_codec(
                    'json',
                    encoder= json.dumps,
                    decoder= json.loads,
                    schema='pg_catalog'
                )
                warns= await conn.fetchval('SELECT warns::json FROM guildsettings WHERE guild_id = $1', member.guild.id)
                warns= warns or {}
                if not str(member.id) in warns.keys():
                    return 0
                else:
                    return warns[str(member.id)]
        if member:
            modrole= self.client.db.fetchval('SELECT modrole_id FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
            if not modrole: modrole= 0
            is_mod= False
            if modrole in [role.id for role in member.roles]:
                is_mod= True
            elif member.guild_permissions.manage_guild:
                is_mod= True
            if not is_mod:
                return await ctx.send('Non-mods may only see warnings assign to them.')
            else:
                warns= await get_warns(member)
        else:
            warns= await get_warns(ctx.author)
        if not warns:
            await ctx.send(f'**{f"{member} is" if member else "You are"}** all great, have no warnings :^)')
        else:
            embed= discord.Embed(
                description= f'**{member if member else "You"}** have `{warns}` warnings.',
                color= ctx.me.color if not ctx.me.color == discord.Color.default() else discord.Color.blurple()
            )
            embed.set_author(name= str(member) if member else str(ctx.author), icon_url= member.avatar_url if member else ctx.author.avatar_url)
            await ctx.send(embed= embed)

    # Sends a paginated output of server emojies
    @commands.command(name= 'emojis', aliases= ['emojies'], help= 'Sends a list of guild emojies with proper notations.')
    async def _emojis(self, ctx):
        pag= commands.Paginator(prefix= '', suffix= '', max_size= 750)
        emojis= ctx.guild.emojis
        for emoji in emojis:
            line= f'{emoji} `{emoji}`'
            pag.add_line(line)
        embed= discord.Embed(title= 'Server emojis!',description= f'This server has `{len(emojis)}`',color= discord.Color.blurple())
        embed.set_author(name= str(ctx.me), icon_url= ctx.me.avatar_url)
        pags= pag.pages
        embed.set_footer(text= f'Page 1/{len(pags)}')
        del pag
        embed.description= pags[0]
        pag_now= 0
        page_no= range(1, len(pags)+1)
        msg: discord.Message= await ctx.send(embed= embed)
        if len(pags) <= 1: return
        def check(r, u):
            return str(r.emoji) in ['◀', '⏹', '▶'] and u.id== ctx.author.id and r.message.id == msg.id
        def check2(rrr: discord.RawReactionActionEvent):
            return str(rrr.emoji) in ['◀', '▶'] and rrr.user_id == ctx.author.id and rrr.message_id == msg.id
        await msg.add_reaction('◀')
        await msg.add_reaction('⏹')
        await msg.add_reaction('▶')
        for i in range(0, 25):
            done, pending = await asyncio.wait([ self.client.wait_for('raw_reaction_remove', timeout= 45, check= check2),
                self.client.wait_for('reaction_add', timeout= 45, check= check)
                ], return_when= asyncio.FIRST_COMPLETED)
            try:
                res = done.pop().result()
                if isinstance(res, discord.RawReactionActionEvent):
                    emo= str(res.emoji)
                else:
                    emo= str(res[0].emoji)
                if emo == '◀':
                    pag_now-=1
                    if abs(pag_now) == len(pags): pag_now= 0
                elif emo == '⏹':
                    raise Exception
                else:
                    pag_now+=1
                    if abs(pag_now) == len(pags): pag_now= 0
            except:
                try: await msg.clear_reactions()
                except: pass
                for future in done:
                    future.exception()
                for future in pending:
                    future.cancel()
                break
            for future in done:
                future.exception()
            for future in pending:
                future.cancel()
            embed.description= pags[pag_now]
            embed.set_footer(text= f'Page {page_no[pag_now]}/{len(pags)}')
            await msg.edit(embed= embed)
        await msg.edit(content= '**Pagination Ended**')

    # Flips the text
    @commands.command(aliases= ['superimpose'], help= 'Reverse your text!'[::-1])
    async def mirror(self, ctx, *, text: str):
        if len(text)> 1000:
            return await ctx.send('The message was too long, try not more than 1000 letters.')
        REV_LETTERS = 'ɐqɔpǝɟɓɥᴉſʞๅɯuodbɹsʇnʌʍxʎzⱯꓭꓛꓷƎꓞꓨHIſꓘꓶWNOꓒῸꓤSꓕꓵꓥMX⅄\\¿ʻ⅋'
        i= 0
        embed= discord.Embed(
            title= 'Your text',
            description= f'```{text}```',
            color= ctx.me.color if not ctx.me.color == discord.Color.default() else discord.Color.blurple()
        )
        for letter in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXY/?,&':
            text= text.replace(letter, REV_LETTERS[i])
            i+= 1
        embed.add_field(name= 'Reversed text', value= f'```{text}```', inline= False)
        await ctx.send(embed= embed)


def setup(client):
    client.add_cog(General(client))
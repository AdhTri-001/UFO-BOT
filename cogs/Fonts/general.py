from datetime import datetime
from numpy.random import choice
import discord, sys, tracemalloc
from discord.ext import commands, tasks
from time import time
from typing import Union
import json, os, re
from cleantext import clean

class General(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    async def loopstarter(self):
        while True:
            if self.client.inited:
                print(f'Starting Loops in {self.__class__.__name__}...')
                self.remind_checker.start()
                break

    print("General.py has been loaded\n-----------------------------------")

    # Checking for disabled commands
    async def cog_check(self, ctx):
        if not ctx.guild:
            return False
        discmds= await self.client.db.tables['guildsettings'].select('discmds', where= {'guild_id': ctx.guild.id})
        try:
            return not ctx.command.name in discmds[0]['discmds']
        except: return True
    
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
        reminders= await self.client.db.tables['timers'].select('*', where= [['timestamp', '<', time()]])
        if not reminders:
            return
        rem_id= []
        for row in reminders:
            try:
                rem_id.append(row['reminder_id'])
                channel= self.client.get_channel(id= int(row['channel_id']))
                timer= self.client.timeconv(time()-row['timestamp'])
                embed= discord.Embed(
                    color= discord.Color.blurple(),
                    title= 'Reminder!',
                    description= f'Hey <@{row["user_id"]}>! u asked me to remind u in {channel.mention}.'
                )
                embed.set_thumbnail(url= 'https://upload.wikimedia.org/wikipedia/commons/7/7a/Alarm_Clock_GIF_Animation_High_Res.gif')
                embed.add_field(name= 'Reason', value= row['reason'])
                await channel.send(f"<@{row['user_id']}>", embed= embed)
            except:
                pass
        await self.client.db.tables['timers'].delete(where= [['reminder_id', 'in', rem_id]])

    #Ping command
    @commands.command(aliases= ['latency'], help= 'Check the latency of the bot',
        description= 'If too high pls report in support guild `invite` command.')
    async def ping(self, ctx):
        start= time()
        msg= await ctx.send(f'Pinging...')
        embed= discord.Embed(title= '🏓 Pong!', color= ctx.me.color)
        ping = round(self.client.latency * 1000, 1)
        embed.add_field(name= 'Discord Webhook latency', value= f'`{ping}` ms', inline= False)
        dbtime= time()
        test= await self.client.db.tables['guildsettings'].select('guild_id', where= {'guild_id' : ctx.guild.id})
        dbtime= round((time()-dbtime) * 1000, 1)
        embed.add_field(name= 'DB latency', value= f'`{dbtime}` ms', inline= False)
        end= round((time()-start) * 1000, 1)
        embed.add_field(name= 'Message return trip', value= f'`{end}` ms', inline= False)
        await msg.edit(content= '', embed= embed)

    # Invite the bot command.
    @commands.command(aliases= ['support', 'links'],
        help= 'Invite the bot to your server if u found this bot amazing.')
    async def invite(self, ctx):
        embed= discord.Embed(
            title= 'UFO bot invite!',
            description= 'Hey! You can invite me to your server too :)',
            timestamp= datetime.utcnow(),
            color= discord.Color.random()
        )
        embed.add_field(name= 'Invite me:',
            value= '[with full admin permissions](https://discord.com/api/oauth2/authorize?client_id=822448143508963338&permissions=8&redirect_uri=https%3A%2F%2Fdiscord.com%2Finvite%2FyQSmcGCThD&scope=applications.commands%20bot)\n[with custom permissions](https://discord.com/api/oauth2/authorize?client_id=822448143508963338&permissions=2084564471&redirect_uri=https%3A%2F%2Fdiscord.com%2Finvite%2FyQSmcGCThD&scope=applications.commands%20bot)')
        embed.add_field(name= 'Support server:',
            value= '[Click here](https://discord.gg/tZGJjGZvvd)')
        
        await ctx.send(embed= embed)

    # stats of the bot.
    @commands.command(aliases= ['info'], help= 'Get UFO bot\'s stats.')
    async def stats(self, ctx):
        tracemalloc.start()
        uptime= self.client.timeconv(time() - self.client.start_time)
        pyvers= str(sys.version)
        creator= await commands.UserConverter().convert(ctx, '577471505265590273')
        guilds= len(self.client.guilds)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        embed= discord.Embed(
            title= 'UFO bot stats',
            description= f"I'm currently {self.client.timeconv(time() - 1616157317, y= True)} old.\nA total of `{self.client.commandused}` commands used this shift.",
            timestamp= datetime.utcnow(),
            color= ctx.me.color,
            thumbnail= self.client.user.avatar_url
        )
        embed.add_field(name= '⌛Uptime', value= uptime)
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
        greet+= choice(['', '🙏', '😎', '👋', '✌', '🤟'], p= [0.75, 0.05, 0.05, 0.05, 0.05, 0.05])
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
    async def user(self, ctx, *, user: Union[discord.Member, discord.User]):
        acctype= 'Bot' if user.bot else 'Human User'
        color= user.color if user.color != discord.Color.default() else ctx.me.color
        embed= discord.Embed(
            title= 'User Info!',
            color= color,
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
            embed.add_field(name= 'Status', value= str(user.status).split(".")[-1])
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
            color= ctx.me.color,
            timestamp= datetime.utcnow()
        )
        embed.set_thumbnail(url= guild.icon_url)
        embed.add_field(name= 'Owner of empicness', value= f'{guild.owner}')
        embed.add_field(name= 'Guild created at', value= guild.created_at.ctime())
        embed.add_field(name= 'Guild age', value= f'{self.client.timeconv(time() - guild.created_at.timestamp(), y= True)} old')
        reg= guild.region if isinstance(guild.region, str) else f'{guild.region}'.split('.')[-1]
        embed.add_field(name= 'Region', value= reg)
        embed.add_field(name= 'Bans🔨', value= str(len(await ctx.guild.bans())))
        roles= guild.roles
        embed.add_field(name= 'Roles/Top role', value= f'{len(roles)}/{roles[-1].mention}')
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
                color= ctx.me.color,
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
                color= ctx.me.color,
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
            await ctx.message.delete()
        except:
            msg= ctx.message
        with open('{}/data/insults.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')), encoding='utf-8') as insults:
            insultlist= json.load(insults)
            embed= discord.Embed(
                description= choice(insultlist),
                color= ctx.me.color,
                timestamp= datetime.utcnow()
            )
            embed.set_author(name= f'{ctx.author}', icon_url= ctx.author.avatar_url)
            await msg.reply(embed= embed, mention_author=False)
    
    # Snipe a message in channel
    @commands.command(aliases= ['assault'],
        help= 'A command that will help u to snipe the deleted message.',
        description= 'WARNING: Bot ignores the message deleted by bots or the message that contain embeds(can be an image or video too).')
    @commands.guild_only()
    @commands.cooldown(5, 30, commands.BucketType.channel)
    async def snipe(self, ctx, *, channel: discord.TextChannel = None):
        channel= channel or ctx.channel
        values= await self.client.db.tables['snipes'].select('*', where= {'channel_id': channel.id})
        try:
            values= values[0]
        except IndexError:
            await ctx.send(f'Nothing to snipe in {channel.mention}')
            return
        embed= discord.Embed(
            description= values['message_content'],
            timestamp= datetime.utcfromtimestamp(float(values['timestamp'])),
            color= ctx.me.color
        )
        embed.set_author(icon_url= values['author_pfp'], name= values['author_name'])
        await ctx.send(embed= embed)
    @snipe.error
    async def snipe_error(self, ctx, error):
        raise error

    # Reminder and timer
    @commands.group(aliases= ['remindme', 'timer'], invoke_without_command=True,
        help= 'Use the format like 4d3h30m30s where dhms are respective units of time. U can\'t have timer below 2m or above 14d.',
        description= 'This command lets you set/remove a reminder that u wish the bot to remind u.')
    @commands.guild_only()
    async def reminder(self, ctx):
        await ctx.send_help(ctx.command)
    @reminder.command(aliases= ['create'], help= 'Adds a reminder')
    async def add(self, ctx, timep, *, reason= 'no reason given.'):
        timep= self.convert(timep)
        if timep> 1209600:
            await ctx.send('Timer more then 14 days not accepted')
            return
        elif timep< 120:
            await ctx.send('timers below 2 mins are considered as troll timers. Sorry')
            return
        timest= int(time() + timep)
        await self.client.db.tables['timers'].insert(
            user_id= str(ctx.author.id),
            reason= reason,
            timestamp= timest,
            channel_id= str(ctx.channel.id)
        )
        rem_id= await self.client.db.tables['timers'].select('reminder_id', where= {'user_id': ctx.author.id, 'timestamp': timest})
        rem_id= rem_id[0]['reminder_id']
        embed= discord.Embed(
            color= ctx.me.color,
            title= 'Reminder set!',
            description= f'**{ctx.author}** i will remind u after `{self.client.timeconv(timep)}`'
        )
        embed.set_footer(icon_url= 'https://upload.wikimedia.org/wikipedia/commons/7/7a/Alarm_Clock_GIF_Animation_High_Res.gif',
            text= f'Reminder ID : {rem_id}')
        embed.set_author(icon_url= ctx.author.avatar_url, name= str(ctx.author))
        await ctx.send(embed=embed)
    @reminder.command(aliases= ['delete'], help= 'Removes a reminder of given reminder id, user `reminders` command to get reminder id')
    async def remove(self, ctx, reminderID: int):
        timers= await self.client.db.tables['timers'].select('reminder_id', where= {'reminder_id': reminderID, 'user_id': ctx.author.id})
        if not timers:
            await ctx.send(f'Not timers found that are with ID {reminderID} and u as the user')
            return
        await self.client.db.tables['timers'].delete(where= {'reminder_id': reminderID})
        await ctx.send('Removed the timer!')

    # Reminder listing
    @commands.command(aliases= ['timers', 'reminds'])
    @commands.guild_only()
    async def reminders(self, ctx):
        pag= commands.Paginator(prefix='', suffix='', max_size=1500)
        rows= await self.client.db.tables['timers'].select('reminder_id', 'timestamp', 'reason',where= {'user_id': ctx.author.id})
        desc= 'U currently have no reminders. Start adding them with `reminder` command'
        if not rows:
            await ctx.send(desc)
        for row in rows:
            timetogo= row['timestamp']- time()
            desc= f"ID: {row['reminder_id']} ({row['reason']})\nGoes off in: `{self.client.timeconv(timetogo)}`"
            pag.add_line(desc)
        for page in pag.pages:
            embed= discord.Embed(
                title= 'Reminders!',
                description= page,
                color= ctx.me.color,
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

    # Bot count
    @commands.command(aliases= ['notmembers'],
        help= 'This command lets u see the bot count')
    @commands.guild_only()
    async def bots(self, ctx):
        bots= []
        members= await ctx.guild.chunk(cache= False)
        for member in members:
            if member.bot:
                bots.append(member)
        embed= discord.Embed(
            title= f'Bots in {ctx.guild}',
            color= discord.Color.blurple(),
            description= f'This guild has a total of {len(bots)} bots.',
            timestamp= datetime.utcnow()
        )
        botmentions= []
        for bot in bots:
            botmentions.append(bot.mention)
        if len(botmentions) > 100:
            botmentions= ["Too many I can't list all."]
        embed.add_field(name= f'Bot list', value= ' • '.join(botmentions), inline= False)
        await ctx.send(embed= embed)

    # Member count
    @commands.command(aliases= ['members', 'membercount'],
        help= 'Display the member count of the server')
    @commands.guild_only()
    @commands.cooldown(2, 90, commands.BucketType.guild)
    async def serversize(self, ctx):
        members= await ctx.guild.chunk(cache= False)
        embed= discord.Embed(
            title= f'{len(members)} Members',
            color= ctx.me.color
        )
        embed.set_author(name= str(ctx.guild), icon_url= ctx.guild.icon_url)
        await ctx.send(embed= embed)

def setup(client):
    client.add_cog(General(client))
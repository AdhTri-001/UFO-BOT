import asyncio, os
import json
import discord
from discord.ext import commands
from typing import Union
from datetime import datetime
from UFO_Bot import Ufo_bot
from io import StringIO
from textwrap import indent
from traceback import format_exc
from contextlib import redirect_stdout

MODLOG_PARAMS= ['ban','unban','kick','guild-updates','channel-updates','channel-overwrites','roles','message-edit','bulk-delete','message-pin','warns']

class Settings(commands.Cog):
    def __init__(self, client):
        self.client: Ufo_bot= client
        self._last_result= None

    print("Settings.py has been loaded\n-----------------------------------")

    async def cog_check(self, ctx):
        if ctx.guild:
            return True
        else:
            return False

    def is_guild_owner():
        async def predicate(ctx):
            return ctx.author.id== ctx.guild.owner_id
        return commands.check(predicate)

    async def send_greet(self, member, channel= None):
        raw= await self.client.db.fetchrow('SELECT greetmsg, greetch FROM guildsettings WHERE guild_id = $1', member.guild.id)
        if not raw['greetch']: return
        channel= member.guild.get_channel(raw['greetch'])
        desc= raw['greetmsg'] or 'Welcome {usermention} to **{server}**. Hope you have a great stay here. Pls read the server rules and follow them.'
        desc= desc.format(
            usermention= member.mention,
            server= str(member.guild),
            userid= member.id,
            username= str(member),
            joinedat= member.joined_at.ctime(),
            createdat= discord.Object(member.id).created_at.ctime()
        )
        embed= discord.Embed(
            title= 'Welcome!',
            description= desc,
            color= discord.Color.blurple(),
            timestamp= datetime.utcnow()
        )
        embed.set_author(name= member.guild.name, icon_url= member.guild.icon_url)
        embed.set_thumbnail(url= member.avatar_url)
        await channel.send(embed= embed)

    async def cog_check(self, ctx):
        if ctx.guild:
            return True
        else:
            False

    # Bot Settings Commands
    async def embeder(self, ctx, change:str, to:str):
        embed= discord.Embed(
            title= '⚙ Settings', description= f'{change} set to {to}',
            color= discord.Color.dark_theme(), timestamp= datetime.utcnow())
        embed.set_author(name= ctx.author, icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)
    
    # T_T Oh! why do we show offence to a single character ``.``
    @commands.command(aliases= ['pref'],
        help="come on this is easy, just pass the prefix of ur preference",
        description="Prefix can't be more then 5 letters. U need admin perms to use this command"
    )
    @commands.has_guild_permissions(administrator= True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def prefix(self, ctx, prefix: str= '.'):
        if len(str(prefix)) > 10:
            await ctx.send('Your prefix can\'t be longer than 10 letters!')
            return
        prefix= await self.client.db.fetchval('INSERT INTO guildsettings(guild_id, prefix) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET prefix = EXCLUDED.prefix RETURNING prefix', ctx.guild.id, prefix)
        discmds= self.client.cache.get(ctx.guild.id, {"discmds":[], "blackch":[]})
        blackch, discmds= discmds['blackch'],discmds['discmds']
        self.client.cache.update({ctx.guild.id:{"prefix":prefix,"discmds":discmds, "blackch":blackch}})
        await self.embeder(ctx, 'Prefix', f'`{prefix}`')

    # My dear mod, aka bot master
    @commands.command(
        help="Mention the role, or give role id, or exect role name.",
        description="Set the mod role that can use commands marked under catagory Moderation."
    )
    @commands.has_guild_permissions(administrator= True)
    async def modrole(self, ctx, *, role: discord.Role = None):
        if not role:
            await self.client.db.execute('INSERT INTO guildsettings(guild_id, modrole_id) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
                DO UPDATE SET modrole_id = EXCLUDED.modrole_id', ctx.guild.id, None)
            await self.embeder(ctx, 'Mod Role', 'None')
            return
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, modrole_id) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
                DO UPDATE SET modrole_id = EXCLUDED.modrole_id', ctx.guild.id, role.id)
        await self.embeder(ctx, 'Mod Role', role.mention)
    
    # Yes! modlogs are for, for and only for no one T_T ppl just ignore them or mark as read.
    @commands.group(aliases= ['mlog','modlogs','logs','log'],
        help="See the modlogs settings of the server.",
        description="This command needs `admin` perms too, members can check there warnings with `warnings`",
        invoke_without_command= True
    )
    @commands.has_guild_permissions(administrator= True)
    async def modlog(self, ctx):
        enabledMlogs= await self.client.db.fetchval('SELECT logging FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        if not enabledMlogs:
            desc= [f'<:uncheck:857494289415798784> {action.capitalize()}' for action in MODLOG_PARAMS]
        else:
            desc= []
            for action in MODLOG_PARAMS:
                if action in enabledMlogs:
                    desc.append(f'<:check:857494064294264862> {action.lower()}')
                else:
                    desc.append(f'<:uncheck:857494289415798784> {action.capitalize()}')
        embed= discord.Embed(
            title= '⚙ Modlog settings for this server!',
            description= '\n'.join(desc),
            color= discord.Color.dark_theme()
        )
        embed.set_author(name= str(ctx.guild), icon_url= ctx.guild.icon_url)
        await ctx.send(embed= embed)
    @modlog.command(aliases= ['enable', 'true'],
        help="enables the mod logs. Pass `all` to enable all modlog actions."
    )
    async def on(self, ctx, action= 'all'):
        if action.lower() == 'all':
            def check(m):
                return m.channel.id == ctx.channel.id and m.content.lower() in ['y','n'] and m.author.id == ctx.author.id
            msg= await ctx.send('This will enable all modlogs action, do you want to continue? (y/n)')
            try:
                msg= await self.client.wait_for('message', check= check, timeout= 20)
            except:
                pass
            if msg.content.lower() == 'y':
                await self.client.db.execute('INSERT INTO guildsettings(guild_id, logging) VALUES ($1, $2::text[]) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
                    DO UPDATE SET logging = EXCLUDED.logging', ctx.guild.id, MODLOG_PARAMS)
            else:
                return await ctx.send('Alright!')
        elif action.lower() not in MODLOG_PARAMS:
            return await ctx.send(f'Wrong parameter. See `{ctx.prefix}modlog` to get list of mod log actions that bot understands.')
        else:
            await self.client.db.execute('INSERT INTO guildsettings(guild_id, logging) VALUES ($1, ARRAY[$2]) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
                DO UPDATE SET logging = guildsettings.logging || EXCLUDED.logging', ctx.guild.id, action.lower())
        await self.embeder(ctx, 'Modlogs', f'`enabled {action}`')
    @modlog.command(aliases= ['disable', 'false'],
        help="enables the mod logs. Pass `all` to disable all modlog actions.",
        description=""
    )
    async def off(self, ctx: commands.Context, action= 'all'):
        if action.lower() == 'all':
            def check(m):
                return m.channel.id == ctx.channel.id and m.content in ['y','n'] and m.author.id == ctx.author.id
            msg= await ctx.send('This will disable all modlogs action, do you want to continue? (y/n)')
            try:
                msg= await self.client.wait_for('message', check= check, timeout= 20)
            except:
                pass
            if msg.content.lower() == 'y':
                await self.client.db.execute('INSERT INTO guildsettings(guild_id, logging) VALUES ($1, NULL) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
                    DO UPDATE SET logging = EXCLUDED.logging', ctx.guild.id)
            else:
                return await ctx.send('Alright!')
        elif action.lower() not in MODLOG_PARAMS:
            return await ctx.send(f'Wrong parameter. See `{ctx.prefix}modlog` to get list of mod log actions that bot understands.')
        else:
            await self.client.db.execute('INSERT INTO guildsettings(guild_id, logging) VALUES ($1, ARRAY_REMOVE(logging, $2)) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
                DO UPDATE SET logging = EXCLUDED.logging', ctx.guild.id, action.lower())
        await self.embeder(ctx, 'Modlogs', f'`disabled {action}`')
    @modlog.command(aliases= ['ch'],
        help="Mention/provide id/Name the channel.",
        description=""
    )
    async def channel(self, ctx, channel: discord.TextChannel = None):
        channel= channel or ctx.channel
        oldchannel= await self.client.db.fetchval('SELECT logch FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        if oldchannel:
            msg= await ctx.send(f'There already exist a mod-log channel, <#{oldchannel}> `{oldchannel}` Do you want to continue? (y/n)')
            def check(m):
                return m.channel.id == ctx.channel.id and m.content in ['y','n'] and m.author.id == ctx.author.id
            try:
                msg= await self.client.wait_for('message', check= check, timeout= 20)
            except:
                pass
            if msg.content.lower() == 'y':
                await self.client.db.execute('UPDATE guildsettings set logch = $2 WHERE guild_id = $1', ctx.guild.id, channel.id)
            else:
                return await ctx.send('Alright!')
        else:
            await self.client.db.execute('INSERT INTO guildsettings(guild_id, logch) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
                DO UPDATE SET logch = EXCLUDED.logch', ctx.guild.id, channel.id)
        await self.embeder(ctx, 'Mod-log channel', channel.mention)
    
    # If ppl don't like @everyone ping so mention startrole. Think smart
    @commands.command(aliases= ['strole'],
        help="Mention the role, or give role id, or exect role name. Please!",
        description="Greet the new comers with a start role."
    )
    @commands.has_guild_permissions(administrator= True)
    async def startrole(self, ctx, *, role: discord.Role = None):
        if role == None:
            roleid= None
            rolemention= None
        else:
            roleid= role.id
            rolemention= role.mention
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, startrole_id) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET startrole_id = EXCLUDED.startrole_id', ctx.guild.id, roleid)
        await self.embeder(ctx, 'Start role', rolemention)

    # The role to dismiss cancerous ppl.
    @commands.command(
        help="Mention the role, or give role id, or exect role name.",
        description="Sets the role to be given while muting someone."
    )
    @commands.has_guild_permissions(administrator= True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def muterole(self, ctx, *, role: discord.Role= None):
        oldmuterole= await self.client.db.fetchval('SELECT muterole_id FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        def check(m):
            return m.content.lower() in ['y', 'n'] and m.author == ctx.author
        if role == None and oldmuterole== None:
            role= await ctx.guild.create_role(name= 'Muted', colour= discord.Color.light_grey(), reason= f'{ctx.author.name}#{ctx.author.discriminator}')
        elif role == None:
            embed= discord.Embed(description= 'This guild already have a mute role setup <@&'+oldmuterole[0]['muterole_id']+'>.\nYou want me to change it and make a new one? (y/n)')
            warning= await ctx.send(embed= embed)
            try:
                msg= await self.client.wait_for('message', timeout= 20, check= check)
            except asyncio.TimeoutError:
                await ctx.send('Alright its a no!')
                return
            try:
                await warning.delete()
                await msg.delete()
            except:
                pass
            if msg.content.lower() == 'n':
                return
            role= await ctx.guild.create_role(name= 'Muted', reason= f'{ctx.author.name}#{ctx.author.discriminator}')
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, muterole_id) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET muterole_id = EXCLUDED.muterole_id', ctx.guild.id, role.id)
        await self.embeder(ctx, 'Mute role', role.mention)
    
    # I will kick those who pass warning threshold
    @commands.command(
        help="Bot automatically kick someone when he pass kickat threshold.",
        description="Can't be less then 3, pass 0 to disable"
    )
    @commands.has_guild_permissions(administrator= True)
    async def kickat(self, ctx, *, kickat: int= 0):
        if kickat <= 0:
            kickat = 0
        if kickat < 3 or kickat > 1000:
            return await ctx.send(":x: Kick at value can't be less then 3 or more than 1000.")
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, kickat) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET kickat = EXCLUDED.kickat', ctx.guild.id, kickat)
        await self.embeder(ctx, "Kick At", kickat if kickat else 'Disabled')

    # I will ban those who pass warning threshold
    @commands.command(
        help="Bot automatically ban someone when he pass kickat threshold.",
        description="Can't be less then 4, pass 0 to disable"
    )
    @commands.has_guild_permissions(administrator= True)
    async def banat(self, ctx, *, banat: int= 0):
        if banat <= 0:
            banat = 0
        if banat < 3 or banat > 1000:
            return await ctx.send(":x: Kick at value can't be less then 3 or more than 1000.")
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, banat) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET banat = EXCLUDED.banat', ctx.guild.id, banat)
        await self.embeder(ctx, "Kick At", banat if banat else 'Disabled')

    # Greet command
    @commands.group(aliases= ['welcome'], invoke_without_command= True, help= 'Sends a sample of greet embed.')
    @commands.has_guild_permissions(administrator= True)
    async def greet(self, ctx, member: discord.Member= None):
        member= member or ctx.author
        await self.send_greet(member, ctx.channel)
    @greet.command(aliases= ['channel'],
        help= 'Set a greet channel',
        description= 'This will use the default greet message, use `greetmsg` command to set a custom message.')
    @commands.has_guild_permissions(administrator= True)
    async def ch(self, ctx, channel: discord.TextChannel= None):
        if channel:
            chid= channel.id
        else:
            chid= None
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, greetch) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET greetch = EXCLUDED.greetch', ctx.guild.id, chid)
        await self.embeder(ctx, "Greet channel", f'<#{chid}>' if chid else 'None')
    @greet.command(aliases= ['msg'],
        help= 'Set a message to be send to `leave channel`. If no arg was passed the bot will use default one.\n\
You can use several tags in message {usermention}, {userid}, {server}, {username}, {joinedat}, {createdat}.')
    @commands.has_guild_permissions(administrator= True)
    async def message(self, ctx, *, message= None):
        if len(message) > 1500:
            await ctx.send('To long text not excepted more than `1500`.')
            return
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, greetmsg) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET greetmsg = EXCLUDED.greetmsg', ctx.guild.id, message)
        await self.embeder(ctx, "Greet message", f'The given message' if message else 'The default one.')

    # Chech out the current Guild settings.
    @commands.command(aliases= ['sets'],
        help="This will display the current server settings",
        description="This command is just for confirmation, tho recommanded to use it in private channels."
    )
    @commands.has_guild_permissions(manage_guild= True, manage_permissions= True, manage_roles= True, view_audit_log= True)
    async def settings(self, ctx):
        settings= await self.client.db.fetchrow('SELECT * FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        if not settings:
            return await ctx.send('No settings are set till now.')
        embed= discord.Embed(title= 'Current Guild Settings', Timestamp= datetime.utcnow(), color= discord.Color.blurple())
        embed.set_author(name= ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.add_field(name= 'Start role', value= '<@&{}>'.format(settings['startrole_id'])) if settings['startrole_id'] else None
        embed.add_field(name= 'Mute role', value= '<@&{}>'.format(settings['muterole_id'])) if settings['muterole_id'] else None
        embed.add_field(name= 'Mod role', value= '<@&{}>'.format(settings['modrole_id']), inline= False) if settings['modrole_id'] else None
        embed.add_field(name= 'Kick At', value= settings['kickat']) if settings['kickat'] else None
        embed.add_field(name= 'Ban At', value= settings['banat']) if settings['banat'] else None
        embed.add_field(name= 'Greet channel', value= f'<#{settings["greetch"]}>') if settings["greetch"] else None
        if not embed.fields:
            await ctx.send('"Nothing to see here"')
            return
        await ctx.send(embed= embed)

    # Disable command
    @commands.command(name= 'disable', help= 'Disable a command')
    @commands.has_guild_permissions(manage_guild= True)
    async def _disable(self, ctx, *commands):
        if len(commands)> 50:
            return await ctx.send('Please not more than 50 commands at a time.')
        discmds= await self.client.db.fetchval('SELECT discmds FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        discmds= discmds or []
        newdiscmds= []
        for cmd in commands:
            cmd= self.client.get_command(cmd)
            if not cmd:
                continue
            elif cmd.cog.qualified_name == 'Settings' or not cmd.cog.qualified_name:
                continue
            elif cmd.name in discmds:
                continue
            newdiscmds.append(cmd.name)
        discmds+= newdiscmds
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, discmds) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET discmds = EXCLUDED.discmds', ctx.guild.id, discmds)
        blackch= self.client.cache.get(ctx.guild.id, {"prefix":'.', "blackch":[]})
        prefix, blackch= blackch['prefix'], blackch['blackch']
        self.client.cache.update({ctx.guild.id:{"prefix":prefix,"discmds":discmds, "blackch":blackch}})
        await self.embeder(ctx, '**Commands**'+'\n```'+', '.join(newdiscmds)+'```\n', '`disabled`')

    # Enable command
    @commands.command(name= 'enable', help= 'Enable a disabled command')
    @commands.has_guild_permissions(manage_guild= True)
    async def _enable(self, ctx, *commands):
        if len(commands)> 50:
            return await ctx.send('Please not more than 50 commands at a time.')
        discmds= await self.client.db.fetchval('SELECT discmds FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        discmds= discmds or []
        cmds_to_enable= []
        for cmd in commands:
            cmd= self.client.get_command(cmd)
            if not cmd:
                continue
            elif cmd.cog.qualified_name == 'Settings' or not cmd.cog.qualified_name:
                continue
            elif not cmd.name in discmds:
                continue
            cmds_to_enable.append(cmd.name)
        discmds= [cmd for cmd in discmds if not cmd in cmds_to_enable]
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, discmds) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET discmds = EXCLUDED.discmds', ctx.guild.id, discmds)
        blackch= self.client.cache.get(ctx.guild.id, {"prefix":'.', "blackch":[]})
        prefix, blackch= blackch['prefix'], blackch['blackch']
        self.client.cache.update({ctx.guild.id:{"prefix":prefix,"discmds":discmds, "blackch":blackch}})
        await self.embeder(ctx, '**Commands**'+'\n```'+', '.join(cmds_to_enable)+'```\n', '`enabled`')

    # set Ranks
    @commands.group(aliases= ['joinroles'],
        help= 'With this command you can set the role that can be joined by members with `rank add` command.', invoke_without_command=True)
    @commands.bot_has_guild_permissions(manage_roles= True)
    async def ranks(self, ctx):
        ranks= await self.client.db.fetchval('SELECT ranks FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        if not ranks:
            return await ctx.send('There are no ranks setuped in the server, start adding them with `ranks add` command')
        pag= commands.Paginator(prefix='', suffix= '', linesep= ' • ')
        for rank in ranks:
            pag.add_line(f'<@&{rank}>')
        for page in pag.pages:
            embed= discord.Embed(title= f'{ctx.guild}\'s Ranks list',
                description= page,
                color= ctx.me.color)
            await ctx.send(embed= embed)
    @ranks.command(aliases= ['new', 'create'], help= 'Add a rank that members can join, these are just joinable role with `rank` command')
    @commands.has_guild_permissions(manage_guild= True, manage_roles= True)
    async def add(self, ctx, role: discord.Role):
        ranks= await self.client.db.fetchval('SELECT ranks FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        if ranks:
            if len(ranks) >= 50:
                return await ctx.send('Limit of 50 ranks already reached.')
        if role.position >= ctx.me.top_role.position:
            return await ctx.send('That role is above me, move the role below my top role so that I can add roles to members.')
        if not ranks:
            ranks= [role.id]
        else:
            if role.id in ranks:
                return await ctx.send('That role is already a rank, lets not do it.')
            ranks.append(role.id)
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, ranks) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET ranks = EXCLUDED.ranks', ctx.guild.id, ranks)
        await self.embeder(ctx, 'Added rank', role.mention)
    @ranks.command(aliases= ['delete'], help= 'Remove a rank that members can join, these are just joinable role with `rank` command')
    @commands.has_guild_permissions(manage_guild= True, manage_roles= True)
    async def remove(self, ctx, role: discord.Role):
        ranks= await self.client.db.fetchval('SELECT ranks FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        try:
            ranks.remove(role.id)
        except:
            return await ctx.send('That role was never a rank. Let\'s not do it.')
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, ranks) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET ranks = EXCLUDED.ranks', ctx.guild.id, ranks)
        await self.embeder(ctx, 'Removed rank', role.mention)
    @ranks.command(aliases= ['give'], help= 'Join a rank!')
    async def join(self,ctx, role: discord.Role):
        ranks= await self.client.db.fetchval('SELECT ranks FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        if not role.id in ranks:
            await ctx.send("That rank doesn't exist in this server. Use `ranks` command to see list of ranks")
            return
        if role in ctx.author.roles:
            await ctx.send('You already have that role!')
        embed= discord.Embed(
            title= 'Rank added',
            description= f'{role.mention} Was Added!',
            color= ctx.me.color
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        try:
            await ctx.author.add_roles(discord.Object(role.id), reason= f'Joined a rank {role.name}')
            await ctx.send(embed= embed)
        except: return await ctx.send('I m not able to add the role, push the rank below my top role.')
    @ranks.command(aliases= ['takeback'], help= 'Drop a rank!')
    async def drop(self,ctx, role: discord.Role):
        ranks= await self.client.db.fetchval('SELECT ranks FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        if not str(role.id) in ranks:
            await ctx.send("That rank doesn't exist in this server. Use `ranks` command to see list of ranks")
            return
        if not role in ctx.author.roles:
            await ctx.send('You dont have that role already!')
        embed= discord.Embed(
            title= 'Rank removed',
            description= f'{role.mention} Was Taken!',
            color= ctx.me.color
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        try:
            await ctx.author.remove_roles(discord.Object(role.id), reason= f'Joined a rank {role.name}')
            await ctx.send(embed= embed)
        except: return await ctx.send('I was unable to remove the role, push the rank below my top role.')

    @commands.command(aliases= ['nolisten'], help= 'This will stop the bot to listen commands on the current or mentioned channels')
    @commands.has_guild_permissions(manage_channels= True)
    async def blacklist(self, ctx, channel: discord.TextChannel= None):
        channel= channel or ctx.channel
        blackch= await self.client.db.fetchval('SELECT blackch FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        if blackch:
            if len(blackch) >= 50:
                return await ctx.send('The limit of 50 blacklisted channels has crossed.')
        else:
            blackch= []
        if channel.id in blackch:
            return await ctx.send(f'{channel.mention} is already blacklisted.')
        else:
            blackch.append(channel.id)
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, blackch) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET blackch = EXCLUDED.blackch', ctx.guild.id, blackch)
        discmds= self.client.cache.get(ctx.guild.id, {"prefix":'.', "discmds":[]})
        prefix, discmds= discmds['prefix'],discmds['discmds']
        self.client.cache.update({ctx.guild.id:{"prefix":prefix,"discmds":discmds, "blackch":blackch}})
        await self.embeder(ctx, f'Channel {channel.mention}', '`blacklisted`')

    @commands.command(aliases= ['plslisten'], help= 'This will stop the bot to stop listen commands on the current or mentioned channels')
    @commands.has_guild_permissions(manage_channels= True)
    async def whitelist(self, ctx, channel: discord.TextChannel= None):
        channel= channel or ctx.channel
        blackch= await self.client.db.fetchval('SELECT blackch FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        if not blackch:
            blackch= []
        if not channel.id in blackch:
            return await ctx.send(f'{channel.mention} is already whitelisted.')
        else:
            blackch.remove(channel.id)
        await self.client.db.execute('INSERT INTO guildsettings(guild_id, blackch) VALUES ($1, $2) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
            DO UPDATE SET blackch = EXCLUDED.blackch', ctx.guild.id, blackch)
        discmds= self.client.cache.get(ctx.guild.id, {"prefix":'.', "discmds":[]})
        prefix, discmds= discmds['prefix'],discmds['discmds']
        self.client.cache.update({ctx.guild.id:{"prefix":prefix,"discmds":discmds, "blackch":blackch}})
        await self.embeder(ctx, f'Channel {channel.mention}', '`Whitelisted`')

    # Command to reset all the bot data in the current guild
    @commands.command(aliases= ['removedata'], help= 'DELETE every guild setting that you set. You NEED TO BE guild owner to use this.')
    @is_guild_owner()
    async def factoryReset(self, ctx):
        await ctx.send('This will delete all the bot settings in this server. Tho this won\'t remove the backlisted channels.\nYou sure? (y/n)')
        def check(m):
            return ctx.author.id== m.author.id and ctx.channel.id== m.channel.id and m.content.lower() in ['y','n']
        try:
            msg= await self.client.wait_for('message', check= check, timeout= 30.0)
        except:
            await ctx.send('Phew')
        if msg.content.lower() == 'y':
            await self.client.db.execute('DELETE FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
            await ctx.send('Damn all settings are now gone.')

    # Bot Owner Commands ----------------
    @commands.command(aliases= ['botban'], hidden= True)
    @commands.is_owner()
    async def bban(self, ctx, *, param: Union[discord.User, discord.Guild]):
        backlists=  open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')))
        backlisted= json.load(backlists)
        backlists.close()
        if isinstance(param, discord.User):
            backlisted['users'].append(param.id)
        if isinstance(param, discord.Guild):
            backlisted['guilds'].append(param.id)
        backlists= open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')), 'w')
        json.dump(backlisted, backlists)
        backlists.close()
        listners= self.client.get_cog('Listners')
        listners.blacklisted= backlisted
        await ctx.send(f'Bot banned `{param.id}`')

    @commands.command(aliases= ['botunban'], hidden= True)
    @commands.is_owner()
    async def bunban(self, ctx, *, param: Union[discord.User, discord.Guild]):
        backlists=  open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')))
        backlisted= json.load(backlists)
        backlists.close()
        if isinstance(param, discord.User):
            backlisted['users'].remove(param.id)
        if isinstance(param, discord.Guild):
            backlisted['guilds'].remove(param.id)
        backlists= open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')), 'w')
        json.dump(backlisted, backlists)
        backlists.close()
        listners= self.client.get_cog('Listners')
        listners.blacklisted= backlisted
        await ctx.send(f'Bot unbanned `{param.id}`')

    @commands.command(
        name='reload', description="Reload all/one of the bots cogs!",
        hidden= True
    )
    @commands.is_owner()
    async def reload(self, ctx, ext: str= None):
        cogs= [cog[:-3] for cog in os.listdir(os.path.normpath(os.path.abspath(__file__)+'/'+'..')) if cog.endswith('.py')]
        ext= discord.utils.find(lambda cog: ext.lower() in cog, cogs) if ext else None
        if not ext or not ext.lower() in cogs:
            msg= await ctx.send('Reloading all cogs.')
            for cog in cogs:
                try:
                    self.client.unload_extension(f'cogs.{cog}')
                except:
                    pass
                finally:
                    self.client.load_extension(f'cogs.{cog}')
        else:
            msg= await ctx.send(f'Reloading `{ext.capitalize()}`')
            try:
                self.client.unload_extension(f'cogs.{ext}')
            except:
                pass
            finally:
                self.client.load_extension(f'cogs.{ext}')
        await msg.edit(content= 'Done 👌')

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    @commands.command(pass_context=True, hidden=True, name='py')
    @commands.is_owner()
    async def _eval(self, ctx, *, body: str):
        env = {
            'bot': self.client,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = StringIO()

        to_compile = f'async def func():\n{indent(body, "    ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            value= value.replace('/cloudclusters/', '[C*nsor*d]')
            msg= await ctx.send(f'```py\n{value}{format_exc().replace("/cloudclusters/", "[C*nsor*d]")}\n```')
            try:
                await msg.add_reaction('🗑')
                try:
                    def check(r, u):
                        return r.emoji== '🗑' and msg.id== r.message.id and u.id == self.client.owner_id
                    await self.client.wait_for('reaction_add', check= check, timeout= 30)
                    await msg.delete()
                except: return
            except: pass
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

def setup(client):
    client.add_cog(Settings(client))
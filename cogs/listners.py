import asyncio
from io import BytesIO
from typing import Union
import discord, json, os
from discord.ext import commands
from datetime import datetime
from time import time
from colorama import Style, Fore
from random import choice
from wavelink import ZeroConnectedNodes
from UFO_Bot import Ufo_bot
from traceback import format_exception

class Listners(commands.Cog):
    def __init__(self, client):
        self.client: Ufo_bot= client
        self.permsCheck= ['change_nickname', 'ban_members', 'kick_members', 'manage_emojis', 'manage_roles', 'manage_nicknames',
            'manage_messages', 'manage_channels', 'manage_guild', 'mention_everyone', 'create_instant_invite', 'administrator']
        self.blacklisted= json.load(open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..'))))

    print('Listners.py has been loaded\n-----------------------------------')

    # Files a case for modlog and resets when Cases Go over 500
    async def file_case(self, guild, action, memberid,reason= None):
        case= {
            "reason": reason,
            "action": action,
            "member": memberid,
        }
        async with self.client.db.acquire() as con:
            await con.set_type_codec(
                'jsonb',
                encoder=json.dumps,
                decoder=json.loads,
                schema='pg_catalog'
            )
            casecount= await con.fetchval(f"UPDATE guildsettings SET logs = logs || ARRAY[$1::jsonb] WHERE (guild_id = $2) RETURNING ARRAY_LENGTH(logs::jsonb[], 1)",
                case, guild.id)
            if casecount<= 500:
                return casecount
            else:
                await con.execute(f"UPDATE guildsettings SET (logs = ARRAY[$1::json]) WHERE guild_id = {guild.id}", case)
                return 1

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author.id in self.client.commandusers.keys():
            if self.client.commandusers[message.author.id][0]:
                return
        if message.author.id in self.blacklisted['users']:
            return
        if message.guild != None and message.guild.id in self.blacklisted['guilds']:
            return
        await self.client.process_commands(message)
        if message.content.strip() in ('<@!822448143508963338>', '<@822448143508963338>'):
            prefix = await self.client.get_prefix(message)
            await message.channel.send(f"My prefix at this guild is `{prefix[0]}`. Alternatively u can mention me at the start of ur message if u dont remember the prefix.")
            return
        # AUTOMODERATION COMING SOON...

    # Gets the modlog channel for a critatira of modlogs.
    '''
    This bot supports logging for:
        - ban                   - unban                 - kick (if kicked by bot.)
        - guild-updates         - channel-updates       - channel-overwrites
        - roles                 - message-edit          - bulk-delete
        - message-pin           - warns
    '''
    async def check_logging(self, checkfor, guild):
        ch_id= await self.client.db.fetchval(f"SELECT logch FROM guildsettings WHERE guild_id = {guild.id} AND '{checkfor}' = ANY(logging)")
        if not ch_id: return False
        channel= guild.get_channel(ch_id)
        if not channel: return False
        else: return channel

    # Sends a message to a channel when a member joins and also give the startrole
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id in self.blacklisted['guilds']: return
        raw= await self.client.db.fetchrow('SELECT greetmsg, greetch FROM guildsettings WHERE guild_id = $1', member.guild.id)
        if not raw: return
        if not raw['greetch']: return
        channel= member.guild.get_channel(raw['greetch'])
        desc= raw['greetmsg'] or 'Welcome {usermention} to **{server}**. Hope you have a great stay here. Pls read the server rules and follow them.'
        desc= desc.format(
            usermention= member.mention,
            server= str(member.guild),
            userid= member.id,
            username= str(member),
            joinedat= int(member.joined_at.timestamp()),
            createdat= int(discord.Object(member.id).created_at.timestamp())
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
        startrole= await self.client.db.fetchrow('SELECT startrole_id, muterole_id FROM guildsettings WHERE guild_id = $1', member.guild.id)
        muterole, startrole= startrole['muterole_id'], startrole['startrole_id']
        guild_mutes= await self.client.db.fetchval('SELECT mutedmems FROM guildsettings WHERE guild_id = $1', member.guild.id)
        if not guild_mutes: return
        if member.id in guild_mutes:
            await member.add_roles(discord.Object(muterole), discord.Object(startrole), reason= 'This user was muted before leaving.', atomic= True)
        else:
            await member.add_roles(discord.Object(startrole), atomic= True)

    # Snipe the message and tranfer to db.
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or message.embeds or len(message.content)> 500 or not message.guild:
            return
        await self.client.db.execute('INSERT INTO snipes VALUES ($1, $2, $3, $4) ON CONFLICT (channel_id) DO UPDATE SET\
            timestamp = EXCLUDED.timestamp, message_content = EXCLUDED.message_content, user_id = EXCLUDED.user_id',
            message.channel.id, int(time()), message.content, message.author.id)

    # Handles all the errors bot faces.
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        try:
            self.client.commandused+=1
            if ctx.author.id in self.client.commandusers.keys():
                self.client.commandusers.update({ctx.author.id: [False, self.client.commandusers[ctx.author.id][1]]})
        except: pass
        if isinstance(error, discord.Forbidden):
            return await ctx.send(f'I was forbidden by discord-\n**{error.code}**: {error.response}')
        elif isinstance(error, commands.MissingRole):
            return
        elif isinstance(error, commands.MissingPermissions):
            return
        elif isinstance(error, commands.MissingAnyRole):
            return
        elif isinstance(error, commands.CommandOnCooldown):
            embed= discord.Embed(
                title= choice(['Cooldown', 'Chill', 'Relax', 'Not now', 'Spam takes ram']),
                description= f'**{ctx.command}** is in cooldown, retry after {round(error.retry_after, 2)} secs.'
            )
        elif isinstance(error, commands.BadUnionArgument):
            embed= discord.Embed(
                title= 'Bad argument',
                description= f'The argument u passed failed to parse'
            )
        elif isinstance(error, commands.CheckFailure):
            return
        elif isinstance(error, commands.NoPrivateMessage):
            embed= discord.Embed(
                title= 'Guild Only',
                description= f'**{ctx.command}** is a guild only command, doesn\'t work on DMs.'
            )
        elif isinstance(error, commands.BadArgument):
            embed= discord.Embed(
                title= 'Bad Argument',
                description= str(error)
            )
            await ctx.send_help(ctx.command)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed= discord.Embed(
                title= 'Missing Argument',
                description= f'{error.param} is the required argument that is missing.'
            )
            await ctx.send_help(ctx.command)
        elif isinstance(error, commands.MemberNotFound):
            embed= discord.Embed(
                title= 'Member Not found',
                description= f'"{error.argument}" Is not a member.'
            )
        elif isinstance(error, commands.UserNotFound):
            embed= discord.Embed(
                title= 'User Not found',
                description= f'"{error.argument}" Is not a User.'
            )
        elif isinstance(error, commands.ChannelNotFound):
            embed= discord.Embed(
                title= 'Channel not found',
                description= f'Channel not found, or if it exists it\'s not visible to me.'
            )
        elif isinstance(error, commands.MessageNotFound):
            embed= discord.Embed(
                title= 'Message not found',
                description= f'Can\'t find any such message.'
            )
        elif isinstance(error, commands.RoleNotFound):
            embed= discord.Embed(
                title= 'Role not found',
                description= f'"{error.argument}" can\'t find any such role.'
            )
        elif isinstance(error, commands.BotMissingPermissions):
            embed= discord.Embed(
                title= 'Not enough perms',
                description= f'"{error.missing_perms}" is the required permission for this command to run.'
            )
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.UserNotFound):
            embed= discord.Embed(
                title= 'User Not found',
                description= f'"{error.argument}" Is not a user.'
            )
        elif isinstance(error, commands.EmojiNotFound):
            embed= discord.Embed(
                title= 'User/Emoji Not found',
                description= f'"{error.argument}" Is not a user/emoji.'
            )
        elif isinstance(error, commands.CommandInvokeError):
            error= error.original
            if isinstance(error, ZeroConnectedNodes):
                await ctx.send('Music command not working right now, Nodes disconnected.')
            elif isinstance(error, discord.Forbidden):
                await ctx.send('I didn\'t had enough permission to run the command.')
            elif isinstance(error, discord.HTTPException):
                await ctx.send('Sorry I tried to send something that was too long i guess...')
            else:
                embed= discord.Embed(
                    title= 'A wild error occured.',
                    description= 'The error was auto-reported in the support server.',
                    timestamp= datetime.utcnow()
                )
                await ctx.send(embed= embed)
                error_ch: discord.TextChannel= self.client.get_guild(822449600509509712).get_channel(862925533498572810)
                embed.add_field(name= 'Guild id', value= ctx.guild.id)
                embed.add_field(name= 'Channel id', value= ctx.channel.id)
                embed.add_field(name= 'Commands used', value= str(ctx.command))
                trace= f'```py\n{"".join(format_exception(etype=type(error), value=error, tb=error.__traceback__))}\n```'
                if len(trace) >= 2000:
                    store= BytesIO(trace.encode('utf-8'))
                    await error_ch.send('<@!577471505265590273>' if ctx.guild.id != 822449600509509712 else None, embed= embed,
                        file= discord.File(store, 'Traceback.py'), allowed_mentions= discord.AllowedMentions(users= True, everyone= False, roles= False))
                else:
                    embed.add_field(name= 'Traceback', value= trace)
                    await error_ch.send('<@!577471505265590273>' if ctx.guild.id != 822449600509509712 else None, embed= embed,
                        allowed_mentions= discord.AllowedMentions(users= True, everyone= False, roles= False))
                print(f'{Fore.RED}-==================================================================-{Style.RESET_ALL}')
                raise error
        embed.set_author(name= f'{ctx.author}', icon_url= ctx.author.avatar_url)
        self.client.errorcount+= 1
        embed.set_footer(icon_url= 'https://data.whicdn.com/images/287267204/original.gif',
            text= f'Errors this session: {self.client.errorcount}')
        embed.color= discord.Color.dark_theme()
        await ctx.send(embed= embed, delete_after= 10)

    # Sends a modlogs on ban
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: Union[discord.User, discord.Member]):
        if guild.id in self.blacklisted['guilds']: return
        channel= await self.check_logging('ban', guild)
        if not channel: return
        await asyncio.sleep(1) # Waiting for audit Logs to cache
        bannedby= 'me'
        try:
            async for audit in guild.audit_logs(limit= 15, action= discord.AuditLogAction.ban):
                if user.id== audit.target.id:
                    reason= audit.reason
                    bannedby= audit.user if audit.user.id != guild.me.id else 'me'
                    break
        except:
            await channel.send('`I have no permissions to see bans or audits. Give me auditlogs and ban members premission to let me log bans.`')
            return
        casecount= await self.file_case(guild, 'ban', user.id, reason)
        embed= discord.Embed(
            title= 'Banned!',
            description= f'**{user}** was banned by __{bannedby}__.',
            color= discord.Color.red()
        )
        embed.set_author(name= f'Cases {casecount}')
        embed.set_thumbnail(url= user.avatar_url)
        embed.add_field(name= 'Reason', value= reason or 'No reason given.')
        await channel.send(embed= embed)

    # Sends a modlog on unban
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        if guild.id in self.blacklisted['guilds']: return
        if user.bot: return
        channel= await self.check_logging('unban', guild)
        if not channel: return
        await asyncio.sleep(1) # Look up
        reason= None
        try:
            async for audit in guild.audit_logs(limit= 15, action= discord.AuditLogAction.unban):
                if user.id== audit.target.id:
                    reason= audit.reason
                    bannedBy= audit.user if audit.user.id != guild.me.id else 'me'
                    break
        except:
            await channel.send('`I have no permissions to see bans or audits. Give me auditlogs and ban members premission to let me log unbans.`')
            return
        casecount= await self.file_case(guild, 'unban', user.id, reason or 'No reason given.')
        embed= discord.Embed(
            title= 'Unbanned!',
            description= f'**{user}** was unbanned by __{bannedBy}__',
            color= discord.Color.green()
        )
        embed.set_author(name= f'Cases {casecount}')
        embed.set_thumbnail(url= user.avatar_url)
        embed.add_field(name= 'Reason', value= reason or 'No reason given.')
        await channel.send(embed= embed)

    # Sends a modlog on guild channel update/create/delete.
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if after.guild.id in self.blacklisted['guilds']: return
        if before.position != after.position: return
        channel= await self.check_logging('channel-updates', after.guild)
        if channel:
            embed= discord.Embed(
                title= 'Channel Updated!',
                description= f'{after.mention} was updated.',
                color= discord.Color.blurple()
            )
            if before.name != after.name:
                embed.add_field(name= 'Name before', value= before.name, inline= False)
                embed.add_field(name= 'Name after', value= after.name, inline= False)
            if before.permissions_synced != after.permissions_synced:
                embed.add_field(name= f'Premission was{"nt" if after.premissions_synced else ""} synced before', value= f'Now they are {"not" if before.premissions_synced else ""} synced.')
            if before.category != after.category:
                embed.add_field(name= 'Category before', value= before.category.name, inline= False)
                embed.add_field(name= 'Category after', value= after.category.name, inline= False)
            if before.position != after.position:
                embed.add_field(name= 'Position before', value= str(before.position))
                embed.add_field(name= 'Position after', value= str(after.position))
            if embed.fields:
                await channel.send(embed= embed)
        channel= await self.check_logging('channel-overwrites', after.guild)
        if not channel or before.overwrites == after.overwrites: return
        def permstoSTR(perms: discord.PermissionOverwrite):
            print(perms)
            perms: dict= perms._values
            readableperms= []
            permcheck= ['view_channel', 'read_message', 'connect', 'send_messages', 'external_emojies', 'embed_links', 'manage_messages',
                'manage_channels', 'manages_permissions', 'manage_webhooks', 'mention_everyone', 'add_reactions', 'create_instant_invite']
            for perm in permcheck:
                perma= perms.get(perm, None)
                value= ''
                if perma == None:
                    value+= '<:slash:857492371267387422>'
                else:
                    value+= '<:check:857494064294264862>' if perma else '<:uncheck:857494289415798784>'
                value+= ' '+ perm.replace('_', ' ').capitalize()
                readableperms.append(value)
            return '\n'.join(readableperms)
        entities= '**, **'.join(list(map(str, after.overwrites.keys())))
        desc= f'{after.mention} was overwritten for entities **{entities}**'
        if len(desc)> 500: desc= desc[0:500] + '...'
        embed= discord.Embed(
            ttile= 'Channel overwritten!',
            description= desc
        )
        embed.set_footer(text= 'Only first 6 shown.')
        overwrites= after.overwrites.keys() if len(after.overwrites.keys())<= 6 else after.overwrites.keys()[0:6]
        for overwrite in overwrites:
            embed.add_field(name= str(overwrite), value= permstoSTR(after.overwrites[overwrite]))
        await channel.send(embed= embed)

    # Sends a modlog on guild channel create.
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if channel.guild.id in self.blacklisted['guilds']: return
        log_ch= await self.check_logging('channel-updates', channel.guild)
        embed= discord.Embed(title= 'Channel Created!', description= f'Channel {channel.mention} was created at <t:{int(channel.created_at.timestamp(0))}:F> UTC')
        embed.add_field(name= 'Channel Category.', value= channel.category.name)
        await log_ch.send(embed= embed)

    # Sends a modlog on guild channel create.
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if channel.guild.id in self.blacklisted['guilds']: return
        log_ch= await self.check_logging('channel-updates', channel.guild)
        embed= discord.Embed(title= 'Channel Deleted!', description= f'Channel {channel.mention} was deleted at <t:{int(channel.created_at.timestamp(0))}:F> UTC')
        embed.add_field(name= 'Channel Category.', value= channel.category.name)
        await log_ch.send(embed= embed)

    # Send a modlog on guild update
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if after.id in self.blacklisted['guilds']: return
        channel= await self.check_logging('guild-updates', after)
        if not channel: return
        if before.name != after.name:
            delta= ('Name Changed', before.name, after.name)
        elif before.afk_channel != after.afk_channel:
            delta= ('AFK Channel Changed!', before.afk_channel, after.afk_channel)
        else:
            return
        embed= discord.Embed(
            title= 'GUILD UPDATED!',
            description= delta[0],
            color= discord.Color.blurple()
        )
        embed.add_field(name= 'Before', value= f'{delta[1]}', inline= False)
        embed.add_field(name= 'After', value= f'{delta[2]}', inline= False)
        await channel.send(embed= embed)

    # Send a modlog on bulk delete
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if messages[0].guild.id in self.blacklisted['guilds']: return
        channel= await self.check_logging('bulk-delete', messages[0].guild)
        if not channel: return
        embed= discord.Embed(title= 'Bulk Delete!',
            description= f'A total of {len(messages)} were deleted in {messages[0].channel.mention}',
            color= discord.Color.blurple())
        await channel.send(embed= embed)

    def permsToStr(self, role: discord.Role):
        permissions= role.permissions
        value= []
        for perm in self.permsCheck:
            text= '<:check:857494064294264862>' if getattr(permissions, perm) else '<:uncheck:857494289415798784>'
            text+= ' '+ perm.replace('_', ' ').capitalize()
            value.append(text)
        return '\n'.join(value)

    # Send a modlog on roles Update/ create/ delete. --- All three below.
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        if role.guild.id in self.blacklisted['guilds']: return
        if role.is_bot_managed(): return
        channel= await self.check_logging('roles', role.guild)
        if not channel: return
        embed= discord.Embed(
            title= 'Role Created!',
            description= f'{role.mention} was created.',
            color= discord.Color.blurple() if role.color == discord.Color.default() else role.color
        )
        embed.add_field(name= 'Permissions', value= self.permsToStr(role), inline= False)
        await channel.send(embed= embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if after.guild.id in self.blacklisted['guilds']: return
        channel= await self.check_logging('roles', after.guild)
        if not channel: return
        embed= discord.Embed(
            title= 'Role Updated!',
            description= f'{after.mention} was updated.',
            color= discord.Color.blurple() if after.color == discord.Color.default() else after.color
        )
        if before.permissions != after.permissions:
            embed.add_field(name= 'Permissions before', value= self.permsToStr(before))
            embed.add_field(name= 'Permissions now', value= self.permsToStr(after))
        if before.color != after.color:
            embed.add_field(name= 'Color changed', value= f'{before.color.to_rgb()} > {after.color.to_rgb()}')
        if before.mentionable != after.mentionable:
            embed.add_field(name= 'Mentionablilty', value= f'The role was{"nt" if after.mentionable else ""} mentionable before. Now, {"it is" if after.mentionable else "it isnt"}.')
        if before.hoist != after.hoist:
            embed.add_field(name= 'Hoist changed', value= f'The role was{"nt" if after.hoist else ""} hoisted before. Now, it is{"" if after.hoist else "nt"}.')
        if embed.fields:
            await channel.send(embed= embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        if role.guild.id in self.blacklisted['guilds']: return
        if role.is_bot_managed(): return
        channel= await self.check_logging('roles', role.guild)
        if not channel: return
        embed= discord.Embed(
            title= 'Role deleted!',
            description= f'**@{role.name}** was deleted.',
            color= discord.Color.purple()
        )
        await channel.send(embed= embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.guild.id in self.blacklisted['guilds']: return
        if after.author.bot or after.content == before.content: return
        channel= await self.check_logging('message-edit', after.guild)
        if not channel: return
        embed= discord.Embed(
            title= 'Message editted!',
            color= discord.Color.blurple(),
            description= f'[\`\`Jump``]({after.jump_url})'
        )
        embed.add_field(name= 'Before', value= before.content[:2000], inline= False)
        embed.add_field(name= 'After', value= after.content[0:2000], inline= False)
        embed.set_footer(text= after.author, icon_url= after.author.avatar_url)
        await channel.send(embed= embed)

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, PINchannel: discord.abc.GuildChannel, last_pin):
        if PINchannel.guild.id in self.blacklisted['guilds']: return
        channel= await self.check_logging('message-pin', PINchannel.guild)
        if not channel: return
        embed= discord.Embed(
            title= 'Message pinned!',
            description= f'Message pinned in {PINchannel.mention}',
            timestamp= last_pin,
            color= discord.Color.blurple() if PINchannel.guild.me.color == discord.Color.default() else PINchannel.guild.me.color
        )
        embed.set_footer(text= 'Pinned message was sent ')
        await channel.send(embed= embed)

def setup(client):
    client.add_cog(Listners(client))
import datetime, discord, re
from discord.ext import commands, tasks
from typing import Union
from discord.ext.commands.cooldowns import BucketType
from time import time
from asyncio import sleep
from json import dumps, loads
from UFO_Bot import Ufo_bot

async def _single_delete_strategy(messages):
    for m in messages:
        await m.delete()

class Moderation(commands.Cog):
    def __init__(self, client):
        self.client: Ufo_bot= client
    
    print("Moderation.py has been loaded\n-----------------------------------")

    @commands.Cog.listener()
    async def on_ready(self):
        await sleep(10)
        self.mutetask= self.mutehandler.start()
        print('Started Mute Task in Moderation.py')
        await sleep(10)
        self.tempbanstask= self.tempban_handler.start()
        print('Started tempBan Task in Moderation.py')

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

    # Custom Check if user can moderate with the power of modrole
    async def has_modrole(ctx):
        modrole= await ctx.bot.db.fetchval('SELECT modrole_id from guildsettings WHERE guild_id = $1', ctx.guild.id)
        if not modrole:
            return False
        try:
            return await commands.has_role(int(modrole)).predicate(ctx)
        except:
            return False

    async def brokencl(self, ctx, count, check):
        d= datetime.timedelta(days= 14)
        dt= datetime.datetime.utcnow() - d
        deleted= 0
        if count<=0:
            raise commands.BadArgument(message= 'Count should be a positive number.')
        count+= 1
        deleted+= len(await ctx.channel.purge(limit= count, after= dt, check= check))
        return deleted

    async def brokencltill(self, ctx, check, msg):
        dt= msg.created_at
        deleted= 0
        for i in range(1, 11):
            deld= deleted
            deleted+= len(await ctx.channel.purge(limit= 100, after= dt, check= check))
            if deld== deleted:
                #if msg.created_at.timestamp() > discord.Object(ctx.channel.last_message_id).created_at.timestamp():
                break
        return deleted

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
                encoder= dumps,
                decoder= loads,
                schema='pg_catalog'
            )
            casecount= await con.fetchval(f"UPDATE guildsettings SET logs = logs || ARRAY[$1::jsonb] WHERE (guild_id = $2) RETURNING ARRAY_LENGTH(logs::jsonb[], 1)",
                case, guild.id)
            if casecount<= 500:
                return casecount
            else:
                await con.execute(f"UPDATE guildsettings SET (logs = ARRAY[$1::json]) WHERE guild_id = {guild.id}", case)
                return 1

    # Convert time.
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

    # Mute handler.
    @tasks.loop(seconds= 30)
    async def mutehandler(self):
        for muteEntry in self.client.mutemem:
            if muteEntry[1] > datetime.datetime.utcnow().timestamp():
                try:
                    muterole= await self.client.db.fetchval('SELECT muterole_id FROM guildsettings WHERE guild_id = $1', muteEntry[0].guild.id)
                    await muteEntry[0].remove_roles(discord.Object(muterole), reason= f'{muteEntry[0]} Unmuted after timeout.')
                except:
                    pass
                await self.client.db.execute('UPDATE guildsettings SET mutedmems = ARRAY_REMOVE(mutedmems, $2::numeric) WHERE guild_id = $1',
                    muteEntry[0].guild.id, muteEntry[0].id)

    # Temp bans handler.
    @tasks.loop(seconds= 30)
    async def tempban_handler(self):
        tempbans= await self.client.db.fetch('SELECT * FROM tempbans WHERE timestamp < $1', int(time()))
        if not tempbans:
            return
        for tempban in tempbans:
            user= discord.Object(tempban['user_id'])
            guild= self.client.get_guild(tempban['guild_id'])
            await guild.unban(user, reason= 'This user was banned using tempban command. There time has come to taste unban.')

    # clear command
    @commands.group(aliases= ['purge', 'delete'], invoke_without_command=True)
    @commands.cooldown(2, 7, BucketType.guild)
    @commands.bot_has_permissions(manage_messages= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(manage_messages= True, manage_guild= True))
    async def clear(self, ctx, count : int, *, user: discord.Member= None):
        if not user:
            def check(m):
                return True
        else:
            def check(m):
                return m.author.id == user.id
        await ctx.channel.trigger_typing()
        start= time()
        deleted= await self.brokencl(ctx, count, check)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command()
    async def bots(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def is_a_bot(m):
            return m.author.bot
        deleted= await self.brokencl(ctx, count, is_a_bot)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['humans', 'nonbots', 'user'])
    async def users(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def is_a_user(m):
            return not m.author.bot
        deleted= await self.brokencl(ctx, count, is_a_user)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['embed'])
    async def embeds(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_embeds(m):
            return len(m.embeds) != 0
        deleted= await self.brokencl(ctx, count, has_embeds)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['u','self'])
    async def you(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def is_me(m):
            return self.client.user == m.author
        deleted= await self.brokencl(ctx, count, is_me)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['links','url'])
    async def link(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_link(m):
            regex= r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
            if re.search(regex, m.content):
                return True
            else: return False
        deleted= await self.brokencl(ctx, count, has_link)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['invites'])
    async def invte(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_invite(m):
            regex= r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
            if re.search(regex, m.content):
                return True
            else: return False
        deleted= await self.brokencl(ctx, count, has_invite)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['attachments'])
    async def files(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_attachments(m):
            regex= r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
            if m.attachments:
                return True
            else: return False
        deleted= await self.brokencl(ctx, count, has_attachments)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['pin'])
    async def pins(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def is_pinned(m):
            return m.pinned
        deleted= await self.brokencl(ctx, count, is_pinned)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['contains'])
    async def contain(self, ctx, count: int, *, text:str):
        await ctx.channel.trigger_typing()
        start= time()
        def is_contained(m):
            return text.lower() in m.content
        deleted= await self.brokencl(ctx, count, is_contained)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['mentions'])
    async def mention(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_mentions(m):
            return len(m.mentions) != 0
        deleted= await self.brokencl(ctx, count, has_mentions)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'<:check:857494064294264862> Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after = 5.0)

    # clear till command, one of the unique feature.
    @commands.group(aliases= ['purgetill', 'deletetill'], invoke_without_command=True)
    @commands.bot_has_permissions(manage_messages= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(manage_messages= True, manage_guild= True))
    @commands.cooldown(2, 7, BucketType.guild)
    async def cleartill(self, ctx, userID: int= None):
        await ctx.channel.trigger_typing()
        if ctx.message.reference:
            msg= ctx.message.reference.resolved
            if userID:
                def check(m):
                    return userID == m.author.id
            else:
                def check(m):
                    return True
        else:
            await ctx.send('You need to reply to the message while using command to purge messages after that message.')
            return
        await ctx.message.delete()
        deleted= await self.brokencltill(ctx, check, msg= msg)
        embed= discord.Embed(
            title= f'<:check:857494064294264862> Purged {deleted} messages',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @cleartill.command(aliases= ['bots'])
    async def bot(self, ctx):
        await ctx.channel.trigger_typing()
        if ctx.message.reference:
            msg= ctx.message.reference.resolved
            def is_a_bot(m):
                return m.author.bot
        else:
            await ctx.send('You need to reply to the message while using command to purge messages after that message.')
            return
        await ctx.message.delete()
        deleted= await self.brokencltill(ctx, is_a_bot, msg= msg)
        embed= discord.Embed(
            title= f'<:check:857494064294264862> Purged {deleted} messages',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @cleartill.command(aliases= ['users', 'humans', 'notbots'])
    async def user(self, ctx):
        await ctx.channel.trigger_typing()
        if ctx.message.reference:
            msg= ctx.message.reference.resolved
            def is_a_human(m):
                return not m.author.bot
        else:
            await ctx.send('You need to reply to the message while using command to purge messages after that message.')
            return
        await ctx.message.delete()
        deleted= await self.brokencltill(ctx, is_a_human, msg= msg)
        embed= discord.Embed(
            title= f'<:check:857494064294264862> Purged {deleted} messages',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @cleartill.command(aliases= ['self'], help= 'Deletes all message of the bot after the replied message.')
    async def ufo(self, ctx):
        await ctx.channel.trigger_typing()
        if ctx.message.reference:
            msg= ctx.message.reference.resolved
            def is_me(m):
                return m.author.id == self.client.user.id
        else:
            await ctx.send('You need to reply to the message while using command to purge messages after that message.')
            return
        deleted= await self.brokencltill(ctx, is_me, msg= msg)
        embed= discord.Embed(
            title= f'<:check:857494064294264862> Purged {deleted} messages',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)

    # ban command
    @commands.command()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.bot_has_permissions(ban_members= True)
    @commands.cooldown(2, 10, BucketType.guild)
    async def ban(self, ctx, member: Union[discord.Member, discord.User], daysToDelete: Union[int, str]= '', *, reason= None):
        if isinstance(daysToDelete, str):
            reason= daysToDelete+ ' ' + reason if reason else ''
            reason= reason.strip()
            daysToDelete= 0
        if isinstance(daysToDelete, int):
            if daysToDelete> 7:
                daysToDelete= 7
            if daysToDelete< 0:
                daysToDelete= 0
        if isinstance(member, discord.Member):
            if (member == ctx.author):
                await ctx.send('You can\'t ban urself.')
                return
            if member.id == ctx.me.id:
                await ctx.send('You wanna ban me? Use other bot or do it urself u lazy human!')
                return
            if member.guild_permissions.administrator == True:
                await ctx.send('You can\'t ban an admin.')
                return
            if member.top_role.position >= ctx.author.top_role.position:
                await ctx.send('You doin\'t have permission to ban them.')
                return
            if member.top_role.position >= ctx.me.top_role.position:
                await ctx.send('I can\'t ban the mentioned user.')
                return
        embed= discord.Embed(
            title= 'U have been banned!',
            description= f'You have been banned from {ctx.guild.name}.',
            color= discord.Color.red(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Reason', value= reason)
        embed.set_footer(text= str(ctx.author), icon_url= ctx.author.avatar_url)
        embed.set_author(name= ctx.guild.name, icon_url= ctx.guild.icon_url)
        try:
            await member.send(embed= embed)
        except:
            pass
        await ctx.guild.ban(user= member, reason= reason, delete_message_days= daysToDelete)
        embed= discord.Embed(
            title= 'User Banned!',
            description= f'<:check:857494064294264862> Banned **{member.display_name}** and deleted all of their messages before {daysToDelete} days.',
            color= discord.Color.green()
        )
        embed.add_field(name= 'Reason', value= reason)
        await ctx.send(embed= embed)

    # Mass ban command
    @commands.command(aliases= ['multiban'])
    @commands.bot_has_permissions(ban_members= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.cooldown(2, 20, BucketType.user)
    async def massban(self, ctx, userids: commands.Greedy[int], *, reason= None):
        await ctx.channel.trigger_typing()
        reason = reason or str(ctx.author)
        if not len(userids):
            await ctx.send('You need to provide me the ids of members whome u want to ban.')
            return
        elif len(userids) > 12:
            await ctx.send('Maximum of 12 memberIDs can be given in mass ban.')
        bans= await ctx.guild.bans()
        for id in userids:
            member= discord.Object(id)
            try:
                await ctx.guild.ban(user= member, reason= reason, delete_message_days= 0)
            except: pass
        afterbans= set(await ctx.guild.bans()) - set(bans)
        afterbans= list(afterbans)
        membannedids= []
        successtext= ''
        for i in range(0, len(afterbans)):
            successtext+= f'{afterbans[i][1].name} - ({afterbans[i][1].id})\n'
            membannedids.append(afterbans[i][1].id)
        failed= list(set(userids)- set(membannedids))
        embed= discord.Embed(
            title= f'Mass banned {len(afterbans)} people!',
            description= f'With reason {reason}',
            color= discord.Color.green(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Succesfull!', value= successtext if len(successtext)>0 else 'No success lmao', inline= False)
        embed.add_field(name= 'Failed!', value= '\n'.join(map(str, failed))) if failed else None
        await ctx.send(embed= embed)

    # Mass Unban
    @commands.command(aliases= ['multiunban'])
    @commands.bot_has_permissions(ban_members= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.cooldown(2, 20, BucketType.user)
    async def massunban(self, ctx, userids: commands.Greedy[int], *, reason= None):
        await ctx.channel.trigger_typing()
        reason = reason or str(ctx.author)
        if not len(userids):
            await ctx.send('You need to provide me the ids of members whome u want to ban.')
            return
        elif len(userids) > 12:
            await ctx.send('Maximum of 12 memberIDs can be given in mass ban.')
        bans= await ctx.guild.bans()
        for id in userids:
            member= discord.Object(id)
            try:
                await ctx.guild.unban(user= member, reason= reason)
            except: pass
        afterbans= set(bans)- set(await ctx.guild.bans())
        afterbans= list(afterbans)
        membannedids= []
        successtext= ''
        for i in range(0, len(afterbans)):
            successtext+= f'{afterbans[i][1].name} - ({afterbans[i][1].id})\n'
            membannedids.append(afterbans[i][1].id)
        failed= list(set(userids)- set(membannedids))
        embed= discord.Embed(
            title= f'Mass unbanned {len(afterbans)} people!',
            description= f'With reason {reason}',
            color= discord.Color.green(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Succesfull!', value= successtext if len(successtext)>0 else 'No success lmao', inline= False)
        embed.add_field(name= 'Failed!', value= '\n'.join(map(str, failed))) if failed else None
        await ctx.send(embed= embed)

    # Temp ban command
    @commands.command(aliases= ['tban'])
    @commands.bot_has_permissions(ban_members= True)
    @commands.guild_only()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    async def tempban(self, ctx, member: discord.Member, time: str, *, reason: str= None):
        reason= reason or str(ctx.author)
        time= self.convert(time)
        if time< 300:
            await ctx.send('Tempbans below 5 mins are considered to be troll tempbans, pls retry with proper duration.')
            return
        id= member.id
        await self.ban(ctx, member, reason+f'with temp ban that will expire after {self.client.timeconv(time)}')
        vals= [id, ctx.guild.id, int(datetime.datetime.utcnow().timestamp()+time)]
        await self.client.db.execute('INSERT INTO tempbans VALUES (user_id = $1, guild_id = $2, timestamp = $3)', *vals)

    # Soft ban
    @commands.command(aliases= ['sban'])
    @commands.bot_has_permissions(ban_members= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.cooldown(2,15, BucketType.user)
    async def softban(self, ctx, member: discord.Member, *, reason: str= None):
        reason= reason or str(ctx.author)
        id= member.id
        await self.ban(ctx, member, 7, reason= reason+' with soft ban.')
        try:
            await ctx.guild.unban(discord.Object(id), reason= f'It was a soft ban by {ctx.author}')
        except:
            pass

    # Mute command
    @commands.command(aliases= ['shut'])
    @commands.bot_has_permissions(manage_roles= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(manage_roles= True))
    @commands.cooldown(2, 10, BucketType.guild)
    async def mute(self, ctx, member: discord.Member, time: str= None, *, reason= None):
        reason= reason or str(ctx.author)
        if member == ctx.author:
            await ctx.send('You can\'t mute urself.')
            return
        elif member.id == ctx.me.id:
            await ctx.send('You wanna mute me? Use other bot or do it urself u lazy human! :(')
            return
        elif member.guild_permissions.administrator == True:
            await ctx.send('You can\'t mute an admin.')
            return
        elif member.top_role.position >= ctx.author.top_role.position:
            await ctx.send('You doin\'t have permission to mute them.')
            return
        elif member.top_role.position >= ctx.me.top_role.position:
            await ctx.send('I can\'t mute the mentioned user.')
            return
        muterole= await self.client.db.fetchrow('SELECT muterole_id, mutedmems FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        mutedmems, muterole= muterole['mutedmems'], muterole['muterole']
        if member.id in mutedmems:
            return await ctx.send('User is already muted muted.')
        if muterole == None:
            await ctx.send('Muterole isn\'t setuped in this guild, use `muterole` command to setup a mute role.')
            return
        try:
            muterole= discord.Object(int(muterole))
            await member.add_roles(muterole, reason= reason)
        except:
            await ctx.send('I was unable to add role, maybe because the mute role is above my role or mute role was deleted.')
        time= self.convert(time) if time else None
        if time != None:
            if time > 1209600:
                await ctx.send("Mute duration cant be more then 14 days.")
            if time < 10:
                await ctx.send('Time can\'t be less than 10 seconds.')
        embed= discord.Embed(
            title= 'Muted!',
            description= f'Muted **{member.display_name}** with reason *{reason}*',
            color= discord.Color.green(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Duration of mute', value= self.client.timeconv(time)) if time else None
        await ctx.send(embed= embed)
        if time != None:
            self.client.mutemem.append((member, datetime.datetime.utcnow().timestamp()+time))
        await self.client.db.execute('UPDATE guildsettings SET mutedmems = mutedmems || ARRAY[$2::NUMERIC(18)] WHERE guild_id = $1',
            ctx.guild.id, member.id)

    # Unmute command
    @commands.command(aliases= ['unshut'])
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(manage_roles= True))
    @commands.bot_has_permissions(manage_roles= True)
    @commands.cooldown(2, 10, BucketType.guild)
    async def unmute(self, ctx, member: discord.Member):
        muterole= await self.client.db.fetchrow('SELECT muterole_id, mutedmems FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
        mutedmems, muterole= muterole['mutedmems'], muterole['muterole']
        if not mutedmems:
            return await ctx.send('User isn\'t muted.')
        elif not member.id in mutedmems:
            return await ctx.send('User isn\'t muted.')
        try:
            await member.remove_roles(discord.Object(muterole), reason= f'{ctx.author} Unmuted.')
        except:
            await ctx.send('I\'m unable to remove the mute role. Might be because I don\'t have perms or the mute role was manually removed after.')
        embed= discord.Embed(
            description= f'Unmuted **{member}**',
            color= discord.Color.green()
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)
        await self.client.db.execute('UPDATE guildsettings SET mutedmems = ARRAY_REMOVE(mutedmems, $2::NUMERIC(18)) WHERE guild_id = $1', ctx.guild.id, member.id)
        for muteEntery in self.client.mutemem:
            if muteEntery[0].id == member.id:
                self.client.mutemem.remove(muteEntery)
                break

    # kick command
    @commands.command()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(kick_members= True))
    @commands.bot_has_permissions(kick_members= True)
    @commands.cooldown(2, 10, BucketType.guild)
    async def kick(self, ctx, member: discord.Member, *, reason= None):
        if member == ctx.author:
            await ctx.send('You can\'t kick urself.')
            return
        elif member.id == ctx.me.id:
            await ctx.send('Goodbye? You forgot what I did for u? :(')
            return
        elif member.guild_permissions.administrator == True:
            await ctx.send('You can\'t kick an admin.')
            return
        elif member.top_role.position >= ctx.author.top_role.position:
            await ctx.send('You dont have permission to ban them.')
            return
        elif member.top_role.position >= ctx.me.top_role.position:
            await ctx.send('I don\'t have permission to ban them.')
        await ctx.guild.kick(user= member, reason= reason)
        embed= discord.Embed(
            title= 'U have been kicked!',
            description= f'You have been kicked from {ctx.guild.name}.',
            color= discord.Color.red(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Reason', value= reason or 'No reason was given.')
        embed.set_footer(text= str(ctx.author), icon_url= ctx.author.avatar_url)
        embed.set_author(name= ctx.guild.name, icon_url= ctx.guild.icon_url)
        try:
            await member.send(embed= embed)
        except:
            pass
        embed= discord.Embed(
            description= f'<:check:857494064294264862> kicked **{member.display_name}**',
            color= discord.Color.green()
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        embed.add_field(name= 'Reason', value= reason)
        await ctx.send(embed= embed)
        channel= await self.client.db.fetchval('SELECT logch FROM guildsettings WHERE guild_id = $1 AND $2 = any(logging)', ctx.guild.id, 'kick')
        if channel:
            casecount= await self.file_case(ctx.guild, 'kick', member.id, reason= reason)
            channel= ctx.guild.get_channel(channel)
        else: return
        embed= discord.Embed(
            title= f'Case {casecount}',
            description= f'**{ctx.author}** Kicked **{member}**',
            color= discord.Color.red()
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        embed.add_field(name= 'Reason', value= reason or f'No reason was given.')
        await channel.send(embed= embed)

    # unban command
    @commands.command()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.bot_has_permissions(ban_members= True)
    @commands.cooldown(2, 10, BucketType.guild)
    async def unban(self, ctx, userID: int, *, reason= None):
        bans= await ctx.guild.bans()
        user= discord.Object(id= userID)
        await ctx.guild.unban(user= user, reason= reason)
        afterbans= await ctx.guild.bans()
        user= set(bans)- set(afterbans)
        user= list(user)
        user= user[0]
        embed= discord.Embed(
            title= 'User Unbanned!',
            description= f'<:check:857494064294264862> Unbanned **{user[1].name}**',
            color= discord.Color.green()
        )
        embed.add_field(name= 'Reason', value= reason)
        await ctx.send(embed= embed)

    # warn command
    @commands.command(aliases= ['redcard'],
        help= "Warns the user. You can optionaly pass time like `1d12h30m30s` which is max at 14 days, u can alse pass count to amount of warnings to add",
        description= "If user crosses the `kickat` or `banat` amount of warnings, they will be treeted",
        usage= "<member> [reason]\nOR\n<member> [count < 10] [reason]")
    @commands.cooldown(2, 10, BucketType.guild)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True, kick_members= True))
    async def warn(self, ctx, member: discord.Member, count: Union[int, str]= 1, reason: str= None):
        if member.bot:
            return await ctx.send(f'Can\'t warn a bot.')
        if isinstance(count, str):
            reason= count + (reason if reason else '')
            count= 1
        if count>= 10: return await ctx.send('U can warn a member upto 10 times per command usage.')
        async with self.client.db.acquire() as conn:
            await conn.set_type_codec(
                'json',
                encoder= dumps,
                decoder= loads,
                schema= 'pg_catalog'
            )
            raw= await conn.fetchrow('SELECT warns::json, banat, kickat FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
            if not raw: raw= {'warns': None, 'kickat': 0, 'banat': 0}
        warnings= raw['warns'] if raw['warns'] else {}
        banat= raw['banat']
        kickat= raw['kickat']
        if str(member.id) in warnings.keys():
            warns= warnings[str(member.id)]
        else:
            warns= 0
        warns+= count
        warnings.update({str(member.id): warns})
        if warns >= banat and banat != 0:
            try:
                command= self.client.get_command('ban')
                return await ctx.invoke(command, member= member, daysToDelete= 0, reason= 'Kicked for crossing Kick At limit.')
            except:
                return await ctx.send(f'**{member}** have crossed Ban At threshold but I couldn\'t ban them.\nAnyways, they got **{warns}** warnings.')
        elif warns >= kickat and kickat != 0:
            try:
                command= self.client.get_command('kick')
                return await ctx.invoke(command, member= member, reason= 'Kicked for crossing Kick At limit.')
            except:
                return await ctx.send(f'**{member}** have crossed kick At threshold but I couldn\'t kick them.\nAnyways, they got **{warns}** warnings.')
        embed= discord.Embed(
            description= f'<:check:857494064294264862> **{member}** has been warned. They have `{warns}` warns now.',
            color= discord.Color.green()
        )
        embed.add_field(name= 'Reason', value= reason)
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        embed.set_footer(text= str(member), icon_url= member.avatar_url)
        await ctx.send(embed= embed)
        async with self.client.db.acquire() as conn:
            await conn.set_type_codec(
                'json',
                encoder= dumps,
                decoder= loads,
                schema= 'pg_catalog'
            )
            await conn.execute('INSERT INTO guildsettings(guild_id, warns) VALUES ($2, $1::json) ON CONFLICT ON CONSTRAINT guildsettings_pkey\
                DO UPDATE SET warns = EXCLUDED.warns', warnings, ctx.guild.id)
            channel= await conn.fetchval('SELECT logch FROM guildsettings WHERE guild_id = $1 AND $2 = any(logging)', ctx.guild.id, 'warns')
            if channel:
                casecount= await self.file_case(ctx.guild, 'warn', member.id, reason= reason)
                channel= ctx.guild.get_channel(channel)
            else: return
        embed= discord.Embed(
            title= 'Member Warned!',
            description= f'**{member}** was warned by moderator **{ctx.author}** who have `{warns}` warns now.',
            color= discord.Color.magenta()
        )
        embed.set_author(name= f'Case {casecount}')
        embed.add_field(name= 'Reason', value= reason if reason else 'No reason was given.')
        await channel.send(embed= embed)

    @commands.command(ailiases= ['forgive'],
        help= 'Remove a warning from someone.',
        description= 'You can remove upto 10 warns at a time.')
    @commands.cooldown(2,10,BucketType.guild)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True, kick_members= True))
    async def pardon(self, ctx, member: discord.Member, count: Union[int, str]= 1, reason: str= None):
        if member.bot:
            return await ctx.send(f'Can\'t warn a bot.')
        if isinstance(count, str):
            reason= count + (reason if reason else '')
            count= 1
        if count>= 10: return await ctx.send('U can pardon a member upto 10 times per command usage.')
        async with self.client.db.acquire() as conn:
            await conn.set_type_codec(
                'json',
                encoder= dumps,
                decoder= loads,
                schema= 'pg_catalog'
            )
            warnings= await conn.fetchval('SELECT warns::json FROM guildsettings WHERE guild_id = $1', ctx.guild.id)
            warnings= warnings or {}
            channel= await conn.fetchval('SELECT logch FROM guildsettings WHERE guild_id = $1 AND $2 = ANY(logging)', ctx.guild.id, 'warns')
        if not str(member.id) in warnings.keys() or warnings[str(member.id)] == 0:
            return await ctx.send('They already have `0` warnings.')
        if warnings[str(member.id)] <= count:
            warnings[str(member.id)]= 0
        else:
            warnings[str(member.id)]= warnings[str(member.id)] - count
        embed= discord.Embed(
            description= f'<:check:857494064294264862> **{member}** has been pardoned. They have `{warnings[str(member.id)]}` warns now.',
            color= discord.Color.green()
        )
        embed.add_field(name= 'Reason', value= reason)
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        embed.set_footer(text= str(member), icon_url= member.avatar_url)
        await ctx.send(embed= embed)
        async with self.client.db.acquire() as conn:
            await conn.set_type_codec(
                'json',
                encoder= dumps,
                decoder= loads,
                schema= 'pg_catalog'
            )
            await conn.execute(f'UPDATE guildsettings SET warns = $1::json WHERE guild_id = {ctx.guild.id}', warnings)
        if channel:
            channel= ctx.guild.get_channel(channel)
            if not channel: return
            casecount= await self.file_case(ctx.guild, 'Pardon', member.id, reason)
        else:
            return
        embed= discord.Embed(
            title= 'Member Pardoned!',
            description= f'**{member}** was pardoned by moderator **{ctx.author}** who have `{warnings[str(member.id)]}` warns now.',
            color= discord.Color.magenta()
        )
        embed.set_author(name= f'Case {casecount}')
        embed.add_field(name= 'Reason', value= reason if reason else 'No reason was given.')
        await channel.send(embed= embed)

    # A command to give role to or remove role from members.
    @commands.group(aliases= ['yum'], invoke_without_command= True, help= 'Command that can be used to give/take back roles.')
    @commands.cooldown(2, 10, BucketType.guild)
    @commands.bot_has_guild_permissions(manage_roles= True)
    @commands.check_any(commands.check(has_modrole), commands.has_guild_permissions(manage_roles= True))
    async def role(self, ctx):
        await ctx.send_help(ctx.command)
    @role.command(name= 'add', aliases= ['give', 'plus', '+'])
    async def _add(self, ctx, member: discord.Member, role: discord.Role):
        try:
            await member.add_roles(role, reason= f'My master {ctx.author} told me.')
        except:
            if role.position > ctx.me.top_role.position:
                await ctx.send('`Failed` to give the role, `Role above me`')
            elif role.is_bot_managed():
                await ctx.send('`Failed` to give the role, `Role is managed by a bot`')
            elif role.is_default():
                await ctx.send('`Failed` to give the role, `Role is default role, they already have it`')
            elif role.is_premium_subscriber():
                await ctx.send('`Failed` to give the role, `Role is a nitro booster role`')
            elif role.is_integration():
                await ctx.send('`Failed` to give the role, `Role is managed by some integration`')
            else:
                await ctx.send('Can\'t add the role')
            return
        embed= discord.Embed(
            title= 'Role was added!',
            description= f'{role.mention} was given to {member.mention}',
            color= role.color if role.color != discord.Color.default() else discord.green()
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)
    @role.command(name= 'remove', aliases= ['rem', 'minus', '-', 'take'])
    async def _remove(self, ctx, member: discord.Member, role: discord.Role):
        try:
            await member.remove_roles(role, reason= f'My master {ctx.author} told me.')
        except:
            if role.position > ctx.me.top_role.position:
                await ctx.send('`Failed` to remove the role, `Role above me`')
            elif role.is_bot_managed():
                await ctx.send('`Failed` to remove the role, `Role is managed by a bot`')
            elif role.is_default():
                await ctx.send('`Failed` to remove the role, `Role is default role, they already have it`')
            elif role.is_premium_subscriber():
                await ctx.send('`Failed` to remove the role, `Role is a nitro booster role`')
            elif role.is_integration():
                await ctx.send('`Failed` to remove the role, `Role is managed by some integration`')
            else:
                await ctx.send('Can\'t remove the role')
            return
        embed= discord.Embed(
            title= 'Role was removed!',
            description= f'{role.mention} was removed {member.mention}',
            color= role.color if role.color != discord.Color.default() else discord.green()
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)

    @commands.command(name= 'case', aliases= ['cs'], help= 'Shows/Edit a modlog case.')
    @commands.cooldown(2,10, BucketType.user)
    async def _case(self, ctx, case: int, *, reason= None):
        async with self.client.db.acquire() as con:
            await con.set_type_codec(
                'jsonb',
                encoder= dumps,
                decoder= loads,
                schema= 'pg_catalog'
            )
            casedata= await con.fetchval(f'SELECT logs::jsonb[] as case FROM guildsettings WHERE guild_id = {ctx.guild.id}')
            try:
                casedata= casedata[case-1]
            except:
                casedata= False
            if not casedata:
                casecount= await con.fetchval(f'SELECT ARRAY_LENGTH(logs::jsonb[], 1) FROM guildsettings WHERE guild_id = {ctx.guild.id}')
            else: casecount= 501
            if casedata and reason:
                perms= ctx.author.guild_permissions
                reasonwillchange= casedata['reason'] != reason and (perms.manage_guild or perms.administrator or await self.has_modrole(ctx))
            else:
                reasonwillchange= False
            if reasonwillchange:
                casedata.update({'reason':reason})
                await con.execute(f'UPDATE guildsettings SET logs[{case}] = $1::jsonb', casedata)
            if not (ctx.author.guild_permissions.manage_guild or await self.has_modrole(ctx)) and casedata['member'] != ctx.author.id:
                return await ctx.send('Your can only veiw cases related to you.\nOne require `Manage server permission or modrole to see/edit any case`')
            if casecount< case:
                return await ctx.send(f'There are only `{casecount}` cases in this guild, pls select a number from 1 to {casecount} only. Note case count reset after 500 cases.')
            elif casecount== 0:
                return await ctx.send('There are no cases in this guild. This might be because UFO logging isn\'t set in this guild.')
        embed= discord.Embed(
            title= f'Case {case}',
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
            description= f'The case was registered for {casedata["member"]}'
        )
        embed.add_field(name= 'Action', value= casedata["action"], inline= False)
        if reasonwillchange:
            embed.add_field(name= 'Reason Changed to', value= reason)
        else:
            embed.add_field(name= 'Reason', value= casedata['reason'])
        await ctx.send(embed= embed)

    @commands.command(aliases= ['sm', 'slowm', 'smode'], help= 'Sets the slow-mode the the mentioned channel or the current channel.')
    @commands.bot_has_permissions(manage_channels= True)
    @commands.check_any(commands.check(has_modrole), commands.has_guild_permissions(manage_channels= True))
    async def slowmode(self, ctx, time: Union[int, str]= 0, channel: discord.TextChannel= None):
        channel: discord.TextChannel= channel or ctx.channel
        if isinstance(time, int):
            if time < 0:
                time= 0
            if time > 21600:
                time= 21600
        else:
            time= self.convert(time)
        await channel.edit(slowmode_delay= time)
        embed= discord.Embed(
            title= f'Slowmode set to {self.client.timeconv(time)}' if time else 'Slowmode removed!',
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)

    #@commands.command(help= 'Sends a paginatate menu to go through modlog cases.')

    @commands.command(hidden= True)
    @commands.is_owner()
    async def ddu(self, ctx):
        if ctx.message.reference:
            await ctx.message.reference.resolved.delete()
        else:
            return

def setup(client):
    client.add_cog(Moderation(client))
import discord
from discord.ext import commands, tasks
import asyncio
import random
from datetime import datetime, timedelta
import re

class Giveaways(commands.Cog):
    def __init__(self, client):
        self.client= client

    print("Giveaway.py has been loaded\n-----------------------------------")

    # Checking for disabled commands
    async def cog_check(self, ctx):
        if not ctx.guild:
            return False
        discmds= await self.client.db.tables['guildsettings'].select('discmds', where= {'guild_id': ctx.guild.id})
        try:
            return not ctx.command.name in discmds[0]['discmds']
        except: return True

    def convert(self, time):
        time_regex= re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
        time_dict= {"h": 3600, "s": 1, "m": 60, "d": 86400}
        time= time.lower()
        matches= re.findall(time_regex, time)
        time= 0
        for key, value in matches:
            try:
                time += time_dict[value] * float(key)
            except KeyError:
                raise commands.BadArgument(f"{value} is an invalid time key! h|m|s|d are valid arguments")
            except ValueError:
                raise commands.BadArgument(f"{key} is not a number!")
        return round(time)

    # Custom Check if user can moderate with the power of modrole
    async def has_modrole(ctx):
        modrole= await ctx.bot.db.tables['guildsettings'].select('modrole_id', where= {'guild_id': ctx.guild.id})
        if modrole[0]['modrole_id']== None or modrole[0]['modrole_id'] == 'NULL':
            return False
        try:
            return await commands.has_role(int(modrole[0]['modrole_id'])).predicate(ctx)
        except:
            return False

    @tasks.loop(seconds= 20)
    async def giveaway_handler(self):
        giveaways= await self.client.db.tables['giveaways'].select('*', where= ['timestamp', '<', int(datetime.utcnow().timestamp())])
        for giveaway in giveaways:
            msg= await self.client.fetch_message(int(giveaway['message_id']))
            users= await msg.reactions[0].users().flatten()
            users.pop(users.index(self.client.user))
            if len(users) == 0:
                em= discord.Embed(title= 'Giveaway Failed', color= discord.Color.default())
                em.add_field(name= "Reason:", value= "No one reacted in time!")
                await msg.channel.send(embed= em)
                return
            winners= ""
            wincount= giveaway['winner_count']
            prize= giveaway['prize']
            for i in range(0, wincount):
                if len(users) == 0:
                    break
                winner= random.choice(users)
                users.remove(winner)
                winners += f"{winner.mention}, "

            # edit embed to show winner
            newembed= discord.Embed(title= "Giveaway Ended!", description= f"{prize}", timestamp= datetime.utcnow())
            # now do winers gizmo
            newembed.add_field(name= "Winner", value= f"{winners[:-2]}")
            newembed.set_footer(text= f"Ended at ", icon_url="https://qotoqot.com/sad-animations/img/400/shy/shy.gif")
            await msg.edit(embed= newembed)
            await msg.channel.send(f"Congratulations! {winners[:-2]} won **{prize}**!")

    # Lmao this is the Biggest command, Yet efficient.
    @commands.command(aliases= ['giveaway', 'ga'],
        help= 'Start a giveaway in a channel where I have permission to embed links.',
        description= 'You would require ')
    @commands.check_any(commands.check(has_modrole), commands.has_guild_permissions(manage_channels= True, manage_guild= True))
    @commands.guild_only()
    async def gstart(self, ctx):
        guild_gways= await self.client.db.tables['giveaways'].select('*', where= {'guild_id': str(ctx.guild.id)})
        if len(guild_gways)>= 5:
            await ctx.send('There are already 5 giveaways running in the current guild. Tarry there.')
        startmessage= await ctx.send("Let's start with this giveaway! Answer these questions within 60 seconds!")

        questions= ["Which channel should it be hosted in?",
                    "What should be the duration of the giveaway? (s|m|h|d)",
                    "What is the prize of the giveaway?",
                    "Tell me how many winners u want to have?",
                    "What role to mention? You can mention the role/give the roleid.\n`skip` to send without mentions"]

        answers= []
        Questions : discord.Message= await ctx.send("Starting...")

        for i in questions:
            embed= discord.Embed(title= "Starting a giveaway!", description= i, color= ctx.author.color)
            embed.set_footer(text= "Alternatively type `Stop` to cancel command")
            await Questions.edit(embed= embed)

            try:
                msg= await self.client.wait_for('message', 
                    timeout= 60.0, 
                    check= lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id)
                if msg.content.lower() == "stop":
                    await ctx.send(":x: Giveaways Cancelled")
                    await Questions.edit(content= "Stopped!")
                    await startmessage.delete()
                    return
            except asyncio.TimeoutError:
                await ctx.send('Oh ho! You failed to send message on time, be quicker next time.')
                return
            else:
                answers.append(msg.content)

        try:
            c_id= int(answers[0][2:-1])
        except:
            await ctx.send(f"You didn't mention a channel properly. Do it like {ctx.channel.mention} next time.")
            return

        channel= self.client.get_channel(c_id)

        time= self.convert(answers[1])
        if time <= 30:
            await ctx.send(f"Time can't be `{time}`, it should be a value greater then 30s.")
            return

        prize= answers[2]
        wincount= int(answers[3])
        a= answers[4]
        if a != 'skip':
            mentionrole= ""
            for i in a:
                try:
                    if int(i) in range(0,10):
                        mentionrole += i
                except:
                    pass
            mentionrole= f"<@&{mentionrole}>"
        else:
            mentionrole= u"\u200B"
        
        if wincount < 1:
            await ctx.send(f"Oh ho {ctx.author.mention}! winners can't be less then 1.")
            return
        
        # send a message for the user to know the giveaway started!
        confembed= discord.Embed(
            title= "Giveaway started!",
            description= f"Giveaway started at {channel.mention} and will last `{time}` seconds!",
            color= ctx.guild.me.color)
        await Questions.edit(content= "", embed= confembed, )
        await startmessage.delete()
        # now send the embed in the channel!
        embed= discord.Embed(title= "Giveaway!", description= prize, color= ctx.guild.me.color, timestamp= datetime.utcnow())
        embed.add_field(name= "Hosted by:", value= ctx.author.mention)
        end_time= datetime.utcnow() + timedelta(seconds= time)
        embed.add_field(name= "Ends at:", value= end_time.strftime("`%m/%d/%Y, %H:%M` UTC"))
        embed.set_footer(text= f"Started at ", icon_url='https://images-ext-1.discordapp.net/external/ZaAMSwxiAFN_-cRIFkr6uHHNITfAPsE9SFRm_RRVCfQ/https/cdn.discordapp.com/emojis/724135911331463279.gif')
        my_msg= await channel.send(mentionrole, embed= embed)
        # and then add the reactions
        await my_msg.add_reaction("🎉")
        vals= {'message_id': my_msg.id, 'prize': prize, 'winner_count': wincount, 'timestamp': int(datetime.utcnow().timestamp()), 'guild_id': ctx.guild.id}
        await self.client.db.tables['giveaways'].insert(**vals)
        return

    @commands.command(aliases= ['gr'])
    @commands.check_any(commands.check(has_modrole), commands.has_guild_permissions(manage_channels= True, manage_guild= True))
    @commands.guild_only()
    async def reroll(self,ctx, channel : discord.TextChannel, id : int):
        try:
            msg= await channel.fetch_message(id)
        except:
            await ctx.send("The id was entered incorrectly. Next time mention a channel and then the id!")
            return

        users= await msg.reactions[0].users().flatten()
        users.pop(users.index(self.client.user))

        winner= random.choice(users)
        await channel.send(f"Congratulations! The new winner is {winner.mention}!")

    @commands.command(aliases= ['glist', 'gs'])
    @commands.guild_only()
    async def giveaways(self, ctx):
        guild_gways= await self.client.db.tables['giveaways'].select('*', where= {'guild_id': str(ctx.guild.id)})
        if len(guild_gways) == 0:
            await ctx.send('There are no giveaways running in this server. Use `gstart` command to start a giveaway.')
            return
        embed= discord.Embed(
            title= 'Giveaways.',
            description= f'There are {len(guild_gways)} running in the server' if len(guild_gways)>1 else 'There is one gievaway running in the server.',
            color= ctx.me.color
        )
        for gway in guild_gways:
            embed.add_field(name= f"Msg.ID: {gway['message_id']}",
                value= f"Winner Count= **{gway['winner_count']}**\nEnds in= {self.client.timeconv(gway['timestamp']-datetime.utcnow().timestamp())}\nPrize= {gway['prize']}",
            )
        await ctx.send(embed= embed)

def setup(client):
    client.add_cog(Giveaways(client))
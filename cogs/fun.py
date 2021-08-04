import asyncio, aiohttp, json, re
from io import BytesIO
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageChops
import discord, os, wikipedia
from akinator.async_aki import Akinator
from discord.ext.commands.cooldowns import BucketType
from random import choice, randint
from art import text2art
from py_expression_eval import Parser
from itertools import cycle

class Fun(commands.Cog):
    def __init__(self, client):
        self.client= client
        self.locateauths= cycle(('tuple', 'of', 'your', 'api', 'key'))
        self.weatherauths= cycle(('tuple', 'of', 'your', 'api', 'key'))

    
    animals= ['dog', 'cat', 'fox', 'bird']
    langs= {
        'ga': 'Irish', 'sq': 'Albanian', 'it': 'Italian', 'ar': 'Arabic', 'ja': 'Japanese',
        'az': 'Azerbaijani', 'kn': 'Kannada', 'eu': 'Basque', 'ko': 'Korean', 'bn': 'Bengali',
        'la': 'Latin', 'be': 'Belarusian', 'lv': 'Latvian', 'bg': 'Bulgarian', 'lt': 'Lithuanian',
        'ca': 'Catalan', 'mk': 'Macedonian', 'zh-CN': 'Chinese Simplified', 'ms': 'Malay',
        'zh-TW': 'Chinese Traditional', 'mt': 'Maltese', 'hr': 'Croatian', 'no': 'Norwegian',
        'cs': 'Czech', 'fa': 'Persian', 'da': 'Danish', 'pl': 'Polish', 'nl': 'Dutch',
        'pt': 'Portuguese', 'en': 'English', 'ro': 'Romanian', 'eo': 'Esperanto', 'ru': 'Russian',
        'et': 'Estonian', 'sr': 'Serbian', 'tl': 'Filipino', 'sk': 'Slovak', 'fi': 'Finnish',
        'sl': 'Slovenian', 'fr': 'French', 'es': 'Spanish', 'gl': 'Galician', 'sw': 'Swahili',
        'ka': 'Georgian', 'sv': 'Swedish', 'de': 'German', 'ta': 'Tamil', 'el': 'Greek', 'te': 'Telugu',
        'gu': 'Gujarati', 'th': 'Thai', 'ht': 'Haitian Creole', 'tr': 'Turkish', 'iw': 'Hebrew',
        'uk': 'Ukrainian', 'hi': 'Hindi', 'ur': 'Urdu', 'hu': 'Hungarian', 'vi': 'Vietnamese',
        'is': 'Icelandic', 'cy': 'Welsh', 'id': 'Indonesian', 'yi': 'Yiddish'}

    print("Fun.py has been loaded\n-----------------------------------")

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

    @commands.command(
        aliases= ["weath","temperature","forecast"],
        help= "May be slightly inaccurate.",
        description= "Display weather of the provided place.",
        usage= '<Place Name>')
    @commands.cooldown(2, 60, BucketType.user)
    async def weather(self, ctx, place):
        async with aiohttp.ClientSession() as cs:
            url= "https://api.openweathermap.org/data/2.5/weather?q="+place+f"&appid={next(self.weatherauths)}"
            async with cs.get(url) as response:
                response= await response.json()
                if response["cod"] == "404":
                    await ctx.send(f"Either api not responding or I can't fetch weather report of __{place.capitalize()}__. Make sure u type exect name, case doesn't matter, no spaces", delete_after= 15.0)
                    return
                weather= response['main']
                embed= discord.Embed(title= f"Weather report of {place.capitalize()}", description= f"{response['weather'][0]['main']} > {response['weather'][0]['description']}",
                    color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
                embed.add_field(name= "Temperature", value= f"Feels like: **{round(weather['temp'] - 273.16),1}°C** ({round(weather['temp_min'] - 273.16, 2)} / {round(weather['temp_max'] - 273.16, 2)})", inline=False)
                embed.add_field(name= "Pressure", value= str(weather['pressure']), inline=True)
                embed.add_field(name= "Humidity", value= str(weather['humidity']), inline=True)
                embed.add_field(name= "Winds", value= f"{response['wind']['speed']}M/h along {response['wind']['deg']}°", inline=True)
                embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{response['weather'][0]['icon']}.png")
                await ctx.send(embed= embed)
    
    @commands.command(
        aliases= ["word"],
        help="Word must belong to ENGLISH dictionary!",
        description="Defines a words with proper examples.")
    @commands.cooldown(5, 60, BucketType.user)
    async def define(self, ctx, word : str):
        async with ctx.channel.typing():
            async with aiohttp.ClientSession() as cs:
                async with cs.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}") as response:
                    response= await response.json()
                    try:
                        if response['title'] == "No Definitions Found":
                            await ctx.send("No such word found in english dictionary.", delete_after= 10.0)
                            return
                    except:
                        pass
                    desc= ""
                    response= response[0]
                    try:
                        desc= f"Origin : __(say: _{response['phonetics'][0]['text']}_)__ {response['origin']}"
                    except:
                        desc= "Origin : `No Origin Found.`"
                    embed= discord.Embed(
                        title= word.capitalize(),
                        description= desc,
                        color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
                    i= 4
                    synonyms= []
                    for meaning in response['meanings']:
                        if i == 0:
                            break
                        i -= 1
                        value= ""
                        for definition in meaning['definitions']:
                            value += "'"+definition['definition']+"'" + "\n"
                            try:
                                value += "`eg.` " + f"_{definition['example']}_\n"
                            except:
                                pass
                            try:
                                synonyms += definition['synonyms']
                            except:
                                pass
                        embed.add_field(name= meaning['partOfSpeech'].capitalize(), value= value)
                    synonyms= list(set(synonyms))
                    syntext= "`No synonyms for this word``"
                    i= 0
                    for syn in synonyms:
                        if i == 0:
                            syntext= ""
                        if i == 15:
                            break
                        i += 1
                        syntext += f"`{syn}` "
                    embed.add_field(name= "Synonyms", value= syntext[:-1])
                    await ctx.send(embed=embed)
    
    @commands.command(
        aliases= ['pinpoint', 'whereis'],
        help="Pinpoint ur CITY in the map",
        description="Make sure this map only and only works with cities and other small areas, also this command is kinda beta so inaccuracy will be there far u go from equator.")
    @commands.cooldown(2, 90, BucketType.user)
    async def locate(self, ctx, *, place):
        await ctx.channel.trigger_typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f'https://geocode.xyz/{place}?json=1&auth={next(self.locateauths)}') as response:
                img= Image.open(f"{os.path.dirname(__file__)}/worldmap.png")
                response= await response.json()
                try:
                    await ctx.send(response['error']['message'])
                    return
                except:
                    pass
                long= round(float(response['longt']), 2)
                lat= round(float(response['latt']), 2)
                try:
                    country= response['standard']['countryname']
                except:
                    if long== 0.00 and lat== 0.00:
                        return await ctx.reply('`No location found.` Make sure only CITY name is accepted.')
                    country= "`No country found.`"
                x= int(360.00 + (2*long))
                y= int(180.00 - (2*lat))
                draw= ImageDraw.Draw(img)
                draw.line((0, y, 720, y), fill= (255,255,255))
                draw.line((x, 0, x, 360), fill= (255,255,255))
                font= f'{os.path.dirname(__file__)}/images/OpenSans-Light.ttf'
                font= ImageFont.truetype(font, 40)
                draw.text((x-7,y-25), '•', (255,0,0), font= font)
                img_bin= BytesIO()
                img.save(img_bin, 'PNG')
                img_bin.seek(0)
                file= discord.File(img_bin, f'TargetLocked.png')
                await ctx.send(f"Longitude: {long}\nLatitude: {lat}\nCountry: {country}", file= file)

    @commands.command(
        aliases= ["haha", "lmao"],
        help="Summon a ahh a joke!",
        description="Jokes can be one part or two part, if two part u need to react in order to see the next part of joke. Alright?")
    @commands.cooldown(5, 60, BucketType.user)
    async def joke(self, ctx):
        await ctx.channel.trigger_typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,racist') as response:
                response= await response.json()
                if response['error']:
                    await ctx.send(f"API raised an error: `{response['message']}`")
                if response['type'] == 'single':
                    embed= discord.Embed(title= response['category'], description= response['joke'],
                        color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
                    await ctx.reply(embed= embed)
                else:
                    embed= discord.Embed(title= response['category'], description= response['setup'],
                        color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
                    msg : discord.Message= await ctx.reply(embed= embed)
                    await msg.add_reaction(emoji= '👀')
                    def check(r, u):
                        return r.message == msg and str(r.emoji) == '👀' and u == ctx.author
                    try:
                        await self.client.wait_for('reaction_add', 
                            timeout= 30.0,
                            check= check)
                    except:
                        pass
                    embed.set_footer(text= response['delivery'])
                    await msg.edit(embed=embed)

    @commands.command(
        aliases= ['memes', 'lol'],
        help="Presents u a meme.",
        description="A random freshy meme from some top subreddits.")
    @commands.cooldown(5, 60, BucketType.user)
    async def meme(self, ctx):
        reddit= choice(['MemeEconomy', 'ComedyCemetery', 'memes', 'dankmemes', 'PrequelMemes', 'terriblefacebookmemes', 'funny', 'teenagers', 'watchpeopledieinside'])
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://meme-api.herokuapp.com/gimme/{reddit}") as response:
                response= await response.json()
                meme= discord.Embed(
                    title= f"r/{response['subreddit']}",
                    url= response['postLink'],
                    description= response['title'], color= discord.Color.orange())
                meme.set_author(
                    name= f"Posted by u/{response['author']}",
                    icon_url= "https://styles.redditmedia.com/t5_3kper/styles/profileIcon_snoo3e112319-987c-49e7-9dde-8858d422c529-headshot.png?width=256&height=256&crop=256:256,smart&s=e2f86a3a77245b62cf3b3f90f6de786ab0451bee",
                    url= f"https://www.reddit.com/user/{response['author']}")
                meme.set_footer(
                    icon_url="https://i.redd.it/b9zcqp6w31w51.jpg",
                    text= response['ups'])
                meme.set_image(url= response['preview'][-1])
                await ctx.reply(embed= meme)
    
    @commands.command(
        aliases= ['subreddit', 'rddt'],
        help="Just a tip, subreddits dont have spaces",
        description="Summons a randome top fresh post from the given reddit(not case sensitive:3)")
    @commands.cooldown(5, 60, BucketType.user)
    async def reddit(self, ctx, reddit):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://meme-api.herokuapp.com/gimme/{reddit}") as response:
                response= await response.json()
                try:
                    await ctx.send(f"**({response['code']})** {response['message']}")
                except KeyError:
                    pass
                meme= discord.Embed(
                    title= f"r/{response['subreddit']}",
                    url= response['postLink'],
                    description= response['title'], color= discord.Color.orange())
                meme.set_author(
                    name= f"Posted by u/{response['author']}",
                    icon_url= "https://bit.ly/3yyTE02",
                    url= f"https://www.reddit.com/user/{response['author']}")
                meme.set_footer(
                    icon_url="https://i.redd.it/b9zcqp6w31w51.jpg",
                    text= response['ups'])
                meme.set_image(url= response['preview'][-1])
                await ctx.reply(embed= meme)
    
    @commands.group(
        aliases= ['ani'], invoke_without_command=True,
        help="Cute animals.",
        description="Use this command with `list` argument to see list of animals u rquest for.")
    @commands.cooldown(8, 60, BucketType.user)
    async def animal(self, ctx, animal: str= None):
        animal= animal or choice(self.animals)
        if not animal.lower() in self.animals:
            await ctx.send('Animal not listed.')
            return
        with open('{}/data/animals.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..'))) as animals:
            anim_dict= json.load(animals)
            anim_dict= choice(anim_dict[animal])# Same variable to save memory
            embed= discord.Embed(
                title= animal.capitalize(),
                color= discord.Color.blurple(),
            )
            embed.set_image(url= anim_dict)
            await ctx.send(embed=embed)
    @animal.command(name= 'list')
    async def _list_(self, ctx):
        desc= " **|** ".join(self.animals)
        emb= discord.Embed(title= "List of animals u can request image for.", description= desc, color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        await ctx.send(embed= emb)

    @commands.group(
        aliases= ['tra'], invoke_without_command=True,
        help="Use 2 letter language code to translate the text to ur language.",
        description="Do .translate list to see the list of available languages with there code.")
    @commands.cooldown(10, 60, BucketType.user)
    async def translate(self, ctx, lang: str= 'en', *, text= None):
        lang= lang.lower()
        if not lang in self.langs.keys():
            if lang.capitalize() in self.langs.values():
                for lan in self.langs.keys():
                    if self.langs[lan] == lang.capitalize():
                        lang= lan
                        break
            else:
                text= lang + ' ' + text if text else ''
                lang= 'en'
        if not text:
            return await ctx.send('What to translate? huh!')
        async with aiohttp.ClientSession() as cs:
            async with cs.post(
                url= f'https://translate.googleapis.com/translate_a/single?client=gtx&ie=UTF-8&oe=UTF-8&sl=auto&tl={lang}&dt=t&q={text}') as response:
                response= await response.json()
                trans= response[0][0][0]
                embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
                embed.add_field(name= 'Detect Language', value= self.langs[response[2]], inline= False)
                embed.add_field(name= f'{self.langs[lang]} Translation', value= trans)
                await ctx.send(embed= embed)
    @translate.command(name= 'list')
    async def _list(self, ctx):
        fields= []
        for i in range(0,len(self.langs), 2):
            lang= list(self.langs.keys())[i]
            try:
                lang2= list(self.langs.keys())[i+1]
            except:
                lang2= None
            fields.append('{:<30}{:<18}'.format(f'[{lang2}]({self.langs[lang2]})' if lang2 else '',f'[{lang}]({self.langs[lang]})'))
        fields= [field.strip() for field in fields]
        desc= '\n'.join(fields)
        embed= discord.Embed(
            title= 'List of languages can be used while translating!',
            description= '```md\n'+desc+'```',
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color
        )
        await ctx.send(embed= embed)

    @commands.command(
        aliases= ['txtart', 'ascii'],
        help="Converts the given text to a teact art.",
        description="I smell some copypastas.")
    async def textart(self, ctx, *, text:str):
        if len(text) > 15:
            await ctx.send("You can't convert more then 15 letters to an ASCII art. Sorry abt that but its for preventing wall of message.")
            return
        text= text.replace(' ', '\n')
        art= text2art(text, font= 'rnd-medium', chr_ignore= True)
        await ctx.send(f'```fix\n{art}\n```')

    @commands.command(
        aliases= ['ttt', 'tic'],
        help="Mention the user or Give there user id or there nick name or user#discrim to challenge ur friend.",
        description="Starts a tictaktoe came against ur friend.")
    async def tictaktoe(self, ctx, *, member2: discord.Member):
        if member2.bot:
            await ctx.send("U can't challenge a bot huh.")
            return
        if member2.id == ctx.author.id:
            return await ctx.send('U can\'t challenge yourself.')
        member1= ctx.author
        msg : discord.Message= await ctx.send(f'{member2.mention}, tictaktoe challenge for u from {member1.mention}.')
        await msg.add_reaction('<:check:857494064294264862>')
        await msg.add_reaction('<:uncheck:857494289415798784>')
        def check(r, u):
            return u.id==member2.id and str(r.emoji) in ['<:check:857494064294264862>','<:uncheck:857494289415798784>'] and r.message == msg

        try:
            r, m= await self.client.wait_for('reaction_add', timeout= 60, check= check)
            if str(r.emoji)== '<:uncheck:857494289415798784>':
                await msg.edit(f'{ctx.author.mention}, They denied your request!')
                return
        except asyncio.TimeoutError:
            await ctx.send(":x: Game Canceled.")
            return

        players= (member1, member2)
        theBoard= {'1': ' ' , '2': ' ' , '3': ' ' ,
                    '4': ' ' , '5': ' ' , '6': ' ' ,
                    '7': ' ' , '8': ' ' , '9': ' ' }
        board_keys= []
        for key in theBoard:
            board_keys.append(key)

        def printBoard(board : dict):
            for i in board.keys():
                if board[i] == ' ':
                    board.update({i : i})
            realb= board['1'] + ' | ' + board['2'] + ' | ' + board['3'] + '\n--+---+-- \n' + board['4'] + ' | ' + board['5'] + ' | ' + board['6'] + '\n--+---+-- \n' + board['7'] + ' | ' + board['8'] + ' | ' + board['9']
            return discord.Embed(description= f'```ml\n{realb}```').set_footer(text= 'Send `q` to quit.')
        
        boardmsg= await ctx.send(embed= printBoard(theBoard))
        turnmsg= await ctx.send("Starting...")

        async def game():

            turn= 'X'
            count= 0


            while count < 10:
                player= players[count%2]
                await boardmsg.edit(embed= printBoard(theBoard))
                await turnmsg.edit(content= f"It is {player.mention}'s turn.")

                move= '0'

                for i in range(1,4):
                    try:
                        movemsg= await self.client.wait_for(
                            'message', timeout= 30, check= lambda m: m.author.id == player.id and m.channel.id == ctx.channel.id)
                    except asyncio.TimeoutError:
                        await turnmsg.edit(content= "Alrigth! I have other things to do too. :wave:")
                        return
                    move= movemsg.content
                    try:
                        await movemsg.delete()
                    except:
                        pass
                    if move.lower() == 'q': return await ctx.send(f'Gameover! **{movemsg.author}** quited')
                    if not move in theBoard.keys() or theBoard[move] in ['X', 'O']:
                        await ctx.send("Invalid input try again, enter the number of the box u wanna place ur turn.", delete_after= 5)
                        move= '0'
                        continue
                    break
                if move == '0':
                    print("Game Over. 3 invalid inputs!")
                    return
                theBoard[move]= turn
                count += 1

                if count >= 5:
                    if theBoard['7'] == theBoard['8'] == theBoard['9'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['4'] == theBoard['5'] == theBoard['6'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['1'] == theBoard['2'] == theBoard['3'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['1'] == theBoard['4'] == theBoard['7'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['2'] == theBoard['5'] == theBoard['8'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['3'] == theBoard['6'] == theBoard['9'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['7'] == theBoard['5'] == theBoard['3'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['1'] == theBoard['5'] == theBoard['9'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return

                if count == 9:
                    await ctx.send("\nGame Over!!\nIt's a Tie oof.")
                    return

                if turn == 'X':
                    turn= 'O'
                else:
                    turn= 'X'

        await game()

    @commands.command(
        aliases= ['echo'],
        help="Just a plane text.",
        description="Just copy paste what u pass.")
    async def say(self, ctx, *, statement):
        if len(statement)> 1000:
            await ctx.send('I m lazy to type that much, sorry...')
            return
        await ctx.send(statement, allowed_mentions= discord.AllowedMentions(everyone= False, users= False, roles= False))
        try:
            await ctx.message.add_reaction('✅')
        except:
            pass

    @commands.command(
        aliases= ['aki'],
        help='Thonk of a character, I will try to guess it by questioning u. The answer must be one of these:\n\t- "yes" OR "y" OR "0" for YES\n\t- "no" OR "n" OR "1" for NO\n\t- "i" OR "idk" OR "i dont know" OR "i don\'t know" OR "2" for I DON\'T KNOW\n\t- "probably" OR "p" OR "3" for PROBABLY\n\t- "probably not" OR "pn" OR "4" for PROBABLY NOT\n\t- "b" OR "back" OR "5" to go back.\n\t- "c" OR "cancel" OR "6" to cancel.',
        description="Starts an Akinator game.")
    @commands.cooldown(1, 60, BucketType.user)
    async def akinator(self, ctx):
        aki= Akinator()
        msg= await ctx.send('Thonk of a character, I will try to guess it by questioning u. The answer must be one of these:\n\t- "yes" OR "y" OR "0" for YES\n\t- "no" OR "n" OR "1" for NO\n\t- "i" OR "idk" OR "i dont know" OR "i don\'t know" OR "2" for I DON\'T KNOW\n\t- "probably" OR "p" OR "3" for PROBABLY\n\t- "probably not" OR "pn" OR "4" for PROBABLY NOT\n\t- "b" OR "back" OR "5" to go back.\n\t- "c" OR "cancel" OR "6" to cancel.')
        await msg.add_reaction('👌')
        def check(r, u):
            return str(r.emoji) == '👌' and u.id== ctx.author.id and r.message == msg
        def anscheck(m):
            return str(m.content.lower()) in ["yes", "y", "0", "no", "n", "1", "i", "idk", "i dont know", "i don't know", "2", "probably", "p", "3", "probably not", "pn", "4", "back", "b", "5", "cancel", "c", "6"]
        try:
            await self.client.wait_for('reaction_add', timeout= 5, check= check)
        except asyncio.TimeoutError:
            pass
        quesno= 1
        ques= await aki.start_game()
        lastmsg= ctx.message

        while aki.progression <= 80:
            embed= discord.Embed(description= f'`{quesno}.` {ques}', color= discord.Color.blue())
            embed.set_footer(text= '"c" OR "cancel" OR "6" to cancel.')
            embed.set_author(icon_url= "https://static.wikia.nocookie.net/video-game-character-database/images/9/9f/Akinator.png/revision/latest/top-crop/width/360/height/450?cb=20200817020737", name= 'Akinator!')
            await lastmsg.reply(embed= embed)
            try:
                lastmsg= await self.client.wait_for('message', timeout= 45, check= anscheck)
            except asyncio.TimeoutError:
                await ctx.send(':x: Canceled akinator game.')
                return
            if lastmsg.content in ["cancel", "c", "6"]:
                await ctx.send(":x: Cancelled Akinator game. Thanks for playing.")
                return
            elif lastmsg.content in ["back", "b", "5"]:
                try:
                    q= await aki.back()
                    continue
                except:
                    await ctx.send("Can't go back at this point, sorry!")
                    continue
            ques= await aki.answer(lastmsg.content)
            if quesno > 39:
                await ctx.send("Akinator: Limit of 40 questions reached. Here is my guess so far.")
                break
            quesno+= 1
        await aki.win()

        endembed= discord.Embed(title= aki.first_guess['name'], description= aki.first_guess['description'], color= discord.Color.blue())
        endembed.set_thumbnail(url= aki.first_guess['absolute_picture_path'])
        endembed.set_footer(text= f"I'm {round(float(aki.first_guess['proba'])*100, 1)}% sure.")
        endembed.set_author(icon_url= ctx.author.avatar_url, name= ctx.author)
        await ctx.send(embed= endembed)

    @commands.command(
        aliases=['math'],
        help="Evaluate a mathematical expression.",
        description="Basic functions: + - / * % ^\nAdvanced: `sin()` `cos()` `tan()` `log(a,b)` `asin()` `acos()` `atan()` `floor()` `round()` `abs()` `exp()`")
    async def solve(self, ctx, *, expression: str):
        embed= discord.Embed(
                color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color
            )
        try:
            eq= Parser().parse(expression)
            val= eq.toString()
            if isinstance(val, str):
                val= val.replace('(', ' ( ').replace(')', ' ) ')
            embed.add_field(name= 'Expression', value= val, inline= False)
            if not eq.variables():
                answer= eq.evaluate({})
                embed.add_field(name= 'Evaluation', value= f'```py\n{round(float(answer), 6)}```', inline= False)
            else:
                answer= eq.simplify({})
                embed.add_field(name= 'Simplification', value= f'```py\n{answer}```', inline= False)
        except Exception as error:
            if isinstance(error, ZeroDivisionError):
                embed.add_field(name= '∞', value= u'\u200b')
            elif isinstance(error, OverflowError):
                return await ctx.send('That\'s some big homewok out there. Good luck doing it alone.')
            elif isinstance(error, Exception):
                embed.add_field(name= 'Error', value= f"```asciidoc\n{error.__class__.__name__} :: '{error.args[0]}'```")
        await ctx.send(embed= embed)

    @commands.command(
        aliases=['hug', 'ship'],
        help="User parameter must be mention/user#discrim/usernick/userid",
        description="Sends a image, ur pfp overlayed over the member's pfp.")
    @commands.cooldown(4, 60, BucketType.user)
    async def cuddle(self, ctx, *, member: discord.User):
        await ctx.channel.trigger_typing()
        pfp1= Image.open(BytesIO(await member.avatar_url_as(format= 'png').read())).convert('RGBA')
        pfp2= Image.open(BytesIO(await ctx.author.avatar_url_as(format= 'png').read())).convert('RGBA')
        async def changeImageSize(maxWidth, maxHeight, image):
            widthRatio  = maxWidth/image.size[0]
            heightRatio = maxHeight/image.size[1]
            newWidth    = int(widthRatio*image.size[0])
            newHeight   = int(heightRatio*image.size[1])
            newImage    = image.resize((newWidth, newHeight))
            return newImage
        pfp1= await changeImageSize(512,512, pfp1)
        pfp2= await changeImageSize(512,512, pfp2)
        pfp1= ImageChops.multiply(pfp1, pfp2)
        pfp2.alpha_composite(pfp1)
        pfp= BytesIO()
        pfp2.save(pfp, 'PNG')
        pfp.seek(0)
        ship= f'{ctx.author.display_name[:-int(len(ctx.author.display_name)/2)]}{member.display_name[int(len(member.display_name)/2):]}'
        await ctx.send(f"**{ctx.author}** gave a sweet hug to **{member}**. As a result **{ship}** was formed!!!",file= discord.File(pfp, 'Blessed-With-Hug.png'))

    @commands.command(aliases= ['wiki'],
        help= 'Pass the argument u want to search in wikipedia',
        description= 'You may get unexpected results, pls keep your query short and sweet.')
    @commands.cooldown(2, 30, BucketType.user)
    async def wikipedia(self, ctx, *, query: str):
        await ctx.channel.trigger_typing()
        if len(query)> 20:
            await ctx.send('Query too long.. Pls only pass query below 20 letters.')
            return
        try:
            result= wikipedia.summary(query, chars= 1000)
        except Exception as error:
            if isinstance(error, wikipedia.DisambiguationError):
                try:
                    opts= error.options[0:10] if len(error.options) > 10 else error.options
                    dym= '\n'.join(opts)
                    embed= discord.Embed(title= 'Page not found!',
                        description= f'*Do you mean?*\n{dym}',
                        color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
                    embed.set_thumbnail(url= 'https://upload.wikimedia.org/wikipedia/commons/d/de/Wikipedia_Logo_1.0.png')
                    await ctx.send(embed= embed)
                    return
                except:
                    await ctx.send('Error occured! failed to find any wiki page related to that.')
                    return
            else:
                await ctx.send('If you are seeing this, this error should hardly occur, pls report this in the support server so i can fix it.')
            return
        embed= discord.Embed(
            title= query.capitalize(),
            description= f'{result}[Continue reading.](https://en.wikipedia.org/wiki/Special:Search?search={query.replace(" ", "%20")}&go=Go&ns0=1)',
            color= discord.Color.blue() if ctx.me.color == discord.Color.default() else ctx.me.color
        )
        embed.set_thumbnail(url= 'https://upload.wikimedia.org/wikipedia/commons/d/de/Wikipedia_Logo_1.0.png')
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)

    @commands.command(aliases= ['websnap', 'urlsnap', 'webss'],
        help= 'Sends a snapshot of a website as an embed, pass a crop value between 0-100 to make adjust the snap ratio.')
    @commands.cooldown(2, 60, BucketType.user)
    async def webshot(self, ctx, url: str, crop: int= 50):
        await ctx.channel.trigger_typing()
        if not crop in range(0,101):
            await ctx.send('Crop can only be an integer in range 0-100')
            return
        crop= 12*crop
        reg= r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
        if not re.match(reg, url):
            await ctx.send('Not a url, pls pass the full url.')
            return
        embed= discord.Embed(
            title= "Website snapshot",
            url= url,
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color
        )
        url= f'http://image.thum.io/get/png/noanimate/width/720/crop/{crop}/&{url}'
        img_bin= BytesIO()
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as response:
                img= Image.open(BytesIO(await response.content.read()))
                img.save(img_bin, 'PNG')
                img_bin.seek(0)
        img= discord.File(img_bin, 'WebSnap.png')
        embed.set_image(url= 'attachment://WebSnap.png')
        await ctx.send(embed= embed, file= img)

    @commands.command(aliases= ['gtn'], help= 'Guess the number bot is thinking of. Range can be any number between 20 and 1000.',
        usage= '[range]', description= '`range` defaults to 50 and User has 8 (or 12 if `range` > 500) chances to guess the number.')
    @commands.cooldown(3, 60, BucketType.user)
    async def guessTheNumber(self, ctx, _range: int= 50):
        if _range not in range(20,1001):
            _range= 50
        hints= 3
        number= randint(1, _range)
        guessedNo= None
        embed= discord.Embed(
            title= 'Guess The Number!',
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color,
            description= f'Guess the number between 1, {_range} I m thinking of. Type `hint` or `h` to get the hint. U got 3 hints'
        )
        def check(m):
            if m.content.isdigit() or m.content.lower() in ['h', 'hint']:
                return True if m.author.id == ctx.author.id and m.channel.id == ctx.channel.id else False
            else:
                return False
        await ctx.reply(mention_author= False, embed= embed)
        chances= 8 if _range< 500 else 12
        while chances !=0:
            try:
                msg: discord.Message= await self.client.wait_for('message', timeout= 30, check= check)
            except:
                return
            if msg.content.lower() in ['h', 'hint']:
                if guessedNo == None:
                    await ctx.send('U lost your one chance, asking for a "HINT" when before guessing a number')
                    chances-=1
                elif hints> 0:
                    await ctx.send(f'The number is __{"higher" if guessedNo < number else "lower"}__ then {guessedNo}\n`{hints-1}` hint{"s" if hints-1>1 else ""} left!')
                    hints-=1
                else:
                    await ctx.send('U haven\'t got any hints and now lost one chance..')
                    chances-=1
                continue
            if msg.content.isdigit():
                if int(msg.content) == number:
                    await msg.add_reaction('✅')
                    return
                else:
                    await msg.add_reaction('❌')
                guessedNo= int(msg.content)
                chances-=1
        await ctx.send(f'The number was `{number}`')

    @commands.command(name="8ball", aliases= ['8b'], help="Ask the 8-ball a question")
    async def eightball(self, ctx, *, question):
        answers= [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Is Trump's skin orange?",
            "Definitely",
            "Why don't you go ask your mom smh.",
            "What? No!",
            "Unscramble `esy`",
            "Doubtful...",
            "I'm lazy rn, don't want to answer it.",
            "Ok, no",
            "Possibly so!",
            "Yes. Yes. Yes."
        ]

        em= discord.Embed(
            title="Magic 8-ball",
            description=f"Question: {question}\n🎱: {choice(answers)}",
            colour=discord.Color.random(),
        )
        await ctx.send(embed=em)

    @commands.group(aliases= ['bin01', 'bin10'], help= 'Encode or Decode the provided integer, text and binary.', invoke_without_command=True)
    async def binary(self, ctx):
        await ctx.send_help(ctx.command)
    @binary.command(name= 'encode', aliases= ['enc'], help= 'Converts the text to binary. text can be a number too.')
    async def _encode(self, ctx, *, text: str):
        if len(text)> 100:
            return await ctx.send('Too long text failed to parse. Pass something below 100 letters.')
        text= ' '.join(format(ord(i), '08b') for i in text)
        await ctx.send(f'```{text}```')
    @binary.command(name= 'decode', aliases= ['dec'], help= 'Converts the binary code to text.')
    async def _decode(self, ctx, *, binary: str):
        def decode_binary_string(s):
            return ''.join(chr(int(s[i*8:i*8+8],2)) for i in range(len(s)//8))
        if not re.fullmatch(r'[01\s]{1,}', binary):
            return await ctx.send('Thats not how binary looks, its like `101000 1011110 1010101 001100 100100`')
        binary= binary.replace(' ', '')
        await ctx.send(f'```{decode_binary_string(binary)}```')

def setup(client):
    client.add_cog(Fun(client))

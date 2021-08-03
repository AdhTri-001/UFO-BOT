import discord
from discord.ext import commands
from PIL import Image, ImageFont, ImageDraw, ImageFilter, ImageChops, ImageOps, ImageEnhance
from UFO_Bot import Ufo_bot
from textwrap import wrap
from pilmoji import Pilmoji
from io import BytesIO
from datetime import datetime
import re, os
from numpy import asarray
from typing import Union
from wand.image import Image as wandImg
import math
from py_expression_eval import Parser
from numpy import arange, vectorize
import matplotlib.pyplot as plt
from random import random

plt.style.use('dark_background')
EMOJI_regex= re.compile('<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>')
PERCENT_regex= re.compile('(?:[1-9]|\d\d\d*)%')
CHANNEL_regex= re.compile('<#(\d{16,22})>')
ROLE_regex= re.compile('(<@&\d{16,22}>)')
MENTION_regex= re.compile('<@(?:!)?(\d{16,22})>')
ITALICS_regex= re.compile('((?:_[^_]+?_(?!\w)|$)|(?:\*[^\*]+?\*(?=(?:\*\*)+|[^\*]+|$)))')
BOLD_regex= re.compile('(\*\*.+?\*{2,})')
MD_regex= re.compile('(`[^`]+`)')
URL_regex= re.compile("(https?://\S\S+)")
MATH_regex= re.compile('([\d\)]x)')
MATH_GLOBALS= {
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'log': math.log,
    'floor': math.floor,
    'ceil': math.ceil,
    'exp': math.exp,
    'E': math.e,
    'PI': math.pi,
    'sqrt': math.sqrt,
    'sind': lambda x: math.sin(math.radians(x)),
    'cosd': lambda x: math.cos(math.radians(x)),
    'tand': lambda x: math.tan(math.radians(x)),
    'random': lambda x: random() * (x or 1),
    'fac': math.factorial,
    'asind': lambda x: math.asin(math.radians(x)),
    'acosd': lambda x: math.acos(math.radians(x)),
    'atand': lambda x: math.atan(math.radians(x))
}
DISC_fnt= ImageFont.truetype(f'{os.path.dirname(__file__)}/images/OpenSans-Light.ttf',28)
DISC_IT_fnt= ImageFont.truetype(f'{os.path.dirname(__file__)}/images/OpenSans-LightItalic.ttf',28)
DISC_BLD_fnt= ImageFont.truetype(f'{os.path.dirname(__file__)}/images/OpenSans-SemiBold.ttf',28)
DISC_BLD_IT_fnt= ImageFont.truetype(f'{os.path.dirname(__file__)}/images/OpenSans-SemiBoldItalic.ttf',28)
DISC_TS_fnt= ImageFont.truetype(f'{os.path.dirname(__file__)}/images/OpenSans-Light.ttf',20)
DISC_MONO_fnt= ImageFont.truetype(f'{os.path.dirname(__file__)}/images/Inconsolata-Medium.ttf', 30)
MC_fnt= ImageFont.truetype(f'{os.path.dirname(__file__)}/images/MC_font.otf', 30)

def flatten(matrix):
    result = []
    for el in matrix:
        if hasattr(el, "__iter__") and not isinstance(el, str):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result

class Images(commands.Cog):

    def __init__(self, client):
        super().__init__()
        self.client: Ufo_bot= client

    print("Fun.py has been loaded\n-----------------------------------")

    def dodge(self, front,back):
        result=back*256.0/(256.0-front) 
        result[result>255]=255
        result[front==255]=255
        return result.astype('uint8')

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
        aliases= ["snap"],
        help= "Make a fake discord message snap to troll ur friends.",
        description= "U may use user id/mention if u don't want member not found error. This command has the font and styling that android uses!")
    async def mimic(self, ctx: commands.Context, member: Union[discord.Member, discord.User, str]= None, *, message= None):
        if not member and not message: return await ctx.send('You haven\'t provided me any argument.')
        if isinstance(member, str):
            message= member + ' ' + (message if message else '')
            member= ctx.author
        if not message:
            return await ctx.send(f'No message was given to mimic for **{member}**')
        async with ctx.channel.typing():
            emojies= EMOJI_regex.findall(message)
            if len(emojies)>3:
                return await ctx.reply('More than three emojies failed to parse.')
            if len(message)>1000:
                await ctx.reply('This is not accepted, word limit is 1000 characters.')
                return
            mentions= MENTION_regex.findall(message)
            channel_mentions= CHANNEL_regex.findall(message)
            blurple_mentions= []
            for mention in mentions:
                newstr= ''
                for mem in ctx.message.mentions:
                    if int(mention) == mem.id:
                        newstr= f'@{mem.display_name}'
                        break
                blurple_mentions.append(newstr)
                message= message.replace(f'<@!{mention}>', newstr).replace(f'<@{mention}>', newstr)
            for mention in channel_mentions:
                newstr= ''
                for mem in ctx.message.channel_mentions:
                    if int(mention) == mem.id:
                        newstr= f'#{mem.name}'
                        break
                blurple_mentions.append(newstr)
                message= message.replace(f'<#{mention}>', newstr)
            if len(blurple_mentions)>6:
                await ctx.send('Not more than 6 mentions (both member and channel) per message.')
                return
            for emote in emojies:
                message= message.replace(f'<{":".join(emote)}>', f'<:e_:{emojies.index(emote)}>')
            lines= []
            for line in message.split('\n'):
                if len(line)>85:
                    for wrapped in wrap(line,85):
                        lines.append(wrapped)
                else:
                    lines.append(line)
            proplines= []
            for line in lines:
                for emote in emojies:
                    line= line.replace(f'<:e_:{emojies.index(emote)}>', f'<{":".join(emote)}>')
                proplines.append(line)
            img= Image.new('RGBA', (1200, 1200), color= (54,57,63))
            parser= Pilmoji(img)
            img_bin= BytesIO()
            if isinstance(member, discord.Member):
                uname= member.display_name
            else:
                uname= member.name
            if isinstance(member, discord.Member):
                parser.text((100, 13), uname, font= DISC_BLD_fnt, fill= member.color.to_rgb() if member.color.to_rgb() != (0,0,0) else (255,255,255))
            else:
                parser.text((100, 13), uname, font= DISC_BLD_fnt, fill= (255,255,255))
            h, w= parser.getsize(uname, font= DISC_BLD_fnt)
            titlelen= 300+h
            if len(proplines)==1:
                vert_crop= 110
            else:
                vert_crop= 125+(32*len(proplines[2:]))
            time= datetime.utcnow().strftime("Today at %H:%M")
            parser.text((110+h, 20), time, font= DISC_TS_fnt, fill=(114, 118, 125))
            draw= ImageDraw.Draw(img)
            boxes= []
            italics= False
            bolded= False
            code_block= False
            i= 1
            for line in proplines:
                if line.strip():
                    nodes= BOLD_regex.split(line)
                    nodes= [ITALICS_regex.split(node) for node in nodes if node]
                    nodes= flatten(nodes)
                    nodes= [MD_regex.split(node) for node in nodes if node]
                    nodes= flatten(nodes)
                    nodes= [URL_regex.split(node) for node in nodes if node]
                    nodes= flatten(nodes)
                else:
                    nodes= [line]
                last_node_len= 0
                fnt= None
                for node in nodes:
                    boxes= []
                    pntnode= node
                    if node.startswith('**'):
                        bolded= not bolded
                        pntnode= pntnode[2:]
                        if node.endswith('**') and len(node)>4:
                            pntnode= pntnode[:-2]
                    elif (node.startswith('_') or (node.startswith('*') and not node.startswith('**'))):
                        italics= True
                        pntnode= pntnode[1:]
                        if node.endswith('_') or (node.endswith('*') and not node.endswith('**')):
                            pntnode= pntnode[:-1]
                    elif node.startswith('`') and node.endswith('`'):
                        code_block= True
                        pntnode= pntnode[1:-1]
                    if bolded and italics and not code_block:
                        fnt= DISC_BLD_IT_fnt
                    elif bolded and not italics and not code_block:
                        fnt= DISC_BLD_fnt
                    elif italics and not bolded and not code_block:
                        fnt= DISC_IT_fnt
                    elif code_block:
                        fnt= DISC_MONO_fnt
                        temp_width= parser.getsize(pntnode, font= fnt)[0]
                        code_box= (last_node_len+100, 28+(32*i), temp_width+last_node_len+100, 60+(32*i))
                        draw.rectangle(code_box, (40,40,40))
                    else:
                        fnt= DISC_fnt
                    if blurple_mentions:
                        for mention in blurple_mentions:
                            subnodes= pntnode.split(mention)
                            if len(subnodes) == 1:
                                continue
                            box= []
                            hmen,wmen= parser.getsize(mention.replace('\u200b', ''), font= fnt)
                            for subnode in subnodes[::2]:
                                h,w= parser.getsize(subnode, font= fnt)
                                box.append(100+last_node_len+h)
                                box.append(32+(32*i))
                                box.append(102+last_node_len+h+hmen)
                                box.append(32+(32*i)+wmen)
                                boxes.append(tuple(box))
                                box=[]
                            pntnode= pntnode.replace(mention, mention.replace('\u200b', ''))
                    if boxes:
                        for box in boxes:
                            draw.rounded_rectangle(box, 5, (80, 105, 191, 190))
                    if pntnode:
                        parser.text((100+last_node_len, 24+(32*i)),
                            pntnode,
                            font= fnt, fill= (255,255,255) if not URL_regex.match(node) else (88, 152, 196),
                            stroke_fill= (255,255,255), stroke_width= 1 if bolded else 0)
                    if node.endswith('**') and len(node)>4:
                        bolded= False
                    elif node.endswith('_') or (node.endswith('*') and not node.endswith('**')):
                        italics= False
                    elif node.startswith('`') and node.endswith('`'):
                        code_block= False
                    last_node_len+= parser.getsize(pntnode, font= fnt)[0]
                if titlelen< last_node_len+100:
                    titlelen= last_node_len+115
                i+=1
            f2= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 64).read())).convert('RGBA')
            mask= Image.new("L", f2.size, 0)
            draw= ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 65, 65), fill=255)
            tempf2= f2.copy()
            tempf2.putalpha(mask)
            f2.paste(tempf2, mask= f2)
            f2.thumbnail((64,64), Image.ANTIALIAS)
            img.paste(f2, (20, 20), f2)
            img= img.crop((0, 0, titlelen, vert_crop))
            img.save(img_bin, 'PNG')
            img_bin.seek(0)
            file= discord.File(img_bin, f'BULLY.png')
            await ctx.reply(file=file)

    @commands.command(aliases= ['blur'], help= 'Blurs a user\'s pfp. Make sure `amount` can only be in range 5,100')
    async def blurify(self, ctx, member: discord.User= None, amount: int= 50):
        member= member or ctx.author
        if not amount in range(5,101): return await ctx.reply('You can only choose between 5 and 100')
        img= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((512,512)).convert('RGBA')
        img= img.filter(ImageFilter.GaussianBlur(amount/20))
        img_store= BytesIO()
        img.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color
        )
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://blur.png')
        await ctx.reply(file= discord.File(img_store, filename= 'blur.png'), embed= embed)

    @commands.command(aliases= ['bnw', 'greyscale'], help= 'Converts your or mentioned users pfp to grey scale.')
    async def blacknwhite(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((512,512)).convert('L')
        img_store= BytesIO()
        img.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(
            color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color
        )
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://BnW.png')
        await ctx.reply(file= discord.File(img_store, 'BnW.png'), embed= embed)

    @commands.command(aliases= ['cyber'], help= 'This overlays member\'s pfp to a green binary image.')
    async def binaryfy(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((512,512)).convert('RGBA')
        bin_img= Image.open(f'{os.path.dirname(__file__)}/images/binary.png').convert('RGBA')
        img= ImageChops.multiply(img, bin_img)
        img_store= BytesIO()
        img.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://binaried.png')
        await ctx.reply(file= discord.File(img_store, 'binaried.png'), embed= embed)

    @commands.command(help= 'Let elon hold you up.')
    async def elonholds(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img= Image.open(f'{os.path.dirname(__file__)}/images/elonholds.png').convert('RGBA')
        pfp= Image.open(BytesIO(await member.avatar_url_as(format='png', size= 512).read())).convert('RGBA').resize((480,480)).rotate(15)
        img.paste(pfp, (90,115), pfp)
        img_store= BytesIO()
        img.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://ElonHolds.png')
        await ctx.reply(file= discord.File(img_store, 'ElonHolds.png'), embed= embed)

    @commands.command(aliases= ['astro'], help= 'Have a chance to be an astronaut.')
    async def astronaut(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img= Image.open(f'{os.path.dirname(__file__)}/images/astro.png')
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 256).read())).convert('RGBA').resize((360,360))
        mask= Image.new("L", pfp.size, 0)
        draw= ImageDraw.Draw(mask)
        draw.ellipse((0, 0, pfp.size[0], pfp.size[1]), fill=255)
        temppfp= pfp.copy()
        temppfp.putalpha(mask)
        pfp.paste(temppfp, mask= pfp)
        img.paste(pfp, (98,110), pfp)
        img_store= BytesIO()
        img.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Astro.png')
        await ctx.reply(file= discord.File(img_store, 'Astro.png'), embed= embed)

    @commands.command(aliases= ['skch'], help= 'Makes a sketch out of your pfp. Results may be bad sometimes.')
    async def sketch(self, ctx, member: discord.User= None):
        member= member or ctx.author
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((512,512)).convert('L')
        inv_img= ImageOps.invert(pfp).filter(ImageFilter.GaussianBlur(7))
        pfp, inv_img= asarray(ImageEnhance.Brightness(pfp).enhance(0.8)), asarray(inv_img)
        inv_img= Image.fromarray(self.dodge(inv_img, pfp), 'L')
        img_store= BytesIO()
        inv_img.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Sketch.png')
        await ctx.reply(file= discord.File(img_store, 'Sketch.png'), embed= embed)

    @commands.command(aliases= ['sus'], help= 'Makes you suspect.')
    async def imposter(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img= Image.open(f'{os.path.dirname(__file__)}/images/sus.png').convert('RGBA')
        imghel= Image.open(f'{os.path.dirname(__file__)}/images/sushel.png').convert('RGBA')
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 256).read())).resize((240,240)).convert('RGBA')
        bg= Image.new('RGBA', img.size, 255)
        bg.paste(pfp, (240,70))
        bg.alpha_composite(img)
        bg.alpha_composite(imghel)
        img_store= BytesIO()
        bg.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Sus.png')
        await ctx.reply(file= discord.File(img_store, 'Sus.png'), embed= embed)

    @commands.command(aliases= ['rain'], help= 'Overlays a rainbow over your pfp.')
    async def rainbow(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img= Image.open(f'{os.path.dirname(__file__)}/images/rainbow.png').resize((512,512)).convert('RGBA')
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((512,512)).convert('LA')
        img= ImageChops.multiply(img, pfp.convert('RGBA'))
        img_store= BytesIO()
        img.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Rainbow.png')
        await ctx.reply(file= discord.File(img_store, 'Rainbow.png'), embed= embed)

    @commands.command(aliases= ['pixelate'], help= 'Pixelate your pfp.')
    async def pixel(self, ctx, member: discord.User= None):
        member= member or ctx.author
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((32,32), Image.BILINEAR).resize((512,512), Image.NEAREST).convert('RGBA')
        img_store= BytesIO()
        pfp.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Pixeled.png')
        await ctx.reply(file= discord.File(img_store, 'Pixeled.png'), embed= embed)

    @commands.command(help= 'Old hand shake meme generator. Pass two sentences split but comma.', usage= '"<text1>" <text2>')
    async def handshake(self, ctx, text1: Union[discord.User, str], *, text2: Union[discord.User, str]):
        text1= str(text1)
        text2= str(text2)
        message= text1+text2
        emojies= EMOJI_regex.findall(message)
        if len(emojies)>2:
            return await ctx.reply('More than two emojies failed to parse.')
        if len(message)>1000:
            await ctx.reply('This is not accepted, word limit is 1000 characters.')
            return
        for emote in emojies:
            text1= text1.replace(f'<{":".join(emote)}>', f'<:e_:{emojies.index(emote)}>')
            text2= text2.replace(f'<{":".join(emote)}>', f'<:e_:{emojies.index(emote)}>')
        img= Image.open(f'{os.path.dirname(__file__)}/images/handshake.png')
        parser= Pilmoji(img)
        h, w= parser.getsize('Test', font= DISC_fnt)
        lines= wrap(text1, 25, replace_whitespace=False)
        proplines= []
        for line in lines:
            for emote in emojies:
                line= line.replace(f'<:e_:{emojies.index(emote)}>', f'<{":".join(emote)}>')
            proplines.append(line)
        for line in proplines:
            parser.text((10, 125+(w*(proplines.index(line)+1))), line, font= DISC_fnt, fill=(255,255,255), stroke_width= 2, stroke_fill= 0)
        lines= wrap(text2, 20, replace_whitespace=False)
        proplines= []
        for line in lines:
            for emote in emojies:
                line= line.replace(f'<:e_:{emojies.index(emote)}>', f'<{":".join(emote)}>')
            proplines.append(line)
        for line in proplines:
            parser.text((270, 220+(w*(proplines.index(line)+1))), line, font= DISC_fnt, fill=(0,0,0), stroke_width= 2, stroke_fill= (255,255,255))
        img_store= BytesIO()
        img.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= '🤝')
        embed.set_image(url= 'attachment://Pixeled.png')
        await ctx.reply(file= discord.File(img_store, 'Pixeled.png'), embed= embed)

    @commands.command(help= 'Bonks your pfp.')
    async def bonk(self, ctx, member: discord.User= None):
        member= member or ctx.author
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 256).read())).resize((256,256)).convert('RGBA')
        bonkers= []
        pfps= []
        for i in range(1,4):
            if i-1:
                pfps.append(pfp.resize((256, 256-75*(i-1))))
            else:
                pfps.append(pfp)
            bonkers.append(Image.open(f'{os.path.dirname(__file__)}/images/B{i}.png').convert('RGBA'))
        frames= []
        bg= Image.new('RGBA', (720,480), (0,0,0,0))
        bgtemp= bg.copy()
        for i in range(0,3):
            bg.paste(pfps[i], (420, 224+(75*i)))
            bg.alpha_composite(bonkers[i], (0,75))
            frames.append(bg)
            bg= bgtemp.copy()
        img_store= BytesIO()
        frames[0].save(img_store, 'GIF', save_all=True, transparency=0, append_images= frames[1:]+frames[::-1], loop= 4, duration= 1)
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Bonk.exe.gif')
        await ctx.reply(file= discord.File(img_store, 'Bonk.exe.gif'), embed= embed)

    @commands.command(help= 'Resize your image, pass the size argument as `percentage` or `number[16-1024]`',
        description= 'Can be used like `resize 512` with reply to resize first attachment or without reply to resize ur pfp. You can also mention someone `resize @user 512 1024` or like `resize @user 512` or simply `resize 512 1024`')
    async def resize(self, ctx, target: Union[discord.User, int, str]= None, width: Union[int, str]= None, height: Union[int, str]= None):
        if not target and not width and not height:
            return await ctx.send_help()
        if not (isinstance(target, str) or isinstance(target, int)) and not width:
            return await ctx.send('`width` and `height` wasn\'t provided.')
        elif not (isinstance(target, str) or isinstance(target, int)) and width:
            img= Image.open(BytesIO(await target.avatar_url_as(format= 'png', size= 512).read()))
        elif (isinstance(target, str) or isinstance(target, int)):
            if ctx.message.attachments:
                attach: discord.Attachment= ctx.message.attachments[0]
            elif ctx.message.reference:
                msg= ctx.message.reference.resolved
                if msg.attachments:
                    attach: discord.Attachment= msg.attachments[0]
                else:
                    return await ctx.send('You need to attach/reply to the attachment message and tell me size in `percentage` or `number[16-1024]` to let me resize it.')
            else:
                attach= None
                img= Image.open(BytesIO(await ctx.author.avatar_url_as(format= 'png', size= 512).read()))
            if attach:
                if not attach.content_type.split('/')[1] in ['png','jpg'] or attach.size> 4096000:
                        return await ctx.send('You need to attach/reply to the attachment **(only png and jpeg)(not more than `4MB`)** message and tell me size in `percentage` or `number[16-1024]` to let me resize it.')
                img= Image.open(BytesIO(await attach.read()))
        if isinstance(target, str) or isinstance(target, int):
            width, height= target, width
        if width and height:
            if isinstance(height, int) and isinstance(width, int):
                ratio= (width, height)
            elif isinstance(height, str) and isinstance(width, str):
                if PERCENT_regex.fullmatch(height) and PERCENT_regex.fullmatch(width):
                    ratio= (img.size[0]*int(width[:-1])//100, img.size[1]*int(height[:-1])//100)
                else:
                    return await ctx.send('Failed to parse the ratio, for percentages do like `40%` or `400%`')
            else:
                return await ctx.send('Failed to parse command!')
        elif width and not height:
            if isinstance(width, int):
                ratio= (width, width)
            elif isinstance(width, str):
                if PERCENT_regex.fullmatch(width):
                    ratio= (img.size[0]*int(width[:-1])//100, img.size[1]*int(width[:-1])//100)
                else:
                    return await ctx.send('Failed to parse the ratio, for percentages do like `40%` or `400%`')
            else:
                return await ctx.send('Failed to parse command!')
        for rat in ratio:
            if rat> 1024 or rat< 16:
                return await ctx.send('File pixels should not exceed 1024 pixs and should be more than 16 pixs')
        img= img.resize(ratio)
        img_store= BytesIO()
        img.save(img_store, 'PNG')
        img_store.seek(0)
        await ctx.reply(file= discord.File(img_store, 'Resized.png'))

    @commands.command(help= 'Swirls your pfp according to the given `amount`')
    async def swirl(self, ctx, member: Union[discord.User, int]= None, amount: int= 90):
        if isinstance(member, int):
            amount= member
            member= ctx.author
        elif not member:
            member= ctx.author
        amount= math.fmod(amount, 360)
        img_store= BytesIO()
        with wandImg(blob= BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())) as img:
            img.resize(512, 512)
            img.swirl(amount, 'blend')
            img.save(img_store)
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Swirled.png')
        await ctx.reply(file= discord.File(img_store, 'Swirled.png'), embed= embed)

    @commands.command(aliases= ['coal'], help= 'Gives a charcoal version of your pfp.')
    async def charcoal(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img_store= BytesIO()
        with wandImg(blob= BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())) as img:
            img.resize(512, 512)
            img.charcoal(6,1)
            img.save(img_store)
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Swirled.png')
        await ctx.reply(file= discord.File(img_store, 'Swirled.png'), embed= embed)

    @commands.command(aliases= ['oil'], help= 'Give the oilpainted version of your pfp.')
    async def oilpaint(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img_store= BytesIO()
        with wandImg(blob= BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())) as img:
            img.resize(512, 512)
            img.oil_paint(9, 0)
            img.save(img_store)
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Oiled.png')
        await ctx.reply(file= discord.File(img_store, 'Oiled.png'), embed= embed)

    @commands.command(help= 'Wavify your image.')
    async def wave(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img_store= BytesIO()
        with wandImg(blob= BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())) as img:
            img.resize(512, 512)
            img.wave(15,15,'blend')
            img.save(img_store)
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Wave.png')
        await ctx.reply(file= discord.File(img_store, 'Wave.png'), embed= embed)

    @commands.command(help= 'Sends a image which mimics clyde')
    async def clyde(self, ctx, *, text):
        if len(text) > 1500:
            return await ctx.send('Too long text. Pls try not more than `1500` letters.')
        img= Image.open(f'{os.path.dirname(__file__)}/images/clyde.png').convert('RGB')
        draw= ImageDraw.Draw(img)
        lines= []
        for line in text.split('\n'):
            if len(line)>75:
                for wrapped in wrap(line,75):
                    lines.append(wrapped)
            else:
                lines.append(line)
        font= f'{os.path.dirname(__file__)}/images/whitneymedium.otf'
        font= ImageFont.truetype(font, 22)
        for line in lines:
            draw.text((115,75+lines.index(line)*22), line, (225, 232, 252), font= font)
        cut_width= len(lines)*22+120
        bg= Image.new('RGB',(img.size[0], cut_width), color= 0)
        bg.paste(img.crop((0,0,img.size[0], cut_width)),(0,0))
        bg.paste(img.crop((0,1100,img.size[0],1135)),(0,cut_width-35))
        img_store= BytesIO()
        bg.save(img_store, 'PNG')
        img_store.seek(0)
        await ctx.reply(file= discord.File(img_store, 'Clyde.png'))

    @commands.command(help= 'Lock someone at the jail.')
    async def jail(self, ctx, member: discord.User= None):
        member= member or ctx.author
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((512,512)).convert('RGBA')
        img= Image.open(f'{os.path.dirname(__file__)}/images/jail.png').convert('RGBA')
        pfp.alpha_composite(img)
        img_store= BytesIO()
        pfp.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Jailer.png')
        await ctx.reply(file= discord.File(img_store, 'Jailer.png'), embed= embed)

    @commands.command(help= 'Waste your life and start again from `Pillbox Hill Medical Center`')
    async def wasted(self, ctx, member: discord.User= None):
        member= member or ctx.author
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((512,512)).convert('RGBA')
        img= Image.open(f'{os.path.dirname(__file__)}/images/wasted.png').convert('RGBA')
        pfp_enc= ImageEnhance.Color(pfp)
        pfp= pfp_enc.enhance(0.3)
        pfp.alpha_composite(img, (0,206))
        img_store= BytesIO()
        pfp.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Wasted.png')
        await ctx.reply(file= discord.File(img_store, 'Wasted.png'), embed= embed)

    @commands.command(name= 'pong', help= 'Sends a fake ping image for the current server or mentioned user.')
    async def _pong(self, ctx, member: discord.User= None):
        if member:
            member= member.avatar_url_as(format= 'png', size= 512)
        else:
            member= ctx.guild.icon_url_as(format= 'png', size= 512)
        pfp= Image.open(BytesIO(await member.read())).resize((512,512)).convert('RGBA')
        img= Image.open(f'{os.path.dirname(__file__)}/images/ping.png').convert('RGBA')
        draw= ImageDraw.Draw(pfp)
        draw.ellipse((270,270,534,534), (0,0,0,0))
        pfp.alpha_composite(img.resize((220,220)), (292,292))
        img_store= BytesIO()
        pfp.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_image(url= 'attachment://Pong.png')
        await ctx.reply(file= discord.File(img_store, 'Pong.png'), embed= embed)

    @commands.command(help= 'Solarize your pfp.')
    async def solar(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img_store= BytesIO()
        with wandImg(blob= BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())) as img:
            img.resize(512, 512)
            img.solarize(1)
            img.save(img_store)
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Solar.png')
        await ctx.reply(file= discord.File(img_store, 'Solar.png'), embed= embed)

    @commands.command(name= 'Alpha', help= 'Make your pfp look a two colored alpha image.')
    async def _alpha(self, ctx, member: discord.User= None):
        member= member or ctx.author
        img_store= BytesIO()
        with wandImg(blob= BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())) as img:
            img.resize(512, 512)
            img.threshold(0.6)
            img.save(img_store)
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Solar.png')
        await ctx.reply(file= discord.File(img_store, 'Solar.png'), embed= embed)

    @commands.command(help= 'Gives a black and white toon shading to your pfp. Difference can be noticed in pfp clicked from real camera.')
    async def toon(self, ctx, member: discord.User= None):
        member= member or ctx.author
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((512,512)).convert('RGB')
        edges= pfp.convert('L')
        edges= edges.filter(ImageFilter.Kernel((3, 3), (-1, -1, -1, -1, 8, -1, -1, -1, -1), 0.5, 0))
        edges= ImageOps.invert(edges)
        pfp= pfp.quantize(85,2,5).convert('RGB')
        pfp= ImageEnhance.Brightness(pfp).enhance(1.3)
        pfp= ImageChops.multiply(pfp, edges.convert('RGB'))
        img_store= BytesIO()
        pfp.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Toon.png')
        await ctx.reply(file= discord.File(img_store, 'Toon.png'), embed= embed)

    @commands.command(name= 'plot', help= 'This command lets you plot graphs of mathematical equations. But there are some limitations',
        description= 'Basic functions: + - / * % ^\nAdvanced: `sin()` `cos()` `tan()` `log(x,base)` `asin()` `acos()` `atan()` `ceil()` `floor()` `round()` `abs()` `exp()`, `round()`')
    async def _plot(self, ctx, *, expression):
        expression= expression.replace(' ','').replace('\n','')
        matches = MATH_regex.findall(expression)
        for match in matches:
            expression= expression.replace(match, match.replace('x', '*x'))
        try:
            equation= Parser().parse(expression)
        except:
            return await ctx.send('Equation failed to parse. Please use only x as a variable.')
        if not equation.variables():
            return await ctx.send('There were no variables in the expression given.')
        elif len(equation.variables()) > 1 or not 'x' in equation.variables():
            return await ctx.send('There should be exactly 1 variable named `x`, found: `{}`'.format(', '.join(equation.variables())))
        expression= expression.replace('^', '**')
        x= arange(-40,40,0.1)
        try:
            idict= {}
            exec(f"def y(x):\n\ttry:\n\t\ttoret={expression}\n\t\treturn toret if not isinstance(toret, complex) or not toret.img else None\n\texcept: return None", MATH_GLOBALS, idict)
            y= vectorize(idict['y'])
        except:
            return await ctx.send('Expression was logically or mathematically incorrect.')
        fig, ax= plt.subplots()
        ax.plot(x, y(x), color= (0.447, 0.537, 0.854))
        ax.set_title('y={}'.format(expression))
        img_store= BytesIO()
        fig.savefig(img_store, format= 'png')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_image(url= 'attachment://Plot.png')
        await ctx.reply(file= discord.File(img_store, 'Plot.png'), embed= embed)

    @commands.command(name= 'rotate', help= 'Rotate ur pfp to the given degree.')
    async def _rot(self, ctx, member: Union[discord.User, int]= None, degree: int= 90):
        if isinstance(member, int) or member is None:
            degree= member or 90
            member= ctx.author
        degree= math.fmod(degree, 360)
        pfp= Image.open(BytesIO(await member.avatar_url_as(format= 'png', size= 512).read())).resize((512,512)).convert('RGBA')
        pfp= pfp.rotate(degree, fillcolor= (0,0,0,0), expand= True)
        img_store= BytesIO()
        pfp.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_author(name= str(member), icon_url= member.avatar_url)
        embed.set_image(url= 'attachment://Rotate.png')
        await ctx.reply(file= discord.File(img_store, 'Rotate.png'), embed= embed)

    @commands.command(name= 'minecraft', help= 'Throws u to the nostalgic respawn screen.')
    async def minecraft(self, ctx, *, text: str= None):
        if not text:
            text= f'{ctx.author} was too lazy to drop text here.'
        else:
            mentions= MENTION_regex.findall(text)
            if mentions:
                for mention in mentions:
                    newstr= ''
                    for mem in ctx.message.mentions:
                        if int(mention) == mem.id:
                            newstr= f'@{mem.display_name}'
                            break
                    text= text.replace(f'<@!{mention}>', newstr).replace(f'<@{mention}>', newstr)
        img= Image.open(f'{os.path.dirname(__file__)}/images/Minecraft.png') # 640, 245
        draw= ImageDraw.Draw(img)
        x= draw.textlength(text, font= MC_fnt)
        if x> 1220:
            return await ctx.send('Text was too long to fit in death screen.')
        draw.text(((1286-x)/2, 238), text, (75 ,75 ,75), MC_fnt)
        draw.text(((1280-x)/2, 235), text, (255,255,255), MC_fnt)
        img_store= BytesIO()
        img.save(img_store, 'PNG')
        img_store.seek(0)
        embed= discord.Embed(color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
        embed.set_image(url= 'attachment://Respawn.png')
        await ctx.reply(file= discord.File(img_store, 'Respawn.png'), embed= embed)

    # @commands.command(help= '')
    # async def puzzle(self, ctx, member: discord.User= None):
    #     member= member or ctx.author


def setup(client):
    client.add_cog(Images(client))
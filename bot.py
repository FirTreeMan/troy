import discord
import pygame
import requests
from dotenv import load_dotenv
from discord.ext import commands
from pygame import Surface, display, image, Rect, font, FONT_LEFT, FONT_RIGHT, FONT_CENTER
import datetime
import io
import os
import random

font.init()
display.init()
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
FONT = "Futura Condensed Extra Bold.otf"
KFONT = "gg sans Medium.woff"
with open('stop.txt', 'r') as file:
    STOPQUOTES = tuple(file.readlines())
with open('kill.txt', 'r') as file:
    KILLQUOTES = tuple(file.readlines())
with open('cat.txt', 'r') as file:
    CATQUOTES = tuple(file.readlines())
DISCORDBG = (49, 51, 56)
STRANGLERANGE = (5, 300)
STRANGLEMULT = 3
STRANGLEMAX = 10
CATMAX = len(CATQUOTES) - 1
stranglespam = {}
currmonth = -1
catspam = {}
open('losers.txt', 'a+').close()
with open('losers.txt', 'r') as file:
    losers = [s.rstrip('\n') for s in file.readlines()]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="troy please ", intents=intents)


def drawtext(surface: Surface, text, rect: Rect, color=(0, 0, 0), fontname=FONT, fontsize=80, aa=True,
             bkg=(255, 255, 255), align=FONT_LEFT):
    usedfont = font.Font(fontname, fontsize)
    usedfont.align = align

    while True:
        fontrect = usedfont.render(text, antialias=aa, color=color, bgcolor=bkg, wraplength=rect.width)
        if fontrect.get_height() <= rect.height:
            break
        fontsize -= 1
        usedfont = font.Font(fontname, fontsize)
        usedfont.align = align

    surface.blit(fontrect, rect.topleft)

    return fontrect


def surfsequal(surf1: Surface, surf2: Surface):
    if surf1.get_size() != surf2.get_size():
        return False
    for x in range(surf1.get_width()):
        for y in range(surf1.get_height()):
            if surf1.get_at((x, y)) != surf2.get_at((x, y)):
                return False
    return True


async def send(ctx, *args, **kwargs):
    if catspam.get(ctx.message.author.id, 0) // 5 >= CATMAX:
        item = discord.File("cat/" + random.choice(os.listdir('cat')))
        if val := kwargs.get('file', None):
            if isinstance(val, list):
                kwargs['file'] = val.append(item)
            else:
                kwargs['file'] = [val, item]
        else:
            kwargs['file'] = val

    await ctx.channel.send(*args, **kwargs)


@bot.event
async def on_ready():
    print(f'{bot.user.name} on')
    print()
    print(f"{'date': <40}{'name': <30}{'server': <30}{'message': <80}{'extra': <80}")
    print("-" * 260, end="")


@bot.event
async def on_message(message):
    if not message.attachments or message.author.id == message.guild.me.id:
        await bot.process_commands(message)
        return
    baseimg = image.load('cleantroy.png')
    for url in [s.url for s in message.attachments if s.content_type.startswith("image")]:
        img = image.load(io.BytesIO(requests.get(url).content), namehint="")
        if (size := img.get_size()) == baseimg.get_size() and \
                surfsequal(img.subsurface(0, 200, size[0], size[1] - 200),
                           baseimg.subsurface(0, 200, size[0], size[1] - 200)):
            await message.channel.send("hey thats me")
            await bot.process_commands(message)
            return
    await bot.process_commands(message)


@bot.before_invoke
async def start(ctx):
    global currmonth

    message = ctx.message
    print()
    print(f"{str(datetime.datetime.now()): <40}{message.guild.get_member(message.author.id).display_name: <30}"
          f"{message.guild.name: <30}{message.content: <80}", end="")
    if currmonth != (newmonth := datetime.datetime.now().month):
        currmonth = newmonth
        stranglespam.clear()
        catspam.clear()


@bot.command(name='live', help='checks for vitals')
async def live(ctx):
    await send(ctx, "iphone venezuela bottom texxt 100 billion dead")


@bot.command(name='make', help='prints a fresh troy')
async def make(ctx, verb: str = "spit yo shit", obj: str = "Troy", subj: str = "Troy"):
    imgsurf = image.load('cleantroy.png')
    surf = Surface(imgsurf.get_size(), pygame.SRCALPHA)
    surf.blit(imgsurf, (0, 0))
    verbrect = Rect(-2, -10, 363, 93)
    objrect = Rect(375, -10, 160, 93)
    subjrect = Rect(52, 85, 340, 93)

    drawtext(surf, verb, verbrect, align=FONT_CENTER)
    drawtext(surf, obj, objrect, align=FONT_LEFT)
    drawtext(surf, subj, subjrect, align=FONT_RIGHT)
    # pygame.draw.rect(surf, (255, 0, 0), verbrect, 2)
    # pygame.draw.rect(surf, (255, 0, 0), objrect, 2)
    # pygame.draw.rect(surf, (255, 0, 0), subjrect, 2)
    image.save(surf, 'make.png')

    await send(ctx, file=discord.File('make.png'))
    print('|'.join([verb, obj, subj]), end="")


@bot.command(name='stop', help='asks it to stop')
async def stop(ctx):
    await send(ctx, quote := random.choice(STOPQUOTES))
    print(quote, end="")


@bot.command(name='kill', help='something devious')
async def kill(ctx, user: discord.User = None):
    if user and user.id in (698596771059728455, 1127648163747086407):
        await send(ctx, "no thanks sweaty")
        print("invalid victim")
        return

    member = ctx.message.guild.get_member(user.id) if user else ctx.message.guild.get_member(int(ctx.message.author.id))

    quote = random.choice(KILLQUOTES)
    text = quote.replace("\\n", "\n")
    textbox = font.Font(KFONT, 48).render(text + "\n", antialias=True, color=(255, 255, 255), bgcolor=DISCORDBG,
                                          wraplength=2490)
    pfpbase = pygame.transform.scale(image.load(io.BytesIO(requests.get(member.avatar.with_size(512)).content),
                                                namehint=""), (120, 120))
    pfp = Surface(pfpbase.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(pfp, (255, 255, 255, 255), (0, 0, *pfpbase.get_size()))
    pfp.blit(pfpbase, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    name = member.display_name
    rolecolor = member.color.to_rgb()
    namebox = font.Font(KFONT, 48).render(name, antialias=True, color=rolecolor, bgcolor=DISCORDBG,
                                          wraplength=2490)
    time = (f"{random.randint(1, 12):02}/{random.randint(1, 30):02}/{random.randint(2020, 2023):04} "
            f"{random.randint(1, 12)}:{random.randint(1, 59):02} {random.choice(['AM', 'PM'])}")
    if str(ctx.message.guild.id) in losers:
        time = "11/14/1987 4:12 PM"
    timebox = font.Font(KFONT, 32).render(time, antialias=True, color=(148, 155, 164), bgcolor=DISCORDBG,
                                          wraplength=2490)

    surf = Surface((6 + pfp.get_width() + 33 + textbox.get_width(),
                    6 + namebox.get_height() + textbox.get_height()))
    surf.fill(DISCORDBG)
    surf.blit(pfp, (6, 6))
    surf.blit(namebox, (6 + pfp.get_width() + 33, 6))
    surf.blit(timebox, (6 + pfp.get_width() + 33 + namebox.get_width() + 18, 6 + 16))
    surf.blit(textbox, (surf.get_width() - textbox.get_width(), surf.get_height() - textbox.get_height()))
    # pygame.draw.rect(surf, (255, 0, 0), pfp.get_rect(), 2)
    # pygame.draw.rect(surf, (255, 0, 0), namebox.get_rect(), 2)
    # pygame.draw.rect(surf, (255, 0, 0), textbox.get_rect(), 2)

    image.save(surf, 'kill.png')

    await send(ctx, file=discord.File('kill.png'))
    print(quote[:30] + "...", end="")


@bot.command(name='censor', help='for admins to reduce mischief')
async def censor(ctx):
    global losers

    if not ctx.message.author.guild_permissions.manage_messages:
        await send(ctx, "you aren't a moderator silly")
        print("not a moderator", end="")
        return

    if (guildid := str(ctx.message.guild.id)) in losers:
        losers.remove(guildid)
        await send(ctx, "this server is no longer in the stinky pile")
        print("server uncensored", end="")
    else:
        losers.append(guildid)
        await send(ctx, "activated dumb loser mode")
        print("server censored", end="")
    with open('losers.txt', 'w') as f:
        f.writelines([s + "\n" for s in losers])


@bot.command(name='strangle', help='choke someone (and yourself)')
async def strangle(ctx):
    # await send(ctx, len([s for s in ctx.message.guild.members
    #                             if ctx.message.guild.me.top_role > s.top_role]))
    if str(ctx.message.guild.id) in losers:
        await send(ctx, "mods wont let me (1984 anyone?)")
        print("command censored", end="")
        return
    me = ctx.message.guild.me
    instigator = ctx.message.author
    victimchoices = [s for s in ctx.message.guild.members if ctx.message.guild.me.top_role > s.top_role]
    stranglespam[instigator.id] = stranglespam.get(instigator.id, 0) + 1
    if me.top_role <= instigator.top_role:
        await send(ctx, "you are too powerful... admin abuse...")
        print("instigator has higher role", end="")
        return
    if not victimchoices:
        await send(ctx, "there is nobody feeble enough here...")
        print("no valid victims", end="")
        return
    victim = random.choice(victimchoices)
    duration = datetime.timedelta(seconds=random.randrange(*STRANGLERANGE))
    instigatorduration = (duration * STRANGLEMULT ** stranglespam[instigator.id] *
                          (int(stranglespam.get(instigator.id, 0) > STRANGLEMAX) + 1))
    await victim.timeout(duration, reason=f'strangled on behalf of {instigator.mention}')
    await instigator.timeout(instigatorduration, reason=f'wanted to strangle')
    await send(ctx, f"strangled you and {victim.mention}")
    print(victim.display_name, duration, instigatorduration, end="")


@bot.command(name='cat', hidden=True)
async def cat(ctx):
    instigator = ctx.message.author
    spamcnt = catspam.get(instigator.id, 0) + 1
    quotient = spamcnt // 5
    if quotient >= CATMAX:
        await send(ctx, "im all out of cat juice...")
        print("limit reached", end="")
        return
    catspam[instigator.id] = spamcnt
    if spamcnt % 5 == 0:
        await send(ctx, CATQUOTES[quotient])
    await send(ctx, file=discord.File("cat/" + (attachment := random.choice(os.listdir('cat')))))
    print(spamcnt, attachment, end="")


bot.run(TOKEN)

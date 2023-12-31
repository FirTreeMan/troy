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
import pickle

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
STRANGLERANGE = (5, 600)
STRANGLEMULT = 3
STRANGLEMAX = 10
CATINTERVAL = 9
CATMAX = len(CATQUOTES) * CATINTERVAL
CATREGSPACE = 1
CATLOSERSPACE = 3
CATNAMES = tuple(os.listdir("cat"))
if not os.path.isfile("cat.pkl"):
    CATSEARCHTERMS = {frozenset(tag for tag in value.replace(", ", ".").split(".")): index
                      for index, value in enumerate(CATNAMES)}
    with open("cat.pkl", 'wb') as file:
        pickle.dump(CATSEARCHTERMS, file, 5)
else:
    with open("cat.pkl", 'rb') as file:
        CATSEARCHTERMS = pickle.load(file)
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


def searchweights(tags: set[str], terms: tuple[str]):
    tags = {tuple(s.split()) if isinstance(s, str) else s for s in tags}
    termset = set(terms)
    weight = 0
    checkedtitle = False
    for tag in tags:
        if not checkedtitle and tag[-1] == "!":
            if tag[:-1] == terms:
                print('TITLE FOUND')
                return 999
            checkedtitle = True
            continue
        tagset = set(tag)
        intersections = tagset & termset
        weight += len(intersections)
        if len(intersections) == len(tagset) > 1 and tag == terms:
            weight += len(tagset) * 0.1
        elif intersections:
            weight -= len(tagset) * 0.1
    return weight


async def send(ctx, *args, **kwargs):
    if kwargs.pop('forcecat', False) or \
            (not kwargs.pop('nocat', False) and catspam.get(ctx.message.author.id, 0) >= CATMAX):
        item = discord.File("cat/" + random.choice(CATNAMES))
        additions = [item]
        if kwargs.get('file', None):
            additions.insert(0, kwargs.pop('file'))
        kwargs['files'] = kwargs.get('files', []) + additions
    logdata = [logs] if not isinstance(logs := kwargs.pop('log', ''), list) else logs

    await ctx.channel.send(*args, **kwargs)
    await log(ctx, *logdata)


async def log(ctx, *extra):
    message = ctx.message
    nl = "\n"
    print(f"{str(datetime.datetime.now()): <40}{message.guild.get_member(message.author.id).display_name: <30}"
          f"{message.guild.name: <30}{message.content.replace(nl, ' '): <80}", end='')
    print(*extra)


def catcooldown(rate, per, specrate, specper, cooltype=commands.BucketType.default):
    cd = commands.Cooldown(rate, per)
    cdspec = commands.Cooldown(specrate, specper)

    def determine(ctx):
        return cdspec if catspam.get(ctx.message.author.id, 0) >= CATMAX else cd

    return commands.dynamic_cooldown(determine, cooltype)


cooldown = catcooldown(1, 1, 1, 60, commands.BucketType.user)


@bot.event
async def on_ready():
    print(f'{bot.user.name} on')
    print()
    print(f"{'date': <40}{'name': <30}{'server': <30}{'message': <80}{'extra': <80}")
    print("-" * 260)


@bot.event
async def on_message(message):
    if not message.attachments or message.author.id == message.guild.me.id:
        await bot.process_commands(message)
        return
    baseimg = image.load('cleantroy.png')
    for url in [s.url for s in message.attachments if s.content_type.startswith("image")]:
        img = image.load(io.BytesIO(requests.get(url).content), namehint='')
        if (size := img.get_size()) == baseimg.get_size() and \
                surfsequal(img.subsurface(0, 200, size[0], size[1] - 200),
                           baseimg.subsurface(0, 200, size[0], size[1] - 200)):
            await message.channel.send("hey thats me")
            await bot.process_commands(message)
            return
    await bot.process_commands(message)


# noinspection PyUnusedLocal
@bot.before_invoke
async def start(ctx):
    global currmonth

    if currmonth != (newmonth := datetime.datetime.now().month):
        currmonth = newmonth
        stranglespam.clear()
        catspam.clear()


@cooldown
@bot.command(name='live', help='checks for vitals')
async def live(ctx):
    await send(ctx, "iphone venezuela bottom texxt 100 billion dead")


@cooldown
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

    await send(ctx, file=discord.File('make.png'),
               log='|'.join([verb, obj, subj]))


@cooldown
@bot.command(name='stop', help='asks it to stop')
async def stop(ctx):
    await send(ctx, quote := random.choice(STOPQUOTES),
               log=quote)


@cooldown
@bot.command(name='kill', help='something devious')
async def kill(ctx, user: discord.User = None):
    if user and user.id in (698596771059728455, 1127648163747086407):
        await send(ctx, "no thanks sweaty",
                   log="invalid victim")
        return

    member = ctx.message.guild.get_member(user.id) if user else ctx.message.guild.get_member(int(ctx.message.author.id))

    quote = random.choice(KILLQUOTES)
    text = quote.replace("\\n", "\n")
    textbox = font.Font(KFONT, 48).render(text + "\n", antialias=True, color=(255, 255, 255), bgcolor=DISCORDBG,
                                          wraplength=2490)
    pfpbase = pygame.transform.scale(image.load(io.BytesIO(requests.get(member.avatar.with_size(512)).content),
                                                namehint=''), (120, 120))
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

    await send(ctx, file=discord.File('kill.png'),
               log=quote[:30] + "...")


@cooldown
@bot.command(name='censor', help='for admins to reduce mischief')
async def censor(ctx):
    global losers

    if not ctx.message.author.guild_permissions.manage_messages:
        await send(ctx, "you aren't a moderator silly",
                   log="not a moderator")
        return

    if (guildid := str(ctx.message.guild.id)) in losers:
        losers.remove(guildid)
        await send(ctx, "this server is no longer in the stinky pile",
                   log="server uncensored")
    else:
        losers.append(guildid)
        await send(ctx, "activated dumb loser mode",
                   log="server censored")
    with open('losers.txt', 'w') as f:
        f.writelines([s + "\n" for s in losers])


@cooldown
@bot.command(name='strangle', help='choke someone (and yourself)')
async def strangle(ctx):
    # await send(ctx, len([s for s in ctx.message.guild.members
    #                             if ctx.message.guild.me.top_role > s.top_role]))
    if str(ctx.message.guild.id) in losers:
        await send(ctx, "mods won't let me (1984 anyone?)",
                   log="command censored")
        return
    me = ctx.message.guild.me
    instigator = ctx.message.author
    victimchoices = [s for s in ctx.message.guild.members if ctx.message.guild.me.top_role > s.top_role]
    stranglespam[instigator.id] = stranglespam.get(instigator.id, 0) + 1
    if me.top_role <= instigator.top_role:
        await send(ctx, "you are too powerful... admin abuse...",
                   log="instigator has higher role")
        return
    if not victimchoices:
        await send(ctx, "there is nobody feeble enough here...",
                   log="no valid victims")
        return
    victim = random.choice(victimchoices)
    duration = datetime.timedelta(seconds=random.randrange(*STRANGLERANGE))
    instigatorduration = (duration * STRANGLEMULT * (stranglespam[instigator.id] - 1) *
                          (int(stranglespam.get(instigator.id, 0) > STRANGLEMAX) + 1))
    await victim.timeout(duration, reason=f'strangled on behalf of {instigator.mention}')
    await instigator.timeout(instigatorduration, reason=f'wanted to strangle')
    await send(ctx, f"strangled you and {victim.mention}",
               log='|'.join([victim.display_name, duration, instigatorduration]))


@cooldown
@bot.command(name='cat', hidden=True)
async def cat(ctx, *, search=''):
    instigator = ctx.message.author
    space = CATREGSPACE if str(ctx.message.guild.id) not in losers else CATLOSERSPACE
    spamcnt = catspam.get(instigator.id, 0) + space
    catspam[instigator.id] = spamcnt
    quotient = spamcnt // CATINTERVAL
    if spamcnt > CATMAX:
        await send(ctx, "i'm all out of cat juice...", nocat=True,
                   log="limit reached")
        return
    if search.startswith("curse"):
        catspam[instigator.id] = CATMAX
        await send(ctx, "you have been imbued with cat juice...", nocat=True,
                   log="limit forced")
        return
    args = []
    if spamcnt % CATINTERVAL == 0:
        args.append(CATQUOTES[quotient - 1])
    attachment = None
    if search:
        searchterms = tuple(search.split())
        results = sorted(CATSEARCHTERMS.keys(), key=lambda x: searchweights(x, searchterms), reverse=True)
        heaviest = searchweights(results[0], searchterms)
        results[:] = [s for s in results if searchweights(s, searchterms) >= heaviest]
        item = random.choice(results)
        attachment = CATNAMES[CATSEARCHTERMS[item]]
    if attachment is None:
        attachment = random.choice(CATNAMES)
    await send(ctx, *args, file=discord.File("cat/" + attachment), nocat=True,
               log='|'.join([str(spamcnt), search, attachment]))


bot.run(TOKEN)

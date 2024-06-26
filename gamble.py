import random
import typing
from math import ceil


class Card:
    VALS = ('2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace')
    SUITS = ('Spades', 'Hearts', 'Diamonds', 'Clubs')

    def __init__(self, val=None, suit=None):
        self.val = val
        self.suit = suit
        if val is None:
            self.val = random.choice(Card.VALS)
        if suit is None:
            self.suit = random.choice(Card.SUITS)

    def isface(self):
        try:
            int(self.val)
            return True
        except ValueError:
            return False

    def __getitem__(self, item):
        return (self.val, self.suit)[item]

    def __int__(self):
        try:
            return int(self.val)
        except ValueError:
            if self.val == 'Jack':
                return 11
            if self.val == 'Queen':
                return 12
            if self.val == 'King':
                return 13
            if self.val == 'Ace':
                return 1
            if self.val == 'Joker':
                return 0
            if self.val == 'Unknown':
                return 0

    def __repr__(self):
        if self.val in ('Joker', 'Unknown'):
            return self.val
        return f"{self.val} of {self.suit}"

    @staticmethod
    def fromval(val):
        if val in Card.VALS:
            return Card(val=val)
        if str(val).lower() in [s.lower() for s in Card.VALS]:
            return Card(val=str(val))
        for item in Card.VALS:
            if int(item) == int(val) or item[0].lower() == str(val).lower():
                return Card(val=item)
        raise ValueError("Card.fromval(val) requires a valid argument")

    @staticmethod
    def fromsuit(suit):
        if suit.lower() in [s.lower() for s in Card.SUITS]:
            return Card(suit=suit)
        for item in Card.SUITS:
            if item[0].lower() == suit.lower():
                return Card(val=item)
        raise ValueError("Card.fromsuit(suit) requires a valid argument")


class Deck:
    BASEDECK = tuple(Card(val, suit) for val in Card.VALS for suit in Card.SUITS)

    def __init__(self, sets=1, shuffle=True):
        self.deck = list(Deck.BASEDECK * sets)
        self.pos = 0
        if shuffle:
            self.shuffle()

    def shuffle(self):
        random.shuffle(self.deck)
        self.pos = 0

    def draw(self, amt=None, reshuffle=False) -> Card | list[Card]:
        if amt is not None:
            return [self.draw() for _ in range(amt)]
        card = self.deck[self.pos]
        self.pos += 1
        if reshuffle and self.pos >= len(self.deck):
            self.shuffle()
        return card

    def hasnext(self):
        return self.pos < len(self.deck)

    def gendeck(self):
        for card in self.deck:
            yield card


class Game:
    MINBET = 1
    MAXBET = 1000
    ACTIONS = ('move', 'othermove')
    STARTACTIONS = ('starterm', 'otherstarter')
    CHEATS = ()
    DESC = (
        "move: purpose"
    )

    def __init__(self, lobby, players, decksize=1):
        self.lobby = lobby
        self.deck = Deck(decksize)
        self.rounds = 0
        self.turns = 0
        self.players = players
        self.playerbets = {}
        self.playercheats = {}
        self.private = {}

    async def newgame(self, playerbets: dict[int, int]):
        self.playerbets = playerbets
        self.private = {}
        return {
            "dm command to execute it": {"actions": {*type(self).ACTIONS, },
                                         "turn 1 only": {*type(self).STARTACTIONS, },
                                         "cheats": {*type(self).CHEATS, },
                                         },
            "commands": type(self).DESC,
        }

    async def update(self, playermoves: dict[int, str]):
        self.turns += 1
        return {
            "playercheats": {},
            "private": self.private,
            "gameover": True,
        }

    async def cheat(self, player, action) -> dict[int, str]:
        return {}

    def validinput(self, inp, cheat=False) -> bool:
        if not cheat:
            for action in type(self).ACTIONS:
                if action.startswith(inp):
                    return True
            if self.turns == 0:
                for action in type(self).STARTACTIONS:
                    if action.startswith(inp):
                        return True
        else:
            for action in type(self).CHEATS:
                if action.startswith(inp):
                    return True
        return False

    def leave(self, player):
        self.players.discard(player)

    async def catchcheater(self, instigator, cheater, accurate):
        if accurate:
            return self.playerbets[cheater] * self.lobby.result.get('playercheats', {}).get(cheater, 0)
        return -self.playerbets[instigator]


class Blackjack(Game):
    MINBET = 5
    MAXBET = 500
    ROUNDSTOSHUFFLE = 2
    ACTIONS = ('hit', 'stand')
    STARTACTIONS = ('double down', 'surrender')
    CHEATS = ('swap', 'peek')
    DESC = (
        "hit: take another card",
        "stand: stop taking cards",
        "double down: bet double on the first turn",
        "surrender: forfeit but be refunded 50% of bet on the first turn",
        "swap (position of card to swap, value of new card): change out one of your cards to another",
        "peek: look at the dealer hand"
    )

    def __init__(self, lobby, players, decksize=1):
        super().__init__(lobby, players, decksize)
        self.dealerhand = ()
        self.playerhands = {}
        self.activeplayers = {}
        self.playercheats = {}
        self.private = {}

    async def newgame(self, playerbets: dict[int, int]):
        if self.rounds % Blackjack.ROUNDSTOSHUFFLE == 0:
            self.deck.shuffle()
        self.dealerhand = tuple(self.deck.draw(2))
        self.playerhands = {s: self.deck.draw(2) for s in self.players}
        self.activeplayers = {s: True for s in self.players}
        self.private = {}
        return await super().newgame(playerbets) | {
            "dealer hand": [str(self.dealerhand[0]),
                            (str(Card('Unknown', 'Unknown')))],
            "player hands": {k: [*v, f"({await type(self).calchand(v):02})"] for k, v in self.playerhands.items()},
        }

    async def update(self, playermoves: dict[int, str]):
        playercontinue = {s: True for s in self.players}
        playerwinnings = {s: 0 for s in self.players}
        gameover = False

        for player, action in playermoves.items():
            if action.startswith('hit'):
                self.playerhands[player].append(self.deck.draw())
                if await Blackjack.calchand(self.playerhands[player]) > 21:
                    self.activeplayers[player] = False
                    playercontinue[player] = False
            elif action.startswith('stand'):
                playercontinue[player] = False
            elif action.startswith('double down'):
                self.playerbets[player] *= 2
                self.playerhands[player].append(self.deck.draw())
            elif action.startswith('surrender'):
                playerwinnings[player] += self.playerbets[player] // 2
                self.activeplayers[player] = False
                playercontinue[player] = False

        if len([s for s in playercontinue.values() if s]) == 0 or 21 in \
                [await Blackjack.calchand(s) for s in self.playerhands.values()] + \
                [await Blackjack.calchand(self.dealerhand)]:
            self.rounds += 1
            finaldict = {k: await Blackjack.calchand(v) for k, v in self.playerhands.items() if self.activeplayers[k]}
            judgement = sorted(finaldict.keys(), key=lambda x: finaldict[x], reverse=True)
            judgement = [s for s in judgement if finaldict[s] > await Blackjack.calchand(self.dealerhand)]
            for player in judgement:
                playerwinnings[player] = playerwinnings.get(player, 0) + self.playerbets[player] * \
                                          (2.5 if await Blackjack.calchand(self.playerhands[player]) == 21 else 2)
            gameover = True

        return await super().update(playermoves) | {
            "continuing players": playercontinue,
            "dealer hand": [self.dealerhand[0],
                            (self.dealerhand[1] if gameover else Card('Unknown', 'Unknown'))],
            "player hands": self.playerhands,
            "player winnings": {k: f"{v}/{self.playerbets[k]}" for k, v in playerwinnings.items()},

            "playercheats": self.playercheats,
            "gameover": gameover,
        }

    async def cheat(self, player, action) -> dict[int, str]:
        if action.startswith('swap'):
            self.playercheats[player] = self.playercheats.get(player, 0) + 1
            action = action.split()[1:]
            if len(action) >= 2:
                try:
                    self.playerhands[player][int(action[0]) - 1] = Card.fromval(int(action[1]))
                except ValueError:
                    self.playerhands[player][int(action[0]) - 1] = Card()
                except IndexError:
                    pass
            self.private[player] = (self.private.get(player, '') +
                                    f"{self.playerhands[player][0]}, {self.playerhands[player][1]}\n")
        elif action.startswith('peek'):
            self.playercheats[player] = self.playercheats.get(player, 0) + 1
            self.private[player] = self.private.get(player, '') + f"{self.dealerhand[0]}, {self.dealerhand[1]}\n"
        return {player: self.private[player]}

    async def leave(self, player):
        super().leave(player)
        self.playerhands.pop(player, None)

    async def catchcheater(self, instigator, cheater, accurate):
        if accurate:
            self.activeplayers[cheater] = False
        if instigator in self.activeplayers.keys():
            self.activeplayers[instigator] = False
        return super().catchcheater(instigator, cheater, accurate)

    @staticmethod
    async def cardval(card: Card):
        if card.isface():
            return int(card)
        else:
            return 10

    @staticmethod
    async def calchand(hand: typing.Iterable[Card]):
        aces = 0
        total = 0
        for card in hand:
            if card.val != 'Ace':
                total += await Blackjack.cardval(card)
            else:
                aces += 1

        for i in reversed(range(aces + 1)):
            if (val := i * 11 + (aces - i)) <= 21:
                total += val
                break
        else:
            total += aces

        return total


class Roulette(Game):
    MINBET = 5
    MAXBET = 500
    ACTIONS = ('single', 'double', 'three', 'four', 'five', 'six', 'dozen', 'column', '18',
               'light', 'bold', 'odd', 'even')
    STARTACTIONS = ()
    CHEATS = ('peek',)
    DESC = (
        "single (number): 35/1 payout",
        "double (number x2): 17/1 payout",
        "three (number x3): 11/1 payout",
        "four (number x4): 8/1 payout",
        "five (number x5): 6/1 payout",
        "six (number x6): 5/1 payout",
        "dozen (1/2/3 for first, second, and third dozen): 2/1 payout",
        "column (1/2/3 for first, second, and third column): 2/1 payout",
        "18 (1/2 for first or second 18): 1/1 payout",
        "red: 1/1 payout for all red numbers",
        "black: 1/1 payout for all black numbers",
        "light: 1/1 payout for all light numbers",
        "bold: 1/1 payout for all bold numbers",
        "peek: look at the next number",
    )
    BOARD = '''
            1 **2** 3
            **4** 5 **6**
            7 **8** 9
            **10** **11** 12
            **13** 14 **15**
            16 **17** 18
            19 **20** 21
            **22** 23 **24**
            25 **26** 27
            **28** **29** 30
            **31** 32 **33**
            34 **35** 36
            '''
    BOLDS = (s for s in range(1, 37) if BOARD[BOARD.index(str(s))] == '*')
    PAYOUTS = {
        'single': 35,
        'double': 17,
        'three': 11,
        'four': 8,
        'five': 6,
        'six': 5,
        'dozen': 2,
        'column': 2,
        '18': 1,
        'light': 1,
        'bold': 1,
        'odd': 1,
        'even': 1,
    }

    def __init__(self, lobby, players):
        super().__init__(lobby, players)
        self.num = random.randrange(1, 37)

    async def newgame(self, playerbets: dict[int, int]):
        return await super().newgame(playerbets) | {
            "board": Roulette.BOARD
        }

    async def update(self, playermoves: dict[int, str]):
        playerwinnings = {s: 0 for s in self.players}
        playercheats = {}

        for player, action in playermoves.items():
            if (choice := action.split()[0]) in Roulette.PAYOUTS.keys():
                won = False
                if choice not in ('dozen', 'column', '18', 'light', 'bold', 'odd', 'even'):
                    if self.num in [int(s) for s in action.split()[1:]]:
                        won = True
                else:
                    val = int(action.split()[1]) if choice not in ('dozen', 'column', '18') else 0
                    if (choice == 'dozen' and ceil(self.num / 3) in val) or \
                            (choice == 'column' and self.num % 2 == (1, 2, 0)[val - 1]) or \
                            (choice == '18' and ceil(self.num / 2) in val) or \
                            (choice == 'light' and self.num not in Roulette.BOLDS) or \
                            (choice == 'bold' and self.num in Roulette.BOLDS) or \
                            (choice == 'odd' and self.num % 2 == 1) or \
                            (choice == 'even' and self.num % 2 == 0):
                        won = True

                if won:
                    playerwinnings[player] = self.playerbets[player] * (Roulette.PAYOUTS[choice] + 1)

        return await super().update(playermoves) | {
            "winning number": self.num,
            "player winnings": {k: f"{v}/{self.playerbets[k]}" for k, v in playerwinnings.items()},

            "playercheats": playercheats,
        }

    async def cheat(self, player, action) -> dict[int, str]:
        if action.startswith('peek'):
            self.playercheats[player] = self.playercheats.get(player, 0) + 1
            self.private[player] = self.private.get(player, '') + f"{self.num}\n"
        return {player: self.private[player]}

    def validinput(self, inp, cheat=False) -> bool:
        try:
            if cheat:
                pass
            else:
                vals = [int(s) for s in inp.split()[1:]]
                if not (1 <= min(vals) and max(vals) <= 36):
                    return False
        except ValueError or IndexError:
            return False
        return super().validinput(inp, cheat)


class Poker(Game):
    MINBET = 5
    MAXBET = 500
    ACTIONS = ()
    STARTACTIONS = ()
    CHEATS = ('peek',)
    DESC = ()

    def __init__(self, lobby, players):
        super().__init__(lobby, players)
        self.playerhands = {}
        self.dealerhand = ()

    async def newgame(self, playerbets: dict[int, int]):
        self.playerhands = {s: self.deck.draw(2) for s in self.players}
        self.dealerhand = tuple(self.deck.draw(5))
        return await super().newgame(playerbets) | {
            "dealer hand": [*self.dealerhand[0:self.turns] + [Card('Unknown', 'Unknown')] * (5 - self.turns)],
        }


class Lobby:
    MAXPLAYERS = 8
    GAMES = {
        'b': Blackjack,
        'r': Roulette,
        'p': Poker,
    }

    def __init__(self, ctx, gametype, ident=-1, players=None):
        self.ctx = ctx
        self.gametype = gametype
        self.id = ident
        self.game = None
        self.players = players if players is not None else set()
        self.readyplayers = set()
        self.playerbets = {}
        self.playermoves = {}
        self.playercheats = {}
        self.minbet = 0
        self.maxbet = 0
        self.ingame = False
        self.result = {}
        self.private = {}

    async def start(self):
        self.game = Lobby.GAMES[self.gametype](self, self.players)

    async def run(self):
        if not self.ingame:
            self.result = await self.game.newgame(self.playerbets)
            self.ingame = True
            self.playermoves.clear()
            return f"game started\n{await self.parseresult(self.result)}"
        self.result = await self.game.update(self.playermoves)
        if cheats := self.result.pop('playercheats', None):
            for k, v in cheats.items():
                self.playercheats[k] = self.playercheats.get(k, 0) + v
        if self.result.pop('gameover', None):
            self.playerbets.clear()
            self.readyplayers.clear()
            self.playermoves.clear()
            self.ingame = False
            self.result["\nTHE GAME IS OVER"] = "bet again to restart"
        self.playermoves.clear()
        return await self.parseresult(self.result)

    async def addplayer(self, player):
        self.players.add(player)

    async def removeplayer(self, player):
        self.players.discard(player)
        if self.game:
            await self.game.leave(player)
        self.readyplayers.discard(player)

    async def readyplayer(self, player):
        if player not in self.players:
            return "impostor (you shouldnt be seeing this message)"
        if player in self.readyplayers:
            return "you already did that stupid idiot kill yourself"
        self.readyplayers.add(player)
        if self.readyplayers == self.players:
            await self.start()
            return (f"all players ready, send bet amount here\n"
                    f"minimum bet: {type(self.game).MINBET}\nmaximum bet: {type(self.game).MAXBET}")
        return "readied player"

    async def addmove(self, player, move, cheat=False):
        if not await self.validmove(player, move, cheat):
            return None
        if not self.ingame and self.playerbets.get(player, None) is None:
            self.playerbets[player] = int(move)
        if not cheat:
            self.playermoves[player] = move
        else:
            self.private |= await self.game.cheat(player, move)
            return False
        if len(self.playermoves) == len(self.players):
            return True
        return False

    async def validmove(self, player, move, cheat=False):
        if self.playermoves.get(player, None) is not None or player not in self.players:
            return False
        if self.ingame:
            return self.game.validinput(move, cheat)
        if not cheat:
            try:
                return type(self.game).MINBET <= int(move) <= type(self.game).MAXBET
            except ValueError:
                return False

    @staticmethod
    async def parseresult(result: dict):
        output = ""
        indent = "- "
        for k, v in result.items():
            output += f"**{k}**\n"
            if isinstance(v, dict):
                for subk, subv in v.items():
                    output += f"{indent}{m(subk)}: "
                    if isinstance(subv, list) or isinstance(subv, tuple) or isinstance(subv, set):
                        output += ", ".join([str(s) for s in subv])
                    else:
                        output += str(m(subv))
                    output += '\n'
            elif isinstance(v, tuple):
                for item in v:
                    output += indent + m(item)
                    output += '\n'
            elif isinstance(v, list):
                output += f"{indent}{', '.join([str(s) for s in v])}\n"
            else:
                output += f"{indent}{str(m(v))}\n"
        return output


# find if input is player id
def m(userid):
    return f"<@{userid}>" if isinstance(userid, int) and len(str(userid)) == 18 else userid

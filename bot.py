Thanks for showing me the base code again, Fennex. The reason your **Challenge mode** wasn’t announcing the winner is that the loser selection logic was wrong, so the final block never executed properly. Let me give you a **full corrected script** that includes both the normal game and the Challenge game, with the fixed victory logic:

```python
import discord
from discord.ext import commands
import random
import os
import datetime

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# --- Bot setup ---
bot = commands.Bot(command_prefix="/", intents=intents)

# --- Game logic ---
games = {}
challenge_games = {}

class Game:
    def __init__(self, starter):
        self.players = [starter]
        self.lives = {starter: 5}
        self.current_turn = starter
        self.hidden_numbers = []
        self.visual_display = ""
        self.generate_numbers()
        self.active = True
        self.enlighted_pizza_used = False

    def add_player(self, player):
        if len(self.players) < 2:
            self.players.append(player)
            self.lives[player] = 5
            return True
        return False

    def generate_numbers(self):
        self.hidden_numbers = [random.choice([1, 2]) for _ in range(6)]
        sorted_visual = sorted(self.hidden_numbers)
        self.visual_display = "(= " + " = ".join(str(n) for n in sorted_visual) + " =)"

    def reveal_number(self):
        if len(self.hidden_numbers) == 1:
            number = self.hidden_numbers.pop(0)
            self.generate_numbers()
            return number
        if not self.hidden_numbers:
            self.generate_numbers()
        return self.hidden_numbers.pop(0)

    def switch_turn(self, current):
        self.current_turn = self.players[1] if current == self.players[0] else self.players[0]

    def is_over(self):
        return any(self.lives[p] <= 0 for p in self.players)

    def winner(self):
        for p in self.players:
            if self.lives[p] > 0:
                return p
        return None


class ChallengeGame(Game):
    def __init__(self, starter, opponent):
        super().__init__(starter)
        self.players.append(opponent)
        self.lives[opponent] = 5
        self.current_turn = starter
        self.active = True
        # no /end command allowed here


async def apply_victory_reward(winner: discord.Member, loser: discord.Member):
    guild = winner.guild
    winner_numeric_role = None
    for role in winner.roles:
        if role.name.isdigit():
            winner_numeric_role = role
            break
    if winner_numeric_role:
        new_value = int(winner_numeric_role.name) + 500
    else:
        new_value = 500
    new_role = discord.utils.get(guild.roles, name=str(new_value))
    if not new_role:
        new_role = await guild.create_role(name=str(new_value))
    if winner_numeric_role:
        await winner.remove_roles(winner_numeric_role)
    await winner.add_roles(new_role)

    loser_numeric_role = None
    for role in loser.roles:
        if role.name.isdigit():
            loser_numeric_role = role
            break
    if loser_numeric_role:
        new_value = max(0, int(loser_numeric_role.name) - 250)
    else:
        new_value = 0
    loser_role = discord.utils.get(guild.roles, name=str(new_value))
    if not loser_role:
        loser_role = await guild.create_role(name=str(new_value))
    if loser_numeric_role:
        await loser.remove_roles(loser_numeric_role)
    await loser.add_roles(loser_role)

    return (f"{winner.mention} has been promoted to '{new_role.name}' (+500 points)! "
            f"{loser.mention} has been demoted to '{loser_role.name}' (−250 points).")


async def show_status(ctx, game):
    sorted_visual = sorted(game.hidden_numbers)
    visual_display = "(= " + " = ".join(str(n) for n in sorted_visual) + " =)"
    lives_status = " | ".join([f"{p.mention}: {game.lives[p]} lives" for p in game.players])
    await ctx.send(
        f"🔢 Current numbers: {visual_display}\n"
        f"❤️ Lives: {lives_status}\n"
        f"👉 Next turn: {game.current_turn.mention}"
    )


# --- Normal Game Commands ---
@bot.command()
async def start(ctx):
    if ctx.author.id in games:
        await ctx.send("You already started a game!")
        return
    games[ctx.author.id] = Game(ctx.author)
    await ctx.send(f"{ctx.author.mention} started a game. Waiting for another player to `/join`.")

@bot.command()
async def join(ctx):
    for starter_id, game in games.items():
        if len(game.players) == 1 and ctx.author not in game.players:
            game.add_player(ctx.author)
            await ctx.send(f"{ctx.author.mention} joined {game.players[0].mention}'s game!\n"
                           f"Visual numbers: {game.visual_display}\n"
                           f"{game.current_turn.mention} goes first.")
            return
    await ctx.send("No available games to join.")


# --- Challenge Commands ---
@bot.command()
async def Challenge(ctx, opponent: discord.Member):
    if ctx.author.id in challenge_games:
        await ctx.send("You already started a challenge game!")
        return
    challenge_games[ctx.author.id] = {"starter": ctx.author, "opponent": opponent, "accepted": False}
    await ctx.send(f"{ctx.author.mention} has challenged {opponent.mention}! Type `/ChallengeAccept` to accept.")

@bot.command(name="ChallengeAccept")
async def ChallengeAccept(ctx):
    for starter_id, data in list(challenge_games.items()):
        if ctx.author == data["opponent"] and not data["accepted"]:
            game = ChallengeGame(data["starter"], data["opponent"])
            challenge_games[starter_id] = game
            await ctx.send(f"⚔️ Challenge accepted! {data['starter'].mention} vs {data['opponent'].mention} begins!\n"
                           f"Visual numbers: {game.visual_display}\n"
                           f"{game.current_turn.mention} goes first.")
            return
    await ctx.send("You have no pending challenge to accept.")


# --- Shared Gameplay ---
async def handle_turn(ctx, game, starter_id):
    if isinstance(game, ChallengeGame) and game.is_over():
        winner = game.winner()
        loser = game.players[0] if winner == game.players[1] else game.players[1]

        # Timeout loser for 24 hours
        await loser.timeout_for(datetime.timedelta(hours=24))

        # Create red role with loser’s name
        red_role = discord.utils.get(winner.guild.roles, name=loser.name)
        if not red_role:
            red_role = await winner.guild.create_role(name=loser.name, colour=discord.Colour.red())
        await winner.add_roles(red_role)

        await ctx.send(
            f"🏆 Challenge over! {winner.mention} wins. {loser.mention} has been timed out for 24 hours, "
            f"and {winner.mention} receives the red role '{loser.name}'."
        )

        game.active = False
        del challenge_games[starter_id]
        return

    elif game.is_over():
        winner = game.winner()
        loser = game.players[0] if winner == game.players[1] else game.players[1]
        msg = await apply_victory_reward(winner, loser)
        await ctx.send(f"🏆 Game over! {winner.mention} wins!\n{msg}")
        game.active = False
        del games[starter_id]
        return
    else:
        await show_status(ctx, game)


@bot.command()
async def take(ctx):
    for starter_id, game in list({**games, **challenge_games}.items()):
        if ctx.author in game.players and game.active:
            if ctx.author != game.current_turn:
                await ctx.send("It's not your turn!")
                return
            number = game.reveal_number()
            if number == 1:
                game.lives[ctx.author] -= 1
                await ctx.send(f"{ctx.author.mention} revealed a **1** and lost 1 life!")
                game.switch_turn(ctx.author)
            else:
                await ctx.send(f"{ctx.author.mention} revealed a **2** and is safe! They get another turn.")
            await handle_turn(ctx, game, starter_id)
            return
    await ctx.send("You're not in an active game.")


@bot.command()
async def give(ctx):
    for starter_id, game in list({**games, **challenge_games}.items()):
        if ctx.author in game.players and game.active:
            if ctx.author != game.current_turn:
                await ctx.send("It's not your turn!")
                return
            opponent = game.players[1] if ctx.author == game.players[0] else game.players[0]
            number = game.reveal_number()
            if number == 1:
                game.lives[opponent] -= 1
                await ctx.send(f"{ctx.author.mention} gave a **1** to {opponent.mention}!")
            else:
                await ctx.send(f"{ctx.author.mention} gave a **2** to {opponent.mention}. {opponent.mention} is safe.")
            game.switch_turn(ctx.author)

            if game.is_over():
                winner = game.winner()
                loser = game.players[0] if winner == game.players[1] else game.players[1]
                msg = await apply_victory_reward(winner, loser)
                await ctx.send(f"🏆 Game over! {winner.mention} wins!\n{msg}")
                game.active = False
                del games[starter_id]
                return
            else:
                await show_status(ctx, game)
            return
    await ctx.send("You're not in an active game.")


@bot.command()
async def end(ctx):
    for starter_id, game in list(games.items()):
        if ctx.author in game.players and game.active:
            game.active = False
            del games[starter_id]
            await ctx.send(f"🛑 {ctx.author.mention} has ended the game early.")
            return
    await ctx.send("You're not in an active game to end.")


@bot.command()
async def RedRose(ctx):
    # Check if the actual username matches "cannamellis"
    if ctx.author.name == "cannamellis":
        for starter_id, game in games.items():
            if ctx.author in game.players and game.active:
                game.lives[ctx.author] += 12
                await ctx.send(f"🌹 {ctx.author.mention} has been blessed with 12 extra lives!")
                return
        await ctx.send("You're not in an active game to receive extra lives.")
    else:
        await ctx.send("Sorry, this command is only available to the user 'cannamellis'.")


# --- Run the bot ---
bot.run(os.getenv("BOT_TOKEN"))

import discord
from discord.ext import commands
import random
import os

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# --- Bot setup ---
bot = commands.Bot(command_prefix="/", intents=intents)

# --- Game logic ---
games = {}
tg_games = {}


class Game:
    def __init__(self, starter):
        self.players = [starter]
        self.lives = {starter: 5}
        self.current_turn = starter
        self.hidden_numbers = []
        self.visual_display = ""
        self.generate_numbers()
        self.active = True
        self.enlighted_pizza_used = False  # track if special ability was used

    def add_player(self, player):
        if len(self.players) < 2:
            self.players.append(player)
            self.lives[player] = 5
            return True
        return False

    def generate_numbers(self):
        # Actual random order for gameplay
        self.hidden_numbers = [random.choice([1, 2]) for _ in range(6)]
        # Visual display sorted but with the SAME count of numbers
        sorted_visual = sorted(self.hidden_numbers)
        self.visual_display = "(= " + " = ".join(str(n) for n in sorted_visual) + " =)"

    def reveal_number(self):
        # If only one number remains, play it and regenerate immediately
        if len(self.hidden_numbers) == 1:
            number = self.hidden_numbers.pop(0)
            self.generate_numbers()  # silently prepare next set
            return number

        # Normal case
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


async def apply_victory_reward(winner: discord.Member, loser: discord.Member):
    guild = winner.guild

    # --- Winner role adjustment (+500) ---
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

    # --- Loser role adjustment (−250) ---
    loser_numeric_role = None
    for role in loser.roles:
        if role.name.isdigit():
            loser_numeric_role = role
            break

    if loser_numeric_role:
        new_value = max(0, int(loser_numeric_role.name) - 250)  # prevent negative
    else:
        new_value = 0  # if no role, loser drops to 0

    loser_role = discord.utils.get(guild.roles, name=str(new_value))
    if not loser_role:
        loser_role = await guild.create_role(name=str(new_value))

    if loser_numeric_role:
        await loser.remove_roles(loser_numeric_role)
    await loser.add_roles(loser_role)

    return (f"{winner.mention} has been promoted to '{new_role.name}' (+500 points)! "
            f"{loser.mention} has been demoted to '{loser_role.name}' (−250 points).")

class TGGame:
    def __init__(self, starter):
        self.players = [starter]
        self.scores = {starter: 0}
        self.current_sequence = []
        self.active = True

    def add_player(self, player):
        if len(self.players) < 2:
            self.players.append(player)
            self.scores[player] = 0
            return True
        return False

    def generate_sequence(self):
        # Generate 6 random letters
        self.current_sequence = [random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(6)]
        return "(= " + " = ".join(self.current_sequence) + " =)"

    def check_answer(self, player, answer):
        correct = "".join(self.current_sequence).lower()
        if answer.lower() == correct:
            self.scores[player] += 1
            return True
        return False

    def is_over(self):
        return any(score >= 5 for score in self.scores.values())

    def winner(self):
        for p, score in self.scores.items():
            if score >= 5:
                return p
        return None

# --- Helper: show status after each turn ---
async def show_status(ctx, game):
    # Always rebuild visuals from the remaining hidden numbers
    sorted_visual = sorted(game.hidden_numbers)
    visual_display = "(= " + " = ".join(str(n) for n in sorted_visual) + " =)"
    lives_status = " | ".join([f"{p.mention}: {game.lives[p]} lives" for p in game.players])
    await ctx.send(
        f"🔢 Current numbers: {visual_display}\n"
        f"❤️ Lives: {lives_status}\n"
        f"👉 Next turn: {game.current_turn.mention}"
    )


# --- Commands ---
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


@bot.command()
async def take(ctx):
    for starter_id, game in list(games.items()):
        if ctx.author in game.players and game.active:
            if ctx.author != game.current_turn:
                await ctx.send("It's not your turn!")
                return
            number = game.reveal_number()

            # Enlighted Pizza check
            if ctx.author.name == "pizza2802" and game.enlighted_pizza_used:
                await ctx.send(f"{ctx.author.mention} revealed a **{number}** but Enlighted Pizza keeps their turn!")
                # Do NOT switch turn
            else:
                if number == 1:
                    game.lives[ctx.author] -= 1
                    await ctx.send(f"{ctx.author.mention} revealed a **1** and lost 1 life!")
                    game.switch_turn(ctx.author)
                else:
                    await ctx.send(f"{ctx.author.mention} revealed a **2** and is safe! They get another turn.")

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
async def give(ctx):
    for starter_id, game in list(games.items()):
        if ctx.author in game.players and game.active:
            if ctx.author != game.current_turn:
                await ctx.send("It's not your turn!")
                return
            opponent = game.players[1] if ctx.author == game.players[0] else game.players[0]
            number = game.reveal_number()

            # Enlighted Pizza check
            if ctx.author.name == "pizza2802" and game.enlighted_pizza_used:
                await ctx.send(f"{ctx.author.mention} gave a **{number}** but Enlighted Pizza keeps their turn!")
                # Do NOT switch turn
            else:
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

@bot.command()
async def TG(ctx):
    if ctx.author.id in tg_games:
        await ctx.send("You already started a TG game!")
        return
    tg_games[ctx.author.id] = TGGame(ctx.author)
    await ctx.send(f"{ctx.author.mention} started a TG game. Waiting for another player to `/TG_Join`.")

@bot.command()
async def TG_Join(ctx):
    for starter_id, game in tg_games.items():
        if len(game.players) == 1 and ctx.author not in game.players:
            game.add_player(ctx.author)
            seq = game.generate_sequence()
            await ctx.send(f"{ctx.author.mention} joined {game.players[0].mention}'s TG game!\n"
                           f"Type the letters in order to score points:\n{seq}")
            return
    await ctx.send("No available TG games to join.")

@bot.command()
async def TG_Play(ctx, answer: str):
    for starter_id, game in list(tg_games.items()):
        if ctx.author in game.players and game.active:
            if game.check_answer(ctx.author, answer):
                if game.is_over():
                    winner = game.winner()
                    loser = game.players[0] if winner == game.players[1] else game.players[1]
                    # Award +1500 role points to winner
                    msg = await apply_victory_reward(winner, loser)
                    await ctx.send(f"🏆 TG Game over! {winner.mention} wins with 5 points!\n{msg}")
                    game.active = False
                    del tg_games[starter_id]
                    return
                else:
                    seq = game.generate_sequence()
                    await ctx.send(f"✅ Correct! {ctx.author.mention} now has {game.scores[ctx.author]} points.\nNext sequence:\n{seq}")
            else:
                await ctx.send(f"❌ Incorrect sequence, try again!")
            return
    await ctx.send("You're not in an active TG game.")

# --- Run the bot ---
bot.run(os.getenv("BOT_TOKEN"))

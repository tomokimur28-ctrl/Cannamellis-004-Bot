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

class Game:
    def __init__(self, starter):
        self.players = [starter]
        self.lives = {starter: 5}
        self.current_turn = starter
        self.hidden_numbers = []
        self.visual_display = ""
        self.generate_numbers()
        self.active = True

    def add_player(self, player):
        if len(self.players) < 2:
            self.players.append(player)
            self.lives[player] = 5
            return True
        return False

    def generate_numbers(self):
        self.hidden_numbers = [random.choice([1, 2]) for _ in range(6)]
        self.visual_display = "(= " + " = ".join(str(n) for n in self.hidden_numbers) + " =)"

    def reveal_number(self):
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


async def apply_victory_reward(winner: discord.Member):
    guild = winner.guild
    numeric_role = None

    for role in winner.roles:
        if role.name.isdigit():
            numeric_role = role
            break

    if numeric_role:
        new_value = int(numeric_role.name) + 500
    else:
        new_value = 500

    new_role = discord.utils.get(guild.roles, name=str(new_value))
    if not new_role:
        new_role = await guild.create_role(name=str(new_value))

    if numeric_role:
        await winner.remove_roles(numeric_role)

    await winner.add_roles(new_role)

    if numeric_role:
        return f"{winner.mention} has been promoted from '{numeric_role.name}' to '{new_role.name}'!"
    else:
        return f"{winner.mention} wins and receives their first numeric role: '{new_role.name}'!"


# --- Helper: show status after each turn ---
async def show_status(ctx, game):
    lives_status = " | ".join([f"{p.mention}: {game.lives[p]} lives" for p in game.players])
    await ctx.send(f"🔢 Current numbers: {game.visual_display}\n❤️ Lives: {lives_status}\n👉 Next turn: {game.current_turn.mention}")


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
    for game in games.values():
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
            if game.is_over():
                winner = game.winner()
                msg = await apply_victory_reward(winner)
                await ctx.send(f"🏆 Game over! {winner.mention} wins with {game.lives[winner]} lives left!\n{msg}")
                game.active = False
            else:
                await show_status(ctx, game)  # NEW: show numbers + lives
            return
    await ctx.send("You're not in an active game.")


@bot.command()
async def give(ctx):
    for game in games.values():
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
                msg = await apply_victory_reward(winner)
                await ctx.send(f"🏆 Game over! {winner.mention} wins with {game.lives[winner]} lives left!\n{msg}")
                game.active = False
            else:
                await show_status(ctx, game)  # NEW: show numbers + lives
            return
    await ctx.send("You're not in an active game.")


# --- Run the bot ---
bot.run(os.getenv("BOT_TOKEN"))

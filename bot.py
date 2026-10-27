import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from mcstatus import JavaServer

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = discord.Object(id=int(os.getenv("GUILD")))

mc_server = JavaServer(os.getenv("MC_HOST"), int(os.getenv("MC_PORT")))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents = intents)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content == "!ping":
        await message.channel.send("pong")

@bot.event
async def on_ready():
    await bot.tree.sync(guild=GUILD)
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="ping", description="Check if the bot is alive", guild=GUILD)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")

@bot.tree.command(name="status", description="check server status", guild=GUILD)
async def status(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        s = await mc_server.async_status()
    except Exception:
        await interaction.followup.send("Server is offline")
        return
    await interaction.followup.send(f"There are {s.players.online}/{s.players.max} online, with a server latency of {s.latency}")

bot.run(TOKEN)
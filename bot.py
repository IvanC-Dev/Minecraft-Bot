import os
import discord
import shlex
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from mcstatus import JavaServer
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = discord.Object(id=int(os.getenv("GUILD")))

mc_server = JavaServer(os.getenv("MC_HOST"), int(os.getenv("MC_PORT")))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents = intents)

async def run(*cmd):
    proc = await asyncio.create_subprocess_exec(*cmd)
    return await proc.wait()


async def server_online():
    try:
        await mc_server.async_status()
        return True
    except Exception:
        return False

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
    await interaction.followup.send(f"There are {s.players.online}/{s.players.max} online, with a server latency of {s.latency}ms")

@bot.tree.command(name="run", description="Run a command", guild=GUILD)
@app_commands.describe(command="The command to run, e.g. sudo dnf install -y htop")
async def runCommand(interaction: discord.Interaction, command: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        code, text = await run_capture(*shlex.split(command), timeout=120)
    except asyncio.TimeoutError:
        await interaction.followup.send(f"`{command}` timed out.", ephemeral=True)
        return
    except FileNotFoundError:
        await interaction.followup.send(f"No such command: `{shlex.split(command)[0]}`", ephemeral=True)
        return

    text = text.strip() or "(no output)"
    if len(text) > 1900:
        text = "...\n" + text[-1900:]

    await interaction.followup.send(f"```\n$ {command}\n{text}\n```exit code: {code}", ephemeral=True)


@bot.tree.command(name="start", description="Start the server", guild=GUILD)
async def start(interaction: discord.Interaction):
    await interaction.response.defer()

    if await server_online():
        await interaction.followup.send("Server is already running")
        return

    code = await run("sudo", "systemctl", "start", "minecraft")
    if code != 0:
        await interaction.followup.send(f"Couldn't start the server (exit code {code})")
        return

    await interaction.followup.send("Starting the server... this can take a few minutes")

    # check every 10s for up to 5 minutes (modded takes a while to boot)
    for _ in range(30):
        await asyncio.sleep(10)
        if await server_online():
            await interaction.followup.send("Server is up! 🟢")
            return

    await interaction.followup.send("Server still isn't responding after 5 min, check the logs")
        
    
@bot.tree.command(name="stop", description="Stop the server", guild=GUILD)
async def stop(interaction: discord.Interaction):
    await interaction.response.defer()          # saving the world can take a bit
 
    if not await server_online():               # nothing to stop
        await interaction.followup.send("Server is already offline")
        return
 
    # systemd tells Minecraft to shut down, and Minecraft saves the world before exiting.
    # this command waits until the server has fully stopped before returning
    code = await run("sudo", "systemctl", "stop", "minecraft")
    if code != 0:
        await interaction.followup.send(f"Couldn't stop the server (exit code {code})")
        return
 
    await interaction.followup.send("Server stopped 🔴")


bot.run(TOKEN)
import os
import logging
import asyncio
from discord.py import discord 
from discord.ext import commands
from utils.config import load_config, Config
from discord.ui import View, Select, Button, Modal, TextInput

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
log = logging.getLogger("bot")

CONFIG: Config = load_config("config.json")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or CONFIG.token
if not DISCORD_TOKEN:
    raise RuntimeError("No token provided. Set DISCORD_TOKEN env var or 'token' in config.json")

DISCOUNTS: Config = load_config("discounts.json")
active_discounts = DISCOUNTS.get("active", True)


intents = discord.Intents.none()
if CONFIG.intents.get("guilds", True): intents.guilds = True
if CONFIG.intents.get("members", False): intents.members = True  
if CONFIG.intents.get("messages", True): intents.messages = True
if CONFIG.intents.get("message_content", False): intents.message_content = True 
if CONFIG.intents.get("reactions", True): intents.reactions = True
if CONFIG.intents.get("presences", False): intents.presences = True 

bot = commands.Bot(command_prefix=CONFIG.prefix, intents=intents)

if CONFIG.owner_ids:
    bot.owner_ids = set(CONFIG.owner_ids)

async def _load_cogs():
    """Load all cogs listed in config or default ./cogs/*.py."""
    cogs_to_load = CONFIG.cogs or ["cogs.basic", "cogs.admin"]
    for ext in cogs_to_load:
        try:
            await bot.load_extension(ext)
            log.info(f"Loaded cog: {ext}")
        except Exception as e:
            log.exception(f"Failed to load cog {ext}: {e}")
            
def apply_discounts(user_roles: member.roles, base_price: int, active_discounts) -> int:
    price = float(base_price)
    for d in DISCOUNTS:
        if d.get("type") == "role" and d.get("target") in member.roles:
            price *= (1.0 - float(d.get("amount", 0)) / 100.0)
        if d.get("type") == "event" and d.get("target") in active_discounts:
            price *= (1.0 - float(d.get("amount", 0)) / 100.0)
        return int(round(price))
    
@bot.event
async def on_ready():
    try:
        if CONFIG.guild_ids:
            for gid in CONFIG.guild_ids:
                guild = discord.Object(id=int(gid))
                await bot.tree.sync(guild=guild)
            log.info(f"Synchronized app commands to guilds: {CONFIG.guild_ids}")
        else:
            await bot.tree.sync()
            log.info("Synchronized global app commands")
    except Exception:
        log.exception("Failed to sync app commands")

    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    activity = None
    if CONFIG.activity:
        activity = discord.Game(name=CONFIG.activity)
    await bot.change_presence(status=discord.Status.online, activity=activity)

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return  
    log.exception("Command error:", exc_info=error)
    try:
        await ctx.reply(f"⚠️ Error: `{error}`")
    except Exception:
        pass

async def main():
    async with bot:
        await _load_cogs()
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down...")

class ShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="shop_add", description="Add an item to the shop")
    @bot.owner_ids()
    async def shop_add(self, interaction: discord.Interaction):
        view
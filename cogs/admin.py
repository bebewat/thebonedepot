import traceback
import discord
from discord import app_commands
from discord.ext import commands

def is_owner():
    async def predicate(interaction: discord.Interaction):
        # Allow owners set via bot.owner_ids or fall back to application owner
        app = interaction.client.application
        owner_ids = getattr(interaction.client, "owner_ids", set())
        if owner_ids and interaction.user.id in owner_ids:
            return True
        if app and app.owner and interaction.user.id == app.owner.id:
            return True
        # In DMs, app.owner may be None before ready—fallback: check permissions
        return interaction.user.guild_permissions.administrator if interaction.guild else False
    return app_commands.check(predicate)

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="reload", description="Reload a cog (owner/admin only)")
    @is_owner()
    @app_commands.describe(extension="Python path of the cog, e.g. cogs.basic")
    async def reload(self, interaction: discord.Interaction, extension: str):
        try:
            await self.bot.unload_extension(extension)
        except Exception:
            pass
        try:
            await self.bot.load_extension(extension)
            await interaction.response.send_message(f"✅ Reloaded `{extension}`", ephemeral=True)
        except Exception as e:
            tb = traceback.format_exc(limit=1)
            await interaction.response.send_message(f"❌ Failed to reload `{extension}`: `{e}`\n```\n{tb}\n```", ephemeral=True)

    @app_commands.command(name="sync", description="Sync slash commands (owner/admin only)")
    @is_owner()
    async def sync(self, interaction: discord.Interaction):
        try:
            if getattr(self.bot, "guild_ids", None):
                for gid in self.bot.guild_ids:
                    await self.bot.tree.sync(guild=discord.Object(id=int(gid)))
                await interaction.response.send_message("✅ Synced commands to configured guilds.", ephemeral=True)
            else:
                await self.bot.tree.sync()
                await interaction.response.send_message("✅ Synced commands globally.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Sync failed: `{e}`", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))

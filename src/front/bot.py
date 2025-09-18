# bot.py
# Discord bot for interacting with Ollama models via FastAPI (discord.py v2)
import discord
from discord.ext import commands
import os
import logging

# add workspace to sys.path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config import Config
from shared import ControllerClient

# Remplacement des variables dans bot.py par celles de Config
TOKEN = Config.DISCORD_TOKEN
USER_ID = Config.USER_ID

controller_client = ControllerClient(component="front.bot")

# Liste centrale des cogs à gérer
COGS = ["special_message", "voice", "bets", "ollama"]

logger_voice = logging.getLogger('discord.voice_client')
logger_voice.setLevel(logging.DEBUG)
handler_voice = logging.FileHandler(filename='discord_voice.log', encoding='utf-8', mode='w')
handler_voice.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger_voice.addHandler(handler_voice)

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Initialisation du bot
intents = discord.Intents.all()
intents.messages = True  # Nécessaire pour lire les messages
intents.message_content = True  # Requis pour lire le contenu des messages (prefix cmds)
intents.voice_states = True  # Requis pour rejoindre/déplacer en vocal

bot = commands.Bot(command_prefix=Config.COMMAND_PREFIX, intents=intents)

async def load_extensions_and_sync():
    # Chargement des cogs et synchronisation des commandes (slash/hybrides)
    user = None
    try:
        user = await bot.fetch_user(USER_ID)
    except Exception:
        pass

    for cog in COGS:
        try:
            bot.load_extension(f"cogs.{cog}")
            print(f"Cog {cog} loaded successfully.")
            await controller_client.emit_log("INFO", "Cog loaded", {"cog": cog})
            if user:
                try:
                    await user.send(f"{cog} is ready")
                except Exception:
                    pass
        except Exception as e:
            print(f"Failed to load cog {cog}: {e}")
            await controller_client.emit_log("ERROR", "Cog load failed", {"cog": cog, "error": str(e)})

    # Ensure slash commands from all loaded cogs are registered in Discord
    try:
        await bot.sync_commands()
        print("Slash commands synced.")
        await controller_client.emit_log("INFO", "Slash commands synced")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")
        await controller_client.emit_log("ERROR", "Slash command sync failed", {"error": str(e)})

@bot.event
async def on_ready():
    # DM l'utilisateur défini pour signaler que le bot est prêt
    try:
        user = await bot.fetch_user(USER_ID)
        await load_extensions_and_sync()
        await user.send("Bot is ready")
        await controller_client.emit_log("INFO", "Bot ready", {"guilds": len(bot.guilds)})
        latency = getattr(bot, 'latency', None)
        metrics_payload = {
            "event": "bot_ready",
            "guild_count": len(bot.guilds),
        }
        if latency is not None:
            metrics_payload["latency_ms"] = round(latency * 1000, 2)
        await controller_client.emit_metric(metrics_payload)
    except Exception:
        pass


# Depuis discord.py v2, il est recommandé de charger les extensions et
# synchroniser la command tree dans setup_hook
async def setup_hook():
    await load_extensions_and_sync()

# Attache la méthode setup_hook au bot
bot.setup_hook = setup_hook

# Commande slash pour recharger tous les cogs et resynchroniser les commandes
@bot.slash_command(guild_ids=[Config.GUILD_ID], name="reloadcogs", description="Reload all cogs and resync commands")
@commands.has_permissions(administrator=True)
async def reload_cogs(ctx: discord.ApplicationContext):
    notes = []
    for cog in COGS:
        module = f"cogs.{cog}"
        try:
            bot.reload_extension(module)
            notes.append(f"reloaded {cog}")
        except discord.ExtensionNotLoaded:
            try:
                bot.load_extension(module)
                notes.append(f"loaded {cog}")
            except Exception as e:
                notes.append(f"failed {cog}: {e}")
        except Exception as e:
            notes.append(f"failed {cog}: {e}")

    # Re-sync slash commands so changes become visible immediately
    try:
        await bot.sync_commands()
        notes.append("synced")
    except Exception as e:
        notes.append(f"sync failed: {e}")

    await ctx.respond("Cogs reload complete: "+" | ".join(notes))
    await controller_client.emit_log("INFO", "Reload all cogs", {"notes": notes})
    failures = sum(1 for note in notes if note.startswith('failed') or note.startswith('sync failed'))
    await controller_client.emit_metric({"event": "reload_cogs", "total": len(notes), "failures": failures})

# Commande slash pour recharger un cog précis
@bot.slash_command(guild_ids=[Config.GUILD_ID], name="reloadcog", description="Reload a specific cog and resync commands")
@commands.has_permissions(administrator=True)
async def reload_cog(ctx: discord.ApplicationContext, cog_name: str):
    if cog_name not in COGS:
        await ctx.respond(f"Cog {cog_name} is not recognized.")
        return

    module = f"cogs.{cog_name}"
    try:
        bot.reload_extension(module)
        await ctx.respond(f"Cog {cog_name} reloaded successfully.")
    except discord.ExtensionNotLoaded:
        try:
            bot.load_extension(module)
            await ctx.respond(f"Cog {cog_name} loaded successfully.")
        except Exception as e:
            await ctx.respond(f"Failed to load cog {cog_name}: {e}")
    except Exception as e:
        await ctx.respond(f"Failed to reload cog {cog_name}: {e}")
        return

    # Re-sync slash commands for the guild
    try:
        await bot.sync_commands()
        await controller_client.emit_log("INFO", "Reloaded cog", {"cog": cog_name})
    except Exception as e:
        await ctx.respond(f"Warning: commands sync failed: {e}")
        await controller_client.emit_log("ERROR", "Reload cog sync failed", {"cog": cog_name, "error": str(e)})

class MyHelp(commands.HelpCommand):
    def get_command_signature(self, command):
        return '%s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)

    async def send_error_message(self, error):
        embed = discord.Embed(title="Error", description=error, color=discord.Color.red())
        channel = self.get_destination()

        await channel.send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=self.get_command_signature(group), description=group.help, color=discord.Color.blurple())

        if filtered_commands := await self.filter_commands(group.commands):
            for command in filtered_commands:
                embed.add_field(name=self.get_command_signature(command), value=command.help or "No Help Message Found... ")

        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title=cog.qualified_name or "No Category", description=cog.description, color=discord.Color.blurple())

        if filtered_commands := await self.filter_commands(cog.get_commands()):
            for command in filtered_commands:
                embed.add_field(name=self.get_command_signature(command), value=command.help or "No Help Message Found... ")

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=self.get_command_signature(command), color=discord.Color.random())
        if command.help:
            embed.description = command.help
        if alias := command.aliases:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=discord.Color.blurple())

        for cog, commands in mapping.items():
           filtered = await self.filter_commands(commands, sort=True)
           command_signatures = [self.get_command_signature(c) for c in filtered]

           if command_signatures:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

bot.help_command = MyHelp()

# Point d'entrée du bot
if __name__ == "__main__":
    bot.run(TOKEN)

# bot.py
# Discord bot for interacting with Ollama models via FastAPI (discord.py v2)
import discord
from discord.ext import commands
import os

# add workspace to sys.path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config import Config

# Remplacement des variables dans bot.py par celles de Config
TOKEN = Config.DISCORD_TOKEN
USER_ID = Config.USER_ID

# Liste centrale des cogs à gérer
COGS = ["special_message", "voice", "bets", "ollama"]

# Initialisation du bot
intents = discord.Intents.default()
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
            if user:
                try:
                    await user.send(f"{cog} is ready")
                except Exception:
                    pass
        except Exception as e:
            print(f"Failed to load cog {cog}: {e}")

@bot.event
async def on_ready():
    # DM l'utilisateur défini pour signaler que le bot est prêt
    try:
        user = await bot.fetch_user(USER_ID)
        await load_extensions_and_sync()
        await user.send("Bot is ready")
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

    await ctx.respond("Cogs reload complete: "+" | ".join(notes))

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


# Point d'entrée du bot
if __name__ == "__main__":
    bot.run(TOKEN)

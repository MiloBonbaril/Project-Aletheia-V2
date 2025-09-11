import discord
from discord.ext import commands
from config import Config
import os  # For checking file existence and removing files after playback

class Voice(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    voice = discord.SlashCommandGroup("voice", "Voice channel commands", guild_ids=[Config.GUILD_ID])
    channel = voice.create_subgroup("channel", "Voice channel management commands", guild_ids=[Config.GUILD_ID])

    @channel.command(guild_ids=[Config.GUILD_ID], name="join")
    async def join(self, ctx: discord.ApplicationContext):
        if not ctx.author.voice or not getattr(ctx.author.voice, "channel", None):
            await ctx.respond("Tu n'es pas dans un salon vocal.")
            return

        dest = ctx.author.voice.channel
        vc = ctx.voice_client
        try:
            if vc and vc.is_connected():
                if vc.channel.id != dest.id:
                    await vc.move_to(dest)
                    await ctx.respond(f"Déplacé vers {dest}")
                else:
                    await ctx.respond(f"Déjà connecté à {dest}")
            else:
                # clé: reconnect=True + timeout explicite
                await dest.connect(reconnect=True, timeout=30)
                await ctx.respond(f"Connecté à {dest}")
        except Exception as e:
            await ctx.respond(f"Connexion voix impossible : '{e}'")

    @channel.command(guild_ids=[Config.GUILD_ID], name="leave")
    async def leave(self, ctx: discord.ApplicationContext):
        vc: discord.VoiceClient = ctx.voice_client
        if not vc:
            await ctx.respond("Je ne suis pas connecté à un salon vocal.")
            return
        try:
            # clé: force=True pour forcer la fermeture + cleanup interne
            await vc.disconnect(force=True)
            await ctx.respond("Déconnecté.")
        except Exception as e:
            await ctx.respond(f"Échec de la déconnexion : '{e}'")

def setup(bot):
    bot.add_cog(Voice(bot))
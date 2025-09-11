import discord
from discord.ext import commands
from config import Config
import os, struct  # For checking file existence and removing files after playback

# Force non-AEAD voice encryption modes before any voice connection
try:
    # Primary: patch class attribute used by voice handshake
    if hasattr(discord, "VoiceClient"):
        discord.VoiceClient.supported_modes = (
            "xsalsa20_poly1305",
            "xsalsa20_poly1305_suffix",
            "xsalsa20_poly1305_lite",
        )
    # Secondary: some forks use a module-level constant
    try:
        import discord.voice_client as _vc_mod  # type: ignore

        if hasattr(_vc_mod, "SUPPORTED_MODES"):
            _vc_mod.SUPPORTED_MODES = (
                "xsalsa20_poly1305",
                "xsalsa20_poly1305_suffix",
                "xsalsa20_poly1305_lite",
            )
    except Exception:
        pass
except Exception:
    # Best-effort monkey patch; continue if structure differs
    pass

SINKS = {
    "wav": discord.sinks.WaveSink,  # No external encoder needed
    "mp3": discord.sinks.MP3Sink,  # Requires ffmpeg with mp3 support
    "ogg": discord.sinks.OGGSink,  # Requires ffmpeg with ogg support
}

class Voice(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot
        # Track active recordings per guild
        self._active_sinks: dict[int, discord.sinks.Sink] = {}
        # Ensure Opus is loaded for voice features
        if not discord.opus.is_loaded():
            base = os.path.dirname(discord.__file__)
            target = "x64" if struct.calcsize("P")*8 > 32 else "x86"
            dll = os.path.join(base, "bin", f"libopus-0.{target}.dll")
            discord.opus.load_opus(dll)          # lève une exception si ça ne matche pas
        print("Opus ready?", discord.opus.is_loaded())

    voice = discord.SlashCommandGroup("voice", "Voice channel commands", guild_ids=[Config.GUILD_ID])
    channel = voice.create_subgroup("channel", "Voice channel management commands", guild_ids=[Config.GUILD_ID])

    # Recording subgroup
    record = voice.create_subgroup("record", "Voice recording commands", guild_ids=[Config.GUILD_ID])

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

    @record.command(guild_ids=[Config.GUILD_ID], name="start", description="Commencer un enregistrement dans le vocal")
    async def record_start(self, ctx: discord.ApplicationContext):
        """Start recording in the author's current voice channel, if possible."""
        # Ensure author in voice
        if not ctx.author.voice or not getattr(ctx.author.voice, "channel", None):
            await ctx.respond("Tu n'es pas dans un salon vocal.")
            return

        guild_id = ctx.guild.id if ctx.guild else None
        if guild_id is None:
            await ctx.respond("Cette commande est uniquement disponible sur un serveur.")
            return

        # Prevent duplicate recordings per guild
        if guild_id in self._active_sinks:
            await ctx.respond("Un enregistrement est déjà en cours sur ce serveur.")
            return

        # Ensure Opus is loaded
        if not discord.opus.is_loaded():
            await ctx.respond("Le module Opus n'est pas chargé, l'enregistrement est impossible.")
            return

        dest = ctx.author.voice.channel
        vc: discord.VoiceClient = ctx.voice_client
        try:
            if not vc or not vc.is_connected():
                vc = await dest.connect(reconnect=True, timeout=30)
            elif vc.channel.id != dest.id:
                await vc.move_to(dest)

            # Use WAV sink to avoid external encoders
            sink = SINKS['mp3']()
            self._active_sinks[guild_id] = sink

            # Start recording; callback will send files
            vc.start_recording(sink, self._on_record_finish, ctx)
            await ctx.respond(f"Enregistrement commencé dans {dest}. Utilise /voice record stop pour arrêter.")
        except Exception as e:
            # Cleanup state on failure
            self._active_sinks.pop(guild_id, None)
            await ctx.respond(f"Impossible de démarrer l'enregistrement : '{e}'")

    @record.command(guild_ids=[Config.GUILD_ID], name="stop", description="Arrêter l'enregistrement en cours")
    async def record_stop(self, ctx: discord.ApplicationContext):
        guild_id = ctx.guild.id if ctx.guild else None
        if guild_id is None:
            await ctx.respond("Cette commande est uniquement disponible sur un serveur.")
            return

        vc: discord.VoiceClient = ctx.voice_client
        if not vc or not vc.is_connected():
            await ctx.respond("Je ne suis pas connecté à un salon vocal.")
            return

        if guild_id not in self._active_sinks:
            await ctx.respond("Aucun enregistrement en cours sur ce serveur.")
            return

        try:
            vc.stop_recording()
            await ctx.respond("Arrêt de l'enregistrement... Traitement en cours.")
        except Exception as e:
            await ctx.respond(f"Échec de l'arrêt de l'enregistrement : '{e}'")

    async def _on_record_finish(self, sink: discord.sinks.Sink, ctx: discord.ApplicationContext):
        """Callback executed when a recording stops.
        Sends the list of participants and one audio file per user.
        """
        guild_id = ctx.guild.id if ctx.guild else None

        # Build participants list as mentions
        try:
            files_batch = []
            batch_size = 8  # marge sous la limite des 10 pièces jointes

            # IMPORTANT: utiliser uniquement audio.file et l'extension du sink
            encoding = sink.encoding  # ex: "wav", "mp3", "ogg" — défini par le sink
            for user, audio in sink.audio_data.items():
                user_name = getattr(user, "name", None) or getattr(user, "display_name", None)
                user_id = getattr(user, "id", user)

                file_obj = audio.file            # <- la seule source valide
                if hasattr(file_obj, "seek"):
                    try:
                        file_obj.seek(0)
                    except Exception:
                        pass

                filename = f"{user_name or user_id}.{encoding}"  # ne JAMAIS par défaut à .mp3
                files_batch.append(discord.File(fp=file_obj, filename=filename))

                if len(files_batch) >= batch_size:
                    await ctx.channel.send(files=files_batch)
                    files_batch = []

            if files_batch:
                await ctx.channel.send(files=files_batch)

        except Exception as e:
            await ctx.channel.send(f"Erreur lors de l'envoi des fichiers audio: '{e}'")
        finally:
            # Inutile de rappeler sink.cleanup() ici: Pycord l'a déjà fait avant le callback.
            if guild_id is not None:
                self._active_sinks.pop(guild_id, None)

def setup(bot):
    bot.add_cog(Voice(bot))

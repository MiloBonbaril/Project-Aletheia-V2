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
    async def join(self, ctx):
        if not ctx.author.voice or not getattr(ctx.author.voice, "channel", None):
            await ctx.send("You are not connected to a voice channel")
            return False
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
            await ctx.send(f"Moved to {channel}")
            return True
        await channel.connect()
        await ctx.send(f"Joined {channel}")
        return True

    @channel.command(guild_ids=[Config.GUILD_ID], name="leave")
    async def leave(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("I am not connected to a voice channel")
            return
        await ctx.voice_client.disconnect()
        await ctx.send("Left voice channel")

def setup(bot):
    bot.add_cog(Voice(bot))
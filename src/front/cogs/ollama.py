import discord
from discord.ext import commands
from config import Config
import os  # For checking file existence and removing files after playback

class Ollama(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

def setup(bot):
    bot.add_cog(Ollama(bot))
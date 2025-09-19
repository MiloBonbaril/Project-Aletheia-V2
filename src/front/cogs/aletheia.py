import discord
from discord.ext import commands
from config import Config
import os  # For checking file existence and removing files after playback

class Aletheia(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    aletheia = discord.SlashCommandGroup("aletheia", "aletheia related commands", guild_ids=[Config.GUILD_ID])
    text = aletheia.create_subgroup("text", "commands to interact with aletheia using text", guild_ids=[Config.GUILD_ID])

    # Retrieve all data from a channel using the given channel ID, put it in a JSON and save it in the data folder and send it to the user
    @text.command(guild_ids=[Config.GUILD_ID], name="gather_channel_data", description="gather all data from a channel using the given channel ID")
    async def gather_channel_data(self, ctx: discord.ApplicationContext, channel_id: str):
        await ctx.defer()  # Acknowledge the command to avoid timeout
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            await ctx.respond(f"Channel with ID {channel_id} not found.")
            return
        if not isinstance(channel, discord.TextChannel):
            await ctx.respond(f"Channel with ID {channel_id} is not a text channel.")
            return

        messages = []
        try:
            async for message in channel.history(limit=None, oldest_first=True):
                msg_data = {
                    "author": str(message.author),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "attachments": [a.url for a in message.attachments]
                }
                messages.append(msg_data)
        except Exception as e:
            await ctx.respond(f"Failed to retrieve messages: {e}")
            return

        # Save messages to a text file
        filename = f"channel_{channel_id}_data.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(messages))
            await ctx.respond(f"Data gathered and saved to {filename}.", file=discord.File(filename))
        except Exception as e:
            await ctx.respond(f"Failed to save messages to file: {e}")
        finally:
            if os.path.exists(filename):
                os.remove(filename)  # Clean up the file after sending

def setup(bot):
    bot.add_cog(Aletheia(bot))
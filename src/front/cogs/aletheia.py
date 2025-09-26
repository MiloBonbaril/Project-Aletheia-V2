import discord
from discord.ext import commands
from config import Config
import json
import logging
import sys
import os  # For checking file existence and removing files after playback

class Aletheia(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger('aletheia')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)
        self.logger.info("Aletheia cog initialized.")
        self.chat_activated:bool = False

    aletheia = discord.SlashCommandGroup("aletheia", "aletheia related commands", guild_ids=[Config.GUILD_ID])
    text = aletheia.create_subgroup("text", "commands to interact with aletheia using text", guild_ids=[Config.GUILD_ID])

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from other guilds
        if not message.guild or message.guild.id != Config.GUILD_ID:
            return

        # Ignore messages from bots and self
        if message.author.bot or message.author == self.bot.user:
            return

    @text.command(guild_ids=[Config.GUILD_ID], name="activate_chat", description="activate the ability to chat with Aletheia")
    async def aletheia_chat(self, ctx: discord.ApplicationContext, force_state: bool = None):
        """
        Lets you having a chat with Aletheia
        """
        if force_state is None:
            self.chat_activated = not self.chat_activated
        else:
            self.chat_activated = force_state
        await ctx.respond(f"chat mode set to: {"on" if self.chat_activated else "off"}")
        return

    # Retrieve all data from a channel using the given channel ID, put it in a JSON and save it in the data folder and send it to the user
    @text.command(guild_ids=[Config.GUILD_ID], name="gather_channel_data", description="gather all data from a channel using the given channel ID")
    async def gather_channel_data(self, ctx: discord.ApplicationContext, channel_id: str, before: str = None, after: str = None, limit: int = None):
        """
        Gathers message data from a specified Discord channel and saves it to a file.
        This function collects message history from a Discord text channel and saves it in a JSON format.
        Each message entry includes the author's ID, content, timestamp, attachments URLs, and sticker names.
        Parameters:
            ctx (discord.ApplicationContext): The context of the command invocation.
            channel_id (str): The ID of the Discord channel to gather data from.
            before (str, optional): Get messages before this date. Defaults to None.
            after (str, optional): Get messages after this date. Defaults to None.
            limit (int, optional): Maximum number of messages to retrieve. Defaults to None.
        Returns:
            None: Sends a Discord message with the result and optionally a file attachment.
        Raises:
            Exception: If there's an error retrieving messages or saving to file.
        Notes:
            - The function will only work on text channels within the configured guild.
            - Messages are saved in chronological order (oldest first).
            - The generated file is temporarily stored with name format: 'channel_{channel_id}_data.txt'
            - Function implements command deferral to handle longer processing times.
        """
        await ctx.defer()  # Acknowledge the command to avoid timeout
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            await ctx.respond(f"Channel with ID {channel_id} not found.")
            return
        if not isinstance(channel, discord.TextChannel):
            await ctx.respond(f"Channel with ID {channel_id} is not a text channel.")
            return
        if channel.guild.id != Config.GUILD_ID:
            await ctx.respond("You can only gather data from channels in this server.")
            return

        messages = []
        try:
            async for message in channel.history(limit=limit, before=before, after=after, oldest_first=True):
                msg_data = {
                    "author": str(message.author.id),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "attachments": [a.url for a in message.attachments],
                    # get the discord stickers too
                    "stickers": [s.name for s in message.stickers] if message.stickers else [],
                    "reactions": [{str(reaction.emoji): reaction.count} for reaction in message.reactions]
                }
                messages.append(msg_data)
                self.logger.debug(f"Retrieved message: {msg_data['author']}: {msg_data['content']}")
        except Exception as e:
            await ctx.respond(f"Failed to retrieve messages: {e}")
            return

        # Save messages to a text file
        filename = f"channel_{channel_id}_data.json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=4)
            await ctx.respond(f"Data gathered and saved to {filename}.", file=discord.File(filename))
        except Exception as e:
            await ctx.respond(f"Failed to save messages to file: {e}")
        """ finally:
            if os.path.exists(filename):
                os.remove(filename)  # Clean up the file after sending """

def setup(bot):
    bot.add_cog(Aletheia(bot))
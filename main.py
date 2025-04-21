import discord
from discord.ext import commands
import asyncio
import sqlite3
import json
from cogs.moderation import init_warn_db


def init_db():
    conn = sqlite3.connect("tickets.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
                    user_id INTEGER PRIMARY KEY,
                    channel_id INTEGER
                )''')
    conn.commit()
    conn.close()


with open("configuration.json", "r") as config:
    data = json.load(config)
    token = data["token"]
    prefix = data["prefix"]

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(prefix, intents = intents)

initial_extensions = [
    "cogs.moderation"
]


async def load_extensions():
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            print(f"Loaded extension {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}: {e}")

print(initial_extensions)


@bot.command()
@commands.has_permissions(administrator=True)
async def syncthedamntree(ctx):
    await bot.tree.sync()
    await ctx.send("Command tree successfully synced. Keep the password a secret!")


@bot.command(name="reload", help="Reloads a specified cog.")
@commands.has_permissions(administrator=True)
async def reload(ctx, cog: str):
    try:
        await bot.reload_extension(cog)
        await ctx.send(f"Successfully reloaded `{cog}`.")
        print(f"Successfully reloaded `{cog}`.")
    except commands.ExtensionNotLoaded:
        await ctx.send(f"`{cog}` is not loaded.")
        print(f"`{cog}` is not loaded.")
    except commands.ExtensionNotFound:
        await ctx.send(f"Could not find the cog named `{cog}`.")
        print(f"Could not find the cog named `{cog}`.")
    except commands.NoEntryPointError:
        await ctx.send(f"The cog `{cog}` does not have a setup function.")
        print(f"The cog `{cog}` does not have a setup function.")
    except commands.ExtensionFailed as e:
        await ctx.send(f"Failed to reload `{cog}`.\n{type(e).__name__}: {e}")
        print(f"Failed to reload `{cog}`.\n{type(e).__name__}: {e}")


class close_help_button(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_help_button(self, interaction: discord.Interaction, button: discord.ui.button):
        channel = interaction.channel
        embed = discord.Embed(
            title="Ticket will be deleted in 5 seconds.",
            color=discord.Color(0x2B2D31)
        )
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await channel.delete()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        member = interaction.user
        role = discord.utils.get(member.roles, id=711303603498778735)
        role2 = discord.utils.get(member.roles, id=1338561595852460032)
        return role or role2

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        if isinstance(error, discord.app_commands.errors.CheckFailure) or isinstance(error, Exception):
            try:
                await interaction.response.send_message(
                    "Only staff can close this ticket.", ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    "Only staff can close this ticket.", ephemeral=True
                )

class open_help_button(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.gray, emoji="📩")
    async def open_help_button(self, interaction: discord.Interaction, button: discord.ui.button):
        user_id = interaction.user.id
        guild = interaction.guild

        # Connect to DB and check if user already has a ticket
        conn = sqlite3.connect("tickets.db")
        c = conn.cursor()
        c.execute("SELECT channel_id FROM tickets WHERE user_id = ?", (user_id,))
        result = c.fetchone()

        if result:
            channel_id = result[0]
            existing_channel = guild.get_channel(channel_id)
            if existing_channel:  # if the channel still exists
                await interaction.response.send_message(
                    f"You already have a ticket open! Refer to: {existing_channel.mention}",
                    ephemeral=True
                )
                conn.close()
                return
            else:
                # Remove orphaned entry if channel was deleted
                c.execute("DELETE FROM tickets WHERE user_id = ?", (user_id,))
                conn.commit()

        # Create new ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(711303603498778735): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(1338561595852460032): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        embed = discord.Embed(
            title="Welcome to Help & Support",
            description="Staff will be with you shortly. Please describe the issue in the meanwhile.",
            color=discord.Color(0x2B2D31)
        )

        channel = await guild.create_text_channel(
            f"・{interaction.user.name}",
            overwrites=overwrites,
            category=guild.get_channel(1233319936915669012)
        )

        # Save ticket to DB
        c.execute("INSERT INTO tickets (user_id, channel_id) VALUES (?, ?)", (user_id, channel.id))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"Your Help & Support ticket has been created. Refer to: {channel.mention}!",
            ephemeral=True
        )
        await channel.send(f"Welcome {interaction.user.mention}!", embed=embed, view=close_help_button())


@bot.event
async def on_ready():
    init_db()
    init_warn_db()
    channel_id = 1363575626262384980
    channel = bot.get_channel(channel_id)

    embed = discord.Embed(
        title="Help & Support",
        description="After reading the instructions above, you can create a ticket by clicking the button below!",
        color = discord.Color(0x2B2D31)
    )

    await channel.send(embed=embed, view=open_help_button()) 

asyncio.run(load_extensions())
bot.run(token)
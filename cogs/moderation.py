import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import sqlite3
from datetime import datetime
from typing import Optional

def init_warn_db():
    """Initializes the warnings database and table."""
    conn = sqlite3.connect("warnings.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS warnings (
            user_id INTEGER,
            warning_id TEXT,
            timestamp TEXT,
            reason TEXT,
            moderator_id INTEGER,
            PRIMARY KEY (user_id, warning_id)
        )
    ''')
    conn.commit()
    conn.close()


def add_warning(user_id: int, reason: str, moderator_id: int):
    conn = sqlite3.connect("warnings.db")
    c = conn.cursor()

    now = datetime.now()
    time_str = now.strftime("%d%m%y-%H-%M-%S")

    c.execute(
        "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND timestamp = ?",
        (user_id, time_str)
    )
    count_at_time = c.fetchone()[0]
    increment = count_at_time + 1

    warning_id = f"{time_str}-{increment}"
    timestamp = int(datetime.now().timestamp())

    c.execute(
        "INSERT INTO warnings (user_id, warning_id, timestamp, reason, moderator_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, warning_id, timestamp, reason, moderator_id)
    )

    conn.commit()
    conn.close()



def clear_warning(user_id: int, warning_id: Optional[str] = None) -> bool:
    """Clears a specific warning or all warnings for a user."""
    conn = sqlite3.connect("warnings.db")
    c = conn.cursor()

    if warning_id:
        c.execute(
            "DELETE FROM warnings WHERE user_id = ? AND warning_id = ?",
            (user_id, warning_id)
        )
        deleted = c.rowcount
    else:
        c.execute(
            "DELETE FROM warnings WHERE user_id = ?",
            (user_id,)
        )
        deleted = c.rowcount

    conn.commit()
    conn.close()
    return deleted > 0


def get_warnings(user_id: int):
    conn = sqlite3.connect("warnings.db")
    c = conn.cursor()

    c.execute(
        "SELECT warning_id, timestamp, reason, moderator_id FROM warnings "
        "WHERE user_id = ? ORDER BY warning_id ASC",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

class close_button(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.button):
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

class moderation(commands.GroupCog, name="moderation", description="Moderation commands."):
    def __init__(self, bot):
        self.bot = bot
        super().__init__() 

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_any_role(711303603498778735, 1338561595852460032)
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str) -> None:
        embed = discord.Embed(
        title=f"You have been banned from Politecnico di Torino. | Reason: {reason}",
        description="This is a message to inform you that you have been banned from the server. If you think we made a mistake, please appeal using [this link](https://forms.gle/YQErHaMFDHe81Q5s8).",
        color = discord.Color(0x2B2D31)
        )
        try:
            await user.send(embed=embed)
            await interaction.guild.ban(user, reason=reason)
            await interaction.response.send_message(f"{user.display_name} has been banned successfully. Reason: {reason}")
        except discord.Forbidden:
            await interaction.guild.ban(user, reason=reason)
            await interaction.response.send_message(f"{user.display_name} has been banned successfully (DM message failed to send). Reason: {reason}") 

    @app_commands.command(name="unban", description="Unban a member")
    @app_commands.checks.has_any_role(711303603498778735, 1338561595852460032)
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: str) -> None:
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"{user.display_name} has been unbanned successfully. Reason: {reason}") 

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.checks.has_any_role(711303603498778735, 1338561595852460032)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str) -> None:
        embed = discord.Embed(
            title=f"You have been warned in Politecnico di Torino. | Reason: {reason}",
            description="This is a message to inform you that you have been warned. No further actions needed. If you think we made a mistake, appeal by opening a Help & Support ticket in the server.",
            color = discord.Color(0x2B2D31)
        )
        try:
            await user.send(embed=embed)
            await interaction.response.send_message(f"{user.display_name} has been warned successfully. Reason: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message(f"{user.display_name} has been warned successfully (DM message failed to send). Reason: {reason}")

        add_warning(user.id, reason, interaction.user.id)

    @app_commands.command(name="clearwarn", description="Remove a warning OR all warnings from a member")
    @app_commands.checks.has_any_role(711303603498778735, 1338561595852460032)
    async def clearwarn(self, interaction: discord.Interaction, user: discord.Member, warning_id: Optional[str] = None ) -> None:
        success = clear_warning(user.id, warning_id)
        if success:
            if warning_id:
                await interaction.response.send_message(f"Warning ID {warning_id} for {user.display_name} has been cleared successfully.")
            else:
                await interaction.response.send_message(f"All warnings for {user.display_name} have been cleared successfully.")
        else:
            await interaction.response.send_message(f"No warnings found for {user.display_name} with the provided warning ID.")
    

    @app_commands.command(name="info", description="Moderation info about a member")
    @app_commands.checks.has_any_role(711303603498778735, 1338561595852460032)
    async def info(self, interaction: discord.Interaction, user: discord.Member) -> None:
        roles = [role.mention for role in user.roles if role != interaction.guild.default_role]
        roles_str = ", ".join(roles) if roles else "No roles"

        warnings_data = get_warnings(user.id)
        if warnings_data:
            warnings_formatted = "\n".join(
                f"**ID `{wid}`** — <t:{ts}:F>\n> **Reason**: {reason}\n> **By**: <@{mod_id}>"
                for wid, ts, reason, mod_id in warnings_data
            )
        else:
            warnings_formatted = "*No warnings.*"

        created_ts = int(user.created_at.timestamp())
        joined_ts = int(user.joined_at.timestamp())

        embed = discord.Embed(
            title=f"{user} ({user.id})",
            color=discord.Color(0x2B2D31)
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="Roles", value=roles_str, inline=False)
        embed.add_field(name="Warnings", value=warnings_formatted, inline=False)
        embed.add_field(
            name="Account Creation",
            value=f"<t:{created_ts}:F> (<t:{created_ts}:R>)",
            inline=False
        )
        embed.add_field(
            name="Joined Server",
            value=f"<t:{joined_ts}:F> (<t:{joined_ts}:R>)",
            inline=False
        )

        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="ticket", description="Create a channel private to staff and the specified user")
    @app_commands.checks.has_any_role(711303603498778735, 1338561595852460032)
    async def ticket(self, interaction: discord.Interaction, user: discord.Member) -> None:
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(711303603498778735): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(1338561595852460032): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(f"・{user.name}", overwrites=overwrites)

        embed = discord.Embed(
            title="You have been called here by staff.",
            description="This could be due to a various number of reasons. Please wait for further assistance.",
            color = discord.Color(0x2B2D31)
        )

        await channel.send(f"{interaction.user.mention} has summoned {user.mention}.", embed=embed, view=close_button())
        await interaction.response.send_message(f"Moderation ticket created successfully. Refer to: {channel.mention}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(moderation(bot))
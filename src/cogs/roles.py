
import discord
from websockets import Data
import settings
from cogs.configs import get_config_value
from database import DatabaseManager
from discord.ext import commands
from discord.ui import Button, View
from logic.utilities import get_persistent_message, insert_persistent_message
import emoji

logger = settings.get_logger()


class RoleButton(Button):
    def __init__(self):
        super().__init__(
            custom_id="role_button:primary",
            style=discord.ButtonStyle.primary,
            label="Add Role", emoji="🎮")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        view = MyRoleView(guild, user)
        embed = discord.Embed(title="🎮 Game Roles 🎮", description="==============> 𝗦𝗘𝗟𝗘𝗖𝗧 𝗬𝗢𝗨𝗥 𝗥𝗢𝗟𝗘 <==============",
                              color=discord.Color.from_str(settings.DOURADINHOS_COLOR))
        return await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class MyRoleSelect(discord.ui.Select):
    def __init__(self, guild, user):
        # User can only select roles that they don't have + roles that are not premium
        filtered_roles = [
            role for role in guild.roles if role not in user.roles
            and role.id not in settings.PREMIUM_ROLES.values()
            and emoji.emoji_count(role.name[0]) == 1]

        if len(filtered_roles) == 0:
            roles = [discord.SelectOption(
                label="No roles available", value="0")]
        else:
            roles = [discord.SelectOption(
                label=role.name, value=str(role.id)) for role in filtered_roles]
        super().__init__(
            custom_id="persistent_select:game_roles",
            placeholder="Select a role",
            min_values=1,
            max_values=1,
            options=roles)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_role_id = self.values[0]
        if selected_role_id == "0":
            embed = discord.Embed(title="🎮 Game Roles 🎮",
                                  description="No roles available",
                                  color=discord.Color.from_str(settings.DOURADINHOS_COLOR))
            return await interaction.followup.send(embed=embed, ephemeral=True)

        selected_role = discord.utils.get(
            interaction.guild.roles, id=int(selected_role_id))
        user = interaction.user
        # Add the role to the user
        await user.add_roles(selected_role)
        logger.info(f'{user.display_name} added role {selected_role.name}')

        embed = discord.Embed(title="🎮 Game Roles 🎮", description=f"Role `{selected_role.name}` added!",
                              color=discord.Color.from_str(settings.DOURADINHOS_COLOR))
        await interaction.followup.send(embed=embed, ephemeral=True)


class MyRoleView(discord.ui.View):
    def __init__(self, guild, user):
        super().__init__(timeout=None)
        self.add_item(MyRoleSelect(guild, user))


class Roles(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.logger = settings.logger

    def create_embed(self):
        embed = discord.Embed(title="Game Roles",
                              description="Customiza o teu perfil e escolhe os roles que quiseres de acordo com os teus jogos preferidos.",
                              color=discord.Color.from_str(settings.DOURADINHOS_COLOR))
        embed.set_author(name="Douradinhos",
                         icon_url=settings.DOURADINHOS_AVATAR)
        return embed

    @commands.Cog.listener()
    async def on_ready(self):
        view = View(timeout=None)
        view.add_item(RoleButton())
        self.client.add_view(view)
        channel = self.client.get_channel(get_config_value('ROLES_MESSAGE_CHANNEL'))#settings.ROLES_CHANNEL)
        with DatabaseManager().get_connection() as conn:
            message = get_persistent_message(conn, "roles_message")
            if message is None:
                insert_persistent_message(conn, "roles_message")
                await channel.send(embed=self.create_embed(), view=view)
            else:
                logger.info("Roles message already exists")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Roles(client))

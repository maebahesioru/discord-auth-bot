import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN           = os.environ["DISCORD_TOKEN"]
AUTH_CHANNEL_ID = 1403012659032625203

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


class AuthView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="認証する", style=discord.ButtonStyle.green, custom_id="auth_button")
    async def auth(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "以下のリンクから認証してください：\nhttps://discordauth.hikamer.f5.si/auth",
            ephemeral=True
        )


@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    if ctx.channel.id != AUTH_CHANNEL_ID:
        await ctx.send("認証チャンネルで実行してください。")
        return
    embed = discord.Embed(
        title="認証",
        description="ボタンを押してDiscordアカウントで認証してください。\nヒカマニーズ鯖に参加している場合は認証できません。",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=AuthView())


@bot.event
async def on_ready():
    bot.add_view(AuthView())
    print(f"起動: {bot.user}")


bot.run(TOKEN)

import os
import requests
from flask import Flask, redirect, request
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

CLIENT_ID     = os.environ["DISCORD_CLIENT_ID"]
CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
BOT_TOKEN     = os.environ["DISCORD_TOKEN"]
REDIRECT_URI  = "https://discordauth.hikamer.f5.si/callback"

HIKAMANI_GUILD_ID = "1438479348083720252"
MY_GUILD_ID       = "1369976295395426328"
ROLE_ID           = "1493616469362086009"

OAUTH_URL = (
    f"https://discord.com/oauth2/authorize"
    f"?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    f"&response_type=code&scope=identify+guilds"
)


@app.route("/auth")
def auth():
    return redirect(OAUTH_URL)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "エラー：codeがありません", 400

    # トークン取得
    r = requests.post("https://discord.com/api/oauth2/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    })
    token = r.json().get("access_token")
    if not token:
        return "トークン取得失敗", 400

    headers = {"Authorization": f"Bearer {token}"}

    # ユーザー情報取得
    user = requests.get("https://discord.com/api/users/@me", headers=headers).json()
    user_id = user["id"]

    # 参加サーバー一覧取得
    guilds = requests.get("https://discord.com/api/users/@me/guilds", headers=headers).json()
    guild_ids = [g["id"] for g in guilds]

    if HIKAMANI_GUILD_ID in guild_ids:
        return "❌ ヒカマニーズ鯖に参加しているため認証できません。", 403

    # ロール付与（Bot権限で）
    bot_headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    res = requests.put(
        f"https://discord.com/api/guilds/{MY_GUILD_ID}/members/{user_id}/roles/{ROLE_ID}",
        headers=bot_headers
    )

    if res.status_code in (200, 204):
        return "✅ 認証完了！サーバーに戻ってください。"
    else:
        return f"ロール付与失敗: {res.status_code} {res.text}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

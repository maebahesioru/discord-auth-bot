import discord
from discord.ext import commands
from discord import app_commands
import os, json, asyncio, random, time, threading
from pathlib import Path
import aiohttp
import requests as req_lib
from flask import Flask, redirect, request as flask_request
from dotenv import load_dotenv
load_dotenv()

TOKEN           = os.environ["DISCORD_TOKEN"]
CLIENT_ID       = os.environ["DISCORD_CLIENT_ID"]
CLIENT_SECRET   = os.environ["DISCORD_CLIENT_SECRET"]
AUTH_CHANNEL_ID = 1403012659032625203

REDIRECT_URI      = "https://discordauth.hikamer.f5.si/callback"
HIKAMANI_GUILD_ID = "1438479348083720252"
MY_GUILD_ID       = "1369976295395426328"
ROLE_ID           = "1493616469362086009"
OAUTH_URL = (
    f"https://discord.com/oauth2/authorize"
    f"?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    f"&response_type=code&scope=identify+guilds"
)

TWITTER_CHANNEL_ID = int(os.environ.get("TWITTER_CHANNEL_ID", "1494904804533600326"))
SPACE_CHANNEL_ID   = int(os.environ.get("SPACE_CHANNEL_ID", "1494905257510047868"))
HANDLE_TXT         = Path(os.environ.get("HANDLE_TXT", r"data/handle.txt"))
STATE_PATH         = Path("data/state.json")
COOLDOWNS_PATH     = Path("data/cooldowns.json")
SPACE_SEEN_PATH    = Path("data/space_seen.json")
INTERVAL_SEC       = 5 * 60
COOLDOWN_SEC       = 30 * 60
FX_RETRIES         = max(1, int(os.environ.get("FXTWITTER_FETCH_RETRIES", 5)))
FX_RETRY_BASE_MS   = max(50, int(os.environ.get("FXTWITTER_RETRY_BASE_MS", 500)))
YAHOO_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
YAHOO_HEADERS = {"User-Agent": YAHOO_UA, "Accept": "application/json, text/plain, */*", "Referer": "https://search.yahoo.co.jp/realtime/search"}

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]

NUM_MILESTONES = [
    100,200,300,400,500,600,700,800,900,1000,
    2000,3000,4000,5000,6000,7000,8000,9000,10000,
    20000,30000,40000,50000,60000,70000,80000,90000,100000,
    200000,300000,500000,1000000,2000000,5000000,10000000,
]
AGE_MILESTONES = [100,200,365,500,730,1000,1500,2000,3000,5000]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ── Flask認証サーバー ─────────────────────────────────────

flask_app = Flask(__name__)

@flask_app.route("/auth")
def auth():
    return redirect(OAUTH_URL)

@flask_app.route("/callback")
def callback():
    code = flask_request.args.get("code")
    if not code:
        return "エラー：codeがありません", 400

    r = req_lib.post("https://discord.com/api/oauth2/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
    })
    token = (r.json() if r.text else {}).get("access_token")
    if not token:
        return "認証に失敗しました。もう一度 <a href='/auth'>こちら</a> からやり直してください。", 400

    headers = {"Authorization": f"Bearer {token}"}
    user_id = req_lib.get("https://discord.com/api/users/@me", headers=headers).json()["id"]
    guild_ids = [g["id"] for g in req_lib.get("https://discord.com/api/users/@me/guilds", headers=headers).json()]

    if HIKAMANI_GUILD_ID in guild_ids:
        return """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#2b2d31;color:#fff}div{text-align:center;padding:2rem}</style></head>
<body><div><p style="font-size:2rem">❌</p><p>ヒカマニーズ鯖に参加しているため認証できません。</p>
<p>抜けたくない場合は<a href="https://discord.com/channels/1369976295395426328/1493885237330051112" style="color:#5865f2">こちら</a>で要相談。</p></div></body></html>""", 403

    res = req_lib.put(
        f"https://discord.com/api/guilds/{MY_GUILD_ID}/members/{user_id}/roles/{ROLE_ID}",
        headers={"Authorization": f"Bot {TOKEN}"}
    )
    if res.status_code in (200, 204):
        return """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#2b2d31;color:#fff}div{text-align:center;padding:2rem}</style></head>
<body><div><p style="font-size:2rem">✅</p><p>認証完了！</p><p>Discordに戻ってください。</p></div></body></html>"""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#2b2d31;color:#fff}}div{{text-align:center;padding:2rem}}</style></head>
<body><div><p style="font-size:2rem">⚠️</p><p>ロール付与失敗: {res.status_code}</p></div></body></html>""", 500

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000)

# ── Discord認証ボタン ─────────────────────────────────────

class AuthView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="認証する", style=discord.ButtonStyle.green, custom_id="auth_button")
    async def auth(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "以下のリンクから認証してください：\nhttps://discordauth.hikamer.f5.si/auth",
            ephemeral=True
        )


@bot.tree.command(name="setup", description="認証パネルを送信する")
@app_commands.default_permissions(administrator=True)
async def slash_setup(interaction: discord.Interaction):
    if interaction.channel_id != AUTH_CHANNEL_ID:
        await interaction.response.send_message("認証チャンネルで実行してください。", ephemeral=True)
        return
    embed = discord.Embed(
        title="認証",
        description="ボタンを押してDiscordアカウントで認証してください。\nヒカマニーズ鯖に参加している場合は認証できません。",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=AuthView())

# ── Twitter監視機能 ───────────────────────────────────────


def load_json(path: Path) -> dict:
    return json.loads(path.read_text("utf-8")) if path.exists() else {}

def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

def age_days(joined: str) -> int:
    if not joined:
        return 0
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(joined.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return 0

def crossed_milestones(prev: int, curr: int, ms: list) -> list:
    return [m for m in ms if prev < m <= curr]

def normalize_desc(desc: str, website_url: str | None) -> str:
    if not website_url:
        return desc
    return desc.replace(website_url.rstrip("/"), "").rstrip("/").rstrip()

async def fetch_account(session: aiohttp.ClientSession, username: str) -> dict | None:
    url = f"https://api.fxtwitter.com/{username}"
    for attempt in range(FX_RETRIES):
        try:
            headers = {"User-Agent": random.choice(UA_POOL)}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as res:
                if res.status == 200:
                    try:
                        j = await res.json(content_type=None)
                    except Exception:
                        return _dead(username)
                    if j.get("code") != 200 or not j.get("user"):
                        return _dead(username)
                    u = j["user"]
                    joined = u.get("joined", "")
                    return {
                        "id": u.get("id", ""),
                        "name": u.get("name", username),
                        "screen_name": u.get("screen_name", username),
                        "alive": True,
                        "protected": u.get("protected", False),
                        "verified": (u.get("verification") or {}).get("verified", False),
                        "verification_type": (u.get("verification") or {}).get("type"),
                        "source": (u.get("about_account") or {}).get("source", ""),
                        "followers": u.get("followers", 0),
                        "following": u.get("following", 0),
                        "tweets": u.get("tweets", 0),
                        "likes": u.get("likes", 0),
                        "media_count": u.get("media_count", 0),
                        "description": normalize_desc(u.get("description", ""), (u.get("website") or {}).get("url")),
                        "location": u.get("location", ""),
                        "website_url": ((u.get("website") or {}).get("url") or "").rstrip("/") or None,
                        "banner_url": u.get("banner_url"),
                        "avatar_url": (u.get("avatar_url") or "").replace("_normal", "") or None,
                        "joined": joined,
                        "username_changes_count": ((u.get("about_account") or {}).get("username_changes") or {}).get("count", 0),
                        "username_changes_last": ((u.get("about_account") or {}).get("username_changes") or {}).get("last_changed_at", ""),
                        "age_days": age_days(joined),
                        "based_in": (u.get("about_account") or {}).get("based_in", ""),
                    }
                retryable = res.status == 429 or 500 <= res.status <= 599
                if retryable and attempt < FX_RETRIES - 1:
                    ra_header = res.headers.get("Retry-After")
                    ra_sec = None
                    if ra_header:
                        try:
                            v = int(ra_header.strip())
                            if v >= 0:
                                ra_sec = min(v, 120)
                        except ValueError:
                            pass
                    backoff = ra_sec if ra_sec is not None else min(FX_RETRY_BASE_MS * (2 ** attempt), 30000) / 1000
                    await asyncio.sleep(backoff + random.random() * 0.3)
                    continue
                return _dead(username)  # 非retryableエラー（403, 404等）はdead扱い
        except Exception:
            if attempt >= FX_RETRIES - 1:
                return None
            await asyncio.sleep(min(FX_RETRY_BASE_MS * (2 ** attempt), 30000) / 1000)
    return None

def _dead(username: str) -> dict:
    return {"name": username, "screen_name": username, "alive": False,
            "id": "", "protected": False, "verified": False, "verification_type": None,
            "source": "", "followers": 0, "following": 0, "tweets": 0, "likes": 0,
            "media_count": 0, "description": "", "location": "",
            "website_url": None, "banner_url": None, "avatar_url": None,
            "joined": "", "username_changes_count": 0, "username_changes_last": "",
            "age_days": 0, "based_in": ""}

def merge_with_prev(prev: dict | None, curr: dict) -> dict:
    if not prev or not curr.get("alive"):
        return curr
    m = dict(curr)
    if not m.get("source") and prev.get("source"):
        m["source"] = prev["source"]
    if not m.get("based_in") and prev.get("based_in"):
        m["based_in"] = prev["based_in"]
    if m["username_changes_count"] < prev["username_changes_count"]:
        m["username_changes_count"] = prev["username_changes_count"]
        m["username_changes_last"] = prev["username_changes_last"]
    elif (m["username_changes_count"] == prev["username_changes_count"]
          and not m.get("username_changes_last") and prev.get("username_changes_last")):
        m["username_changes_last"] = prev["username_changes_last"]
    return m

def diff(username: str, prev: dict, curr: dict) -> list[dict]:
    changes = []
    tag = f"{curr.get('name') or prev.get('name')}(@{username})"
    meta = {"name": curr.get("name") or prev.get("name"), "username": username, "avatar": curr.get("avatar_url")}

    def c(text, color=0x5865F2, image_url=None, cooldown_key=None):
        changes.append({"text": text, "color": color, "imageUrl": image_url,
                         "cooldownKey": cooldown_key, **meta})

    if prev.get("alive") and not curr.get("alive"):
        c(f"{tag}が凍結または垢消し"); return changes
    if not prev.get("alive") and curr.get("alive"):
        c(f"{tag}が復活")
    if not curr.get("alive"):
        return changes

    if prev["name"] != curr["name"]:
        c(f"{tag}が表示名変更: {prev['name']} → {curr['name']}")
    if prev["screen_name"] != curr["screen_name"]:
        c(f"{tag}がユーザー名変更: @{prev['screen_name']} → @{curr['screen_name']}")
    if curr["username_changes_count"] > prev["username_changes_count"]:
        date = f" ({curr['username_changes_last']})" if curr.get("username_changes_last") else ""
        c(f"{tag}のユーザー名変更回数: {prev['username_changes_count']} → {curr['username_changes_count']}回{date}")

    if not prev["protected"] and curr["protected"]:  c(f"{tag}が鍵垢に")
    if prev["protected"] and not curr["protected"]:  c(f"{tag}が鍵垢解除")
    if not prev["verified"] and curr["verified"]:    c(f"{tag}が認証バッジ取得 ({curr.get('verification_type') or '不明'})")
    if prev["verified"] and not curr["verified"]:    c(f"{tag}が認証バッジ喪失")
    if prev["verified"] and curr["verified"] and prev["verification_type"] != curr["verification_type"]:
        c(f"{tag}のバッジ種別変更: {prev['verification_type']} → {curr['verification_type']}")
    if curr.get("source") and prev.get("source") != curr.get("source"):
        c(f"{tag}の最終クライアント変更: {prev.get('source') or '不明'} → {curr['source']}")

    for field, label in [("followers","フォロワー"),("following","フォロー"),("tweets","ツイート"),("likes","いいね"),("media_count","メディア")]:
        hit = crossed_milestones(prev[field], curr[field], NUM_MILESTONES)
        if hit:
            c(f"{tag}の{label}が{', '.join(f'{m:,}' for m in hit)}を突破 (現在: {curr[field]:,})")

    if curr.get("joined"):
        hit = crossed_milestones(prev["age_days"], curr["age_days"], AGE_MILESTONES)
        if hit:
            labels = [f"{d//365}周年" if d % 365 == 0 else f"{d}日" for d in hit]
            c(f"{tag}のアカウントが{'、'.join(labels)}")

    if prev["description"] != curr["description"]:
        c(f"{tag}のbioが変更\n変更前: {prev['description'] or 'なし'}\n変更後: {curr['description'] or 'なし'}", cooldown_key=f"{username}:description")
    if prev["location"] != curr["location"]:
        c(f"{tag}の場所が変更: \"{prev['location'] or 'なし'}\" → \"{curr['location'] or 'なし'}\"", cooldown_key=f"{username}:location")
    if prev["website_url"] != curr["website_url"]:
        if not curr["website_url"]:
            c(f"{tag}のプロフィールURLを削除 (元: {prev['website_url']})", cooldown_key=f"{username}:website_url")
        else:
            c(f"{tag}のプロフィールURLが変更: {prev['website_url'] or 'なし'} → {curr['website_url']}", cooldown_key=f"{username}:website_url")
    if prev["banner_url"] != curr["banner_url"]:
        if curr["banner_url"]: c(f"{tag}のヘッダーが変更", image_url=curr["banner_url"])
        else: c(f"{tag}のヘッダーを削除")
    if prev["avatar_url"] != curr["avatar_url"] and curr.get("avatar_url"):
        c(f"{tag}のアイコンが変更", image_url=curr["avatar_url"])
    if curr.get("based_in") and prev.get("based_in") != curr.get("based_in"):
        c(f"{tag}の居住国が変更: {prev.get('based_in') or '不明'} → {curr['based_in']}")

    for field, label, threshold in [("followers","フォロワー",50),("following","フォロー",50),("tweets","ツイート",50),("media_count","メディア",50)]:
        p, n = prev[field], curr[field]
        if n < p:
            d = p - n
            if d >= threshold and round(d / p * 100) >= 10:
                c(f"{tag}の{label}が大幅減少: {p:,} → {n:,} (-{d:,})")
    p, n = prev["likes"], curr["likes"]
    if n < p:
        d = p - n
        if d >= 100 and round(d / p * 100) >= 10:
            c(f"{tag}のいいねが大幅減少: {p:,} → {n:,} (-{d:,})")

    return changes

async def send_change_embed(channel: discord.TextChannel, change: dict):
    embed = discord.Embed(description=change["text"], color=change.get("color", 0x5865F2))
    if change.get("name") and change.get("username"):
        kwargs = {"name": f"{change['name']} (@{change['username']})"}
        if change.get("avatar"):
            kwargs["icon_url"] = change["avatar"]
        embed.set_author(**kwargs)
    if change.get("imageUrl"):
        embed.set_image(url=change["imageUrl"])
    await channel.send(embeds=[embed])

async def notify(channel: discord.TextChannel, all_changes: list[dict]):
    cooldowns = load_json(COOLDOWNS_PATH)
    now = time.time()
    grouped: dict[str, list] = {}
    ungrouped = []

    for ch in all_changes:
        if ch.get("cooldownKey"):
            if now - cooldowns.get(ch["cooldownKey"], 0) < COOLDOWN_SEC:
                continue
            cooldowns[ch["cooldownKey"]] = now
        if ch.get("username"):
            grouped.setdefault(ch["username"], []).append(ch)
        else:
            ungrouped.append(ch)

    save_json(COOLDOWNS_PATH, cooldowns)

    for changes in grouped.values():
        first = changes[0]
        image_url = next((c["imageUrl"] for c in changes if c.get("imageUrl")), None)
        text = "\n".join(c["text"] for c in changes)
        await send_change_embed(channel, {**first, "text": text, "imageUrl": image_url})
    for ch in ungrouped:
        await send_change_embed(channel, ch)

_last_check: float | None = None
_next_check: float | None = None
_monitoring_count = 0

async def run_check():
    global _last_check, _monitoring_count
    usernames = [l.strip() for l in HANDLE_TXT.read_text("utf-8").splitlines() if l.strip()]
    _monitoring_count = len(usernames)

    prev_state = load_json(STATE_PATH)
    is_first = not prev_state
    new_state: dict = {}
    all_changes: list[dict] = []

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch_account(session, u) for u in usernames])

    for username, curr in zip(usernames, results):
        if curr is None:
            continue
        prev = prev_state.get(username)
        merged = merge_with_prev(prev, curr)
        new_state[username] = merged
        if not is_first:
            if prev:
                changes = diff(username, prev, merged)
                all_changes.extend(changes)
                # ユーザー名変更を検知したらhandle.txtを自動更新
                if merged.get("alive") and merged["screen_name"] != username:
                    new_handle = merged["screen_name"]
                    lines = HANDLE_TXT.read_text("utf-8").splitlines()
                    lines = [new_handle if l.strip() == username else l for l in lines]
                    HANDLE_TXT.write_text("\n".join(lines) + "\n", "utf-8")
                    print(f"[handle] {username} → {new_handle} に更新")
            elif not merged.get("alive"):
                all_changes.append({"text": f"**{username}** 🆕 新規追加（ステータス: 消えています）"})

    if not is_first:
        prev_alive = sum(1 for s in prev_state.values() if s.get("alive"))
        disappeared = sum(1 for c in all_changes if "凍結または垢消し" in c["text"])
        if prev_alive > 0 and disappeared / prev_alive >= 0.3:
            print(f"⚠️ {disappeared}件が同時消滅 - fxtwitterダウンの可能性があるため通知をスキップ")
            return

    save_json(STATE_PATH, new_state)
    _last_check = time.time()

    if not all_changes:
        print(f"[{time.strftime('%H:%M:%S')}] {'初回: 状態保存完了' if is_first else '変化なし'}")
        return

    channel = bot.get_channel(TWITTER_CHANNEL_ID)
    if channel:
        await notify(channel, all_changes)
    print(f"[{time.strftime('%H:%M:%S')}] {len(all_changes)} 件通知")

# ── スペース監視機能 ──────────────────────────────────────

import urllib.parse as _urlparse
import re as _re

async def fetch_yahoo_spaces(session: aiohttp.ClientSession, handles: list[str]) -> list[dict]:
    """handle.txtのユーザーを50件ずつ分割してYahoo APIで検索し、スペースURLを含むツイートを返す"""
    results = []
    chunk_size = 150
    chunks = [handles[i:i+chunk_size] for i in range(0, len(handles), chunk_size)]

    async def fetch_chunk(chunk):
        or_part = " OR ".join(f"ID:{h}" for h in chunk)
        q = _urlparse.quote(f"({or_part}) (URL:x.com/i/spaces OR URL:twitter.com/i/spaces)")
        url = f"https://search.yahoo.co.jp/realtime/api/v1/pagination?p={q}&md=t&results=40"
        try:
            async with session.get(url, headers=YAHOO_HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as res:
                if res.status != 200:
                    return []
                j = await res.json(content_type=None)
                return j.get("timeline", {}).get("entry", [])
        except Exception:
            return []

    entries_list = await asyncio.gather(*[fetch_chunk(c) for c in chunks])
    for entries in entries_list:
        results.extend(entries)
    return results

def clean_text(text: str) -> str:
    return _re.sub(r'\tSTART\t|\tEND\t', '', text).strip()

async def run_space_check():
    handles = [l.strip() for l in HANDLE_TXT.read_text("utf-8").splitlines() if l.strip()]
    seen = load_json(SPACE_SEEN_PATH)
    is_first = not seen

    async with aiohttp.ClientSession() as session:
        entries = await fetch_yahoo_spaces(session, handles)

    channel = bot.get_channel(SPACE_CHANNEL_ID)
    if not channel and not is_first:
        return

    new_seen = dict(seen)
    for entry in entries:
        tweet_id = entry.get("id", "")
        if not tweet_id or tweet_id in seen:
            continue
        space_url = None
        for u in entry.get("urls", []):
            eu = u.get("expandedUrl", "")
            if "/i/spaces/" in eu:
                space_url = eu
                break
        new_seen[tweet_id] = True
        if not space_url or is_first:
            continue

        name = entry.get("name", entry.get("screenName", ""))
        screen_name = entry.get("screenName", "")
        avatar = entry.get("profileImage", "")
        text = clean_text(entry.get("displayText", ""))
        for u in entry.get("urls", []):
            text = text.replace(u.get("url", ""), "").strip()
        badge = entry.get("badge", {})
        color = 0x1DA1F2 if badge.get("type") == "blue" else 0xDBAB00 if badge.get("type") == "business" else 0x5865F2

        embed = discord.Embed(description=f"{text}\n\n🎙️ {space_url}", color=color, url=space_url)
        embed.set_author(name=f"{name} (@{screen_name})", icon_url=avatar, url=f"https://x.com/{screen_name}")
        await channel.send(embeds=[embed])

    save_json(SPACE_SEEN_PATH, new_seen)
    if is_first:
        print(f"[space] 初回: {len(new_seen)}件を既読としてスキップ")

async def twitter_monitor_loop():
    global _next_check
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await run_check()
        except Exception as e:
            print(f"[monitor] エラー: {e}")
        _next_check = time.time() + INTERVAL_SEC
        await asyncio.sleep(INTERVAL_SEC)

async def space_monitor_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await run_space_check()
        except Exception as e:
            print(f"[space] エラー: {e}")
        await asyncio.sleep(INTERVAL_SEC)

# ── スラッシュコマンド ─────────────────────────────────────

@bot.tree.command(name="ping", description="Botの応答速度を確認")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="status", description="監視状況を確認")
async def slash_status(interaction: discord.Interaction):
    last = f"<t:{int(_last_check)}:R>" if _last_check else "未実行"
    nxt  = f"<t:{int(_next_check)}:R>" if _next_check else "不明"
    await interaction.response.send_message(
        f"📊 監視件数: **{_monitoring_count}件**\n前回チェック: {last}\n次回チェック: {nxt}"
    )

@bot.tree.command(name="check", description="今すぐ全件チェックを実行")
@app_commands.default_permissions(administrator=True)
async def slash_check(interaction: discord.Interaction):
    await interaction.response.defer()
    await run_check()
    await interaction.followup.send("✅ チェック完了")

@bot.tree.command(name="account", description="アカウントの現在状態を確認")
@app_commands.describe(username="Twitterユーザー名 (@なし)")
async def slash_account(interaction: discord.Interaction, username: str):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        curr = await fetch_account(session, username.strip())
    if not curr or not curr.get("alive"):
        await interaction.followup.send(f"@{username} は取得できませんでした（凍結・削除・存在しない可能性）")
        return
    state = load_json(STATE_PATH)
    in_csv = username in state
    embed = discord.Embed(
        title=f"{curr['name']} (@{curr['screen_name']})",
        url=f"https://x.com/{curr['screen_name']}",
        color=0x5865F2
    )
    if curr.get("avatar_url"):  embed.set_thumbnail(url=curr["avatar_url"])
    if curr.get("banner_url"):  embed.set_image(url=curr["banner_url"])
    embed.add_field(name="監視対象", value="✅ CSV内" if in_csv else "❌ CSV外", inline=True)
    embed.add_field(name="ID", value=curr["id"] or "不明", inline=True)
    embed.add_field(name="鍵垢", value="あり" if curr["protected"] else "なし", inline=True)
    embed.add_field(name="認証", value=f"あり ({curr['verification_type']})" if curr["verified"] else "なし", inline=True)
    embed.add_field(name="フォロワー", value=f"{curr['followers']:,}", inline=True)
    embed.add_field(name="フォロー", value=f"{curr['following']:,}", inline=True)
    embed.add_field(name="ツイート", value=f"{curr['tweets']:,}", inline=True)
    embed.add_field(name="いいね", value=f"{curr['likes']:,}", inline=True)
    embed.add_field(name="メディア", value=f"{curr['media_count']:,}", inline=True)
    embed.add_field(name="居住国", value=curr.get("based_in") or "不明", inline=True)
    embed.add_field(name="クライアント", value=curr.get("source") or "不明", inline=True)
    uc = curr["username_changes_count"]
    ul = f"\n(最終: {curr['username_changes_last']})" if curr.get("username_changes_last") else ""
    embed.add_field(name="ユーザー名変更", value=f"{uc}回{ul}", inline=True)
    embed.add_field(name="アカウント経過", value=f"{curr['age_days']}日\n({curr['joined']})", inline=True)
    embed.add_field(name="bio", value=curr.get("description") or "なし", inline=False)
    embed.add_field(name="場所", value=curr.get("location") or "なし", inline=True)
    embed.add_field(name="プロフィールURL", value=curr.get("website_url") or "なし", inline=True)
    await interaction.followup.send(embeds=[embed])

# ── 起動 ─────────────────────────────────────────────────

@bot.event
async def on_ready():
    bot.add_view(AuthView())
    await bot.tree.sync()
    print(f"起動: {bot.user}")
    threading.Thread(target=run_flask, daemon=True).start()
    bot.loop.create_task(twitter_monitor_loop())
    bot.loop.create_task(space_monitor_loop())


bot.run(TOKEN)

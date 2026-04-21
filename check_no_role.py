"""
ヒカマニーズ鯖:
1. 認証ロールなし & ヒカマニーズ鯖参加者リスト（オンライン状態付き）
2. 過去24時間の全チャンネルの会話エクスポート
"""
import asyncio
import discord
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

MY_GUILD_ID       = 1369976295395426328
HIKAMANI_GUILD_ID = 1438479348083720252
AUTH_ROLE_ID      = 1493616469362086009

MAIN_TOKEN    = os.environ["DISCORD_TOKEN"]
WATCHER_TOKEN = os.environ["HIKAMANI_WATCH_TOKEN"]

STATUS_LABEL = {
    discord.Status.online:    "🟢 オンライン",
    discord.Status.idle:      "🌙 退席中",
    discord.Status.dnd:       "🔴 取り込み中",
    discord.Status.offline:   "⚫ オフライン",
    discord.Status.invisible: "⚫ オフライン",
}

async def main():
    main_client = discord.Client(intents=discord.Intents(members=True, guilds=True))
    intents = discord.Intents(members=True, guilds=True, presences=True, message_content=True, messages=True)
    watcher = discord.Client(intents=intents, chunk_guilds_at_startup=True)

    has_role: set[int] = set()
    hikamani: dict[int, tuple[str, discord.Status]] = {}

    @main_client.event
    async def on_ready():
        guild = main_client.get_guild(MY_GUILD_ID)
        role  = guild.get_role(AUTH_ROLE_ID)
        async for member in guild.fetch_members(limit=None):
            if not member.bot and role in member.roles:
                has_role.add(member.id)
        print(f"ヒカマーニチ鯖 認証ロールあり: {len(has_role)}人")
        await main_client.close()

    @watcher.event
    async def on_ready():
        guild = watcher.get_guild(HIKAMANI_GUILD_ID)
        if not guild:
            print("ヒカマニーズ鯖が見つかりません")
            await watcher.close()
            return

        # メンバー情報取得
        await guild.chunk()
        for member in guild.members:
            if not member.bot:
                hikamani[member.id] = (f"{member.display_name} (@{member.name})", member.status)
        online = sum(1 for _, s in hikamani.values() if s not in (discord.Status.offline, discord.Status.invisible))
        print(f"ヒカマニーズ鯖メンバー: {len(hikamani)}人 (オンライン: {online}人)")

        # 過去24時間のメッセージエクスポート
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        all_messages: list[str] = []

        for channel in guild.text_channels:
            try:
                msgs = []
                async for msg in channel.history(after=since, limit=None, oldest_first=True):
                    ts = msg.created_at.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
                    content = msg.content or "[添付ファイル/Embed]"
                    msgs.append(f"  [{ts}] {msg.author.display_name}: {content}")
                if msgs:
                    all_messages.append(f"\n=== #{channel.name} ===")
                    all_messages.extend(msgs)
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"[{channel.name}] エラー: {e}")

        now_str = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d_%H%M%S")
        export_path = f"hikamani_export_{now_str}.txt"
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(f"ヒカマニーズ鯖 過去24時間のログ ({now_str})\n")
            f.write("\n".join(all_messages))
        print(f"エクスポート完了: {export_path} ({len(all_messages)}行)")

        await watcher.close()

    await asyncio.gather(
        main_client.start(MAIN_TOKEN),
        watcher.start(WATCHER_TOKEN),
    )

    # 認証ロールなしリスト出力
    result = {uid: v for uid, v in hikamani.items() if uid not in has_role}
    print(f"\n認証ロールなし該当者: {len(result)}人")
    with open("no_role_in_hikamani.txt", "w", encoding="utf-8") as f:
        for name, status in sorted(result.values(), key=lambda x: x[0]):
            label = STATUS_LABEL.get(status, "⚫ オフライン")
            f.write(f"{label} {name}\n")
    print("no_role_in_hikamani.txt に出力しました")

asyncio.run(main())

# -*- coding: utf-8 -*-
"""LINEに通知を送る"""
import json
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "line_config.json"
BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"


def send_line(text):
    """友だち全員(=自分)にLINEでメッセージを送る"""
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    token = config["channel_access_token"]
    body = json.dumps({"messages": [{"type": "text", "text": text}]}).encode("utf-8")
    req = urllib.request.Request(
        BROADCAST_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        return res.status


if __name__ == "__main__":
    print(send_line("rocky9-webからのテスト通知です"))

# -*- coding: utf-8 -*-
"""サーバーの状態をチェックして、変化があればLINEに通知するスクリプト"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

import psutil

from notify import send_line

BASE_DIR = Path(__file__).resolve().parent
STATUS_FILE = BASE_DIR / "status.json"
ALERT_LOG = BASE_DIR / "alerts.log"

# 見張るサービスの一覧
SERVICES = ["nginx", "kakeibo", "sshd"]

# これ以上になったら「異常」とみなす使用率(%)
THRESHOLDS = {"cpu": 80, "memory": 80, "disk": 80}
LABELS = {"cpu": "CPU", "memory": "メモリ", "disk": "ディスク"}


def service_status(name):
    """systemctl is-active でサービスの状態を調べる"""
    r = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True)
    return r.stdout.strip()


def collect():
    """今のサーバーの状態を集める"""
    return {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent,
        "services": {s: service_status(s) for s in SERVICES},
    }


def find_problems(status):
    """異常を {種類: メッセージ} の形で返す"""
    problems = {}
    for key, limit in THRESHOLDS.items():
        if status[key] >= limit:
            problems[key] = f"{LABELS[key]}使用率が{status[key]}%です(しきい値{limit}%)"
    for name, state in status["services"].items():
        if state != "active":
            problems[f"service:{name}"] = f"{name}が停止しています(状態: {state})"
    return problems


def load_previous_problems():
    """前回のチェック結果から、異常の一覧を読み込む"""
    try:
        prev = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        return prev.get("problem_map", {})
    except Exception:
        return {}


def write_alert_log(line):
    with ALERT_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def notify_changes(prev, now, checked_at):
    """前回と比べて、増えた異常・消えた異常だけを通知する"""
    messages = []
    for key in now.keys() - prev.keys():
        messages.append(f"⚠ 異常発生\n{now[key]}")
    for key in prev.keys() - now.keys():
        messages.append(f"✅ 復旧\n{prev[key]} → 正常に戻りました")
    for m in messages:
        write_alert_log(f"[{checked_at}] " + m.replace("\n", " "))
        try:
            send_line(f"【rocky9-web】{checked_at}\n{m}")
        except Exception as e:
            write_alert_log(f"[{checked_at}] LINE送信に失敗: {e}")


def main():
    prev = load_previous_problems()
    status = collect()
    problem_map = find_problems(status)
    status["problem_map"] = problem_map
    status["problems"] = list(problem_map.values())
    notify_changes(prev, problem_map, status["checked_at"])
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

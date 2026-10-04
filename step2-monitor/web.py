# -*- coding: utf-8 -*-
"""監視ダッシュボードの画面"""
import json
from pathlib import Path

from flask import Flask, render_template_string

BASE_DIR = Path(__file__).resolve().parent
STATUS_FILE = BASE_DIR / "status.json"

app = Flask(__name__)

PAGE = """
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<title>rocky9-web 監視</title>
<style>
  body { font-family: sans-serif; max-width: 800px; margin: 2em auto; padding: 0 1em; }
  .cards { display: flex; gap: 12px; }
  .card { flex: 1; background: #f3f3f3; border-radius: 8px; padding: 12px; }
  .num { font-size: 1.6em; }
  .bar { height: 6px; background: #ddd; border-radius: 3px; margin-top: 6px; }
  .fill { height: 6px; border-radius: 3px; background: #3b8d3b; }
  .fill.warn { background: #c0392b; }
  table { border-collapse: collapse; width: 100%; }
  td { border-bottom: 1px solid #ddd; padding: 8px; }
  .ok { color: #3b8d3b; }
  .ng { color: #c0392b; font-weight: bold; }
</style>
</head>
<body>
<h1>rocky9-web 監視</h1>
{% if error %}
  <p class="ng">{{ error }}</p>
{% else %}
  <p>最終チェック {{ s.checked_at }}(60秒ごとに自動更新)</p>

  <div class="cards">
  {% for key, label in [("cpu", "CPU"), ("memory", "メモリ"), ("disk", "ディスク /")] %}
    <div class="card">
      <div>{{ label }}</div>
      <div class="num">{{ s[key] }}%</div>
      <div class="bar"><div class="fill {% if s[key] >= 80 %}warn{% endif %}" style="width: {{ s[key] }}%"></div></div>
    </div>
  {% endfor %}
  </div>

  <h2>サービスの状態</h2>
  <table>
  {% for name, state in s.services.items() %}
    <tr>
      <td>{{ name }}</td>
      <td class="{{ 'ok' if state == 'active' else 'ng' }}">
        {{ '稼働中' if state == 'active' else '停止(' ~ state ~ ')' }}
      </td>
    </tr>
  {% endfor %}
  </table>

  <h2>異常</h2>
  {% if s.problems %}
    <ul>{% for p in s.problems %}<li class="ng">{{ p }}</li>{% endfor %}</ul>
  {% else %}
    <p class="ok">異常はありません</p>
  {% endif %}
{% endif %}
</body>
</html>
"""


@app.route("/")
def index():
    try:
        status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        error = None
    except Exception as e:
        status = None
        error = f"状態ファイルを読み込めませんでした: {e}"
    return render_template_string(PAGE, s=status, error=error)

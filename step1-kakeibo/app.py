# -*- coding: utf-8 -*-
"""PayPay家計簿 Web版の画面部分"""
from flask import Flask, request, render_template_string

from kakeibo_core import summarize

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # アップロードは5MBまで

PAGE = """
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>PayPay家計簿</title>
<style>
  body { font-family: sans-serif; max-width: 960px; margin: 2em auto; padding: 0 1em; }
  table { border-collapse: collapse; margin: 1em 0; }
  th, td { border: 1px solid #ccc; padding: 4px 10px; text-align: right; }
  th { background: #1F4E78; color: #fff; }
  .note { color: #666; font-size: 0.9em; }
  .err { color: #c00; }
</style>
</head>
<body>
<h1>PayPay家計簿</h1>
<form action="/upload" method="post" enctype="multipart/form-data">
  <input type="file" name="csv" accept=".csv">
  <button type="submit">集計する</button>
</form>
<p class="note">※アップロードしたCSVはサーバーに保存されません。運用・獲得に関する取引は除外して集計します。</p>

{% if error %}<p class="err">{{ error }}</p>{% endif %}

{% if result %}
  <p>読み込み {{ result.total_rows }}行 / 除外 {{ result.excluded }}行 / 集計対象 {{ result.count }}件</p>
  {% if result.monthly_html %}
    <h2>月別・カテゴリ別</h2>
    {{ result.monthly_html | safe }}
    <h2>カテゴリ別合計</h2>
    {{ result.category_html | safe }}
  {% else %}
    <p>集計できる支出がありませんでした。</p>
  {% endif %}
{% endif %}
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE, result=None, error=None)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("csv")
    if not f or f.filename == "":
        return render_template_string(PAGE, result=None, error="CSVファイルを選んでください。")
    try:
        result = summarize(f.read())
    except Exception as e:
        return render_template_string(PAGE, result=None, error=f"集計できませんでした: {e}")
    return render_template_string(PAGE, result=result, error=None)

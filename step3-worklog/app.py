from datetime import datetime

from flask import Flask, abort, redirect, render_template, request, url_for

from db import get_conn, init_db

app = Flask(__name__)
init_db()  # 起動時に、データベースとテーブルがなければ作る

KINDS = ["障害", "作業", "改善"]
STATUSES = ["対応中", "完了"]
FIELDS = ["occurred_at", "kind", "title", "event", "impact", "cause", "action", "prevention", "status"]


def read_form():
    """入力画面から送られてきた値を取り出し、正しいかチェックする"""
    data = {f: request.form.get(f, "").strip() for f in FIELDS}
    errors = []

    # 日時の入力欄からは "2026-10-06T22:42" の形で届くので、保存用に "2026-10-06 22:42" に直す
    data["occurred_at"] = data["occurred_at"].replace("T", " ")
    try:
        datetime.strptime(data["occurred_at"], "%Y-%m-%d %H:%M")
    except ValueError:
        errors.append("発生日時を正しく入力してください")

    if data["kind"] not in KINDS:
        errors.append("種別を選んでください")
    if data["status"] not in STATUSES:
        errors.append("ステータスを選んでください")
    if not data["title"]:
        errors.append("タイトルを入力してください")

    return data, errors


@app.route("/")
def index():
    """一覧画面:種別・ステータスで絞り込みできる"""
    kind = request.args.get("kind", "")
    status = request.args.get("status", "")

    sql = "SELECT id, occurred_at, kind, status, title FROM records WHERE 1=1"
    params = []
    if kind in KINDS:
        sql += " AND kind = ?"
        params.append(kind)
    if status in STATUSES:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY occurred_at DESC, id DESC"

    conn = get_conn()
    records = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template(
        "index.html",
        records=records,
        kinds=KINDS,
        statuses=STATUSES,
        kind=kind,
        status=status,
    )


@app.route("/records/<int:record_id>")
def detail(record_id):
    """詳細画面:1件分のすべての項目を表示する"""
    conn = get_conn()
    record = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    conn.close()

    if record is None:
        abort(404)

    return render_template("detail.html", record=record)


@app.route("/records/new", methods=["GET", "POST"])
def new():
    """新規登録:GETで入力画面を表示、POSTで登録する"""
    if request.method == "POST":
        data, errors = read_form()
        if not errors:
            conn = get_conn()
            cur = conn.execute(
                """
                INSERT INTO records
                    (occurred_at, kind, title, event, impact, cause, action, prevention, status)
                VALUES
                    (:occurred_at, :kind, :title, :event, :impact, :cause, :action, :prevention, :status)
                """,
                data,
            )
            conn.commit()
            new_id = cur.lastrowid
            conn.close()
            return redirect(url_for("detail", record_id=new_id))
    else:
        # 最初に表示するときの初期値
        data = {f: "" for f in FIELDS}
        data["occurred_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        data["kind"] = "障害"
        data["status"] = "対応中"
        errors = []

    return render_template(
        "form.html", mode="new", data=data, errors=errors, kinds=KINDS, statuses=STATUSES
    )


@app.route("/records/<int:record_id>/edit", methods=["GET", "POST"])
def edit(record_id):
    """編集:GETで今の内容を入れた入力画面を表示、POSTで更新する"""
    conn = get_conn()
    record = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    if record is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        data, errors = read_form()
        if not errors:
            conn.execute(
                """
                UPDATE records SET
                    occurred_at = :occurred_at, kind = :kind, title = :title,
                    event = :event, impact = :impact, cause = :cause,
                    action = :action, prevention = :prevention, status = :status,
                    updated_at = datetime('now', 'localtime')
                WHERE id = :id
                """,
                {**data, "id": record_id},
            )
            conn.commit()
            conn.close()
            return redirect(url_for("detail", record_id=record_id))
    else:
        data = {f: (record[f] or "") for f in FIELDS}
        errors = []

    conn.close()
    return render_template(
        "form.html",
        mode="edit",
        record_id=record_id,
        data=data,
        errors=errors,
        kinds=KINDS,
        statuses=STATUSES,
    )

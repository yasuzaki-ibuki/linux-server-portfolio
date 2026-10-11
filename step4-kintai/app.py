from datetime import datetime, timedelta

from flask import Flask, abort, redirect, render_template, request, url_for

from db import get_conn

app = Flask(__name__)

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def minutes_between(start, end):
    """出勤から退勤までの分数を計算する(どちらかが空なら0)"""
    if start is None or end is None:
        return 0
    return int((end - start).total_seconds() // 60)


def fmt_minutes(minutes):
    """分数を「8:30」のような表示に直す"""
    return f"{minutes // 60}:{minutes % 60:02d}"


def get_today(conn):
    """データベース側の「今日の日付」を取得する"""
    return conn.execute("SELECT CURRENT_DATE AS d").fetchone()["d"]


# ---------------------------------------------------------------
# 打刻
# ---------------------------------------------------------------

@app.route("/")
def index():
    """トップ画面:今日の状態、打刻ボタン、今月の一覧"""
    with get_conn() as conn:
        today = get_today(conn)
        record = conn.execute(
            "SELECT clock_in, clock_out FROM attendance WHERE work_date = CURRENT_DATE"
        ).fetchone()
        rows = conn.execute(
            """
            SELECT work_date, clock_in, clock_out
            FROM attendance
            WHERE work_date >= date_trunc('month', CURRENT_DATE)
            ORDER BY work_date DESC
            """
        ).fetchall()

    if record is None or record["clock_in"] is None:
        status = "未出勤"
    elif record["clock_out"] is None:
        status = "勤務中"
    else:
        status = "退勤済み"

    total = 0
    for r in rows:
        m = minutes_between(r["clock_in"], r["clock_out"])
        r["worked"] = fmt_minutes(m) if m else ""
        total += m

    return render_template(
        "index.html",
        today=today,
        status=status,
        record=record,
        rows=rows,
        total=fmt_minutes(total),
    )


@app.route("/clock-in", methods=["POST"])
def clock_in():
    """出勤:今日の行を作って出勤時刻を入れる(すでに出勤済みなら何もしない)"""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO attendance (work_date, clock_in)
            VALUES (CURRENT_DATE, now())
            ON CONFLICT (work_date) DO UPDATE
                SET clock_in = now(), updated_at = now()
                WHERE attendance.clock_in IS NULL
            """
        )
    return redirect(url_for("index"))


@app.route("/clock-out", methods=["POST"])
def clock_out():
    """退勤:出勤済みで、まだ退勤していない場合だけ退勤時刻を入れる"""
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE attendance
            SET clock_out = now(), updated_at = now()
            WHERE work_date = CURRENT_DATE
              AND clock_in IS NOT NULL
              AND clock_out IS NULL
            """
        )
    return redirect(url_for("index"))


# ---------------------------------------------------------------
# 日報
# ---------------------------------------------------------------

@app.route("/reports")
def reports():
    """日報一覧:新しい順に最大31件"""
    with get_conn() as conn:
        today = get_today(conn)
        rows = conn.execute(
            """
            SELECT report_date, done, issues, plan
            FROM daily_reports
            ORDER BY report_date DESC
            LIMIT 31
            """
        ).fetchall()
    return render_template("reports.html", today=today, rows=rows)


@app.route("/reports/<report_date>", methods=["GET", "POST"])
def report_edit(report_date):
    """日報の入力:GETで入力画面、POSTで保存(その日の日報がなければ新規、あれば上書き)"""
    try:
        d = datetime.strptime(report_date, "%Y-%m-%d").date()
    except ValueError:
        abort(404)  # 日付として正しくないURLは「見つかりません」

    if request.method == "POST":
        data = {k: request.form.get(k, "").strip() for k in ("done", "issues", "plan")}
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO daily_reports (report_date, done, issues, plan)
                VALUES (%(d)s, %(done)s, %(issues)s, %(plan)s)
                ON CONFLICT (report_date) DO UPDATE
                    SET done = EXCLUDED.done,
                        issues = EXCLUDED.issues,
                        plan = EXCLUDED.plan,
                        updated_at = now()
                """,
                {"d": d, **data},
            )
        return redirect(url_for("reports"))

    with get_conn() as conn:
        row = conn.execute(
            "SELECT done, issues, plan, updated_at FROM daily_reports WHERE report_date = %s",
            (d,),
        ).fetchone()
    return render_template("report_form.html", d=d, row=row)


# ---------------------------------------------------------------
# 月次集計
# ---------------------------------------------------------------

@app.route("/monthly")
def monthly():
    """月次集計:指定した月(?month=2026-10)の全日付について、勤務時間と日報の有無を表示する"""
    with get_conn() as conn:
        today = get_today(conn)

    try:
        first = datetime.strptime(request.args.get("month", ""), "%Y-%m").date()
    except ValueError:
        first = today.replace(day=1)  # 指定がない・おかしい場合は今月

    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                d::date AS day,
                a.clock_in,
                a.clock_out,
                CASE
                    WHEN a.clock_in IS NOT NULL AND a.clock_out IS NOT NULL
                    THEN FLOOR(EXTRACT(EPOCH FROM a.clock_out - a.clock_in) / 60)::int
                END AS minutes,
                (r.report_date IS NOT NULL) AS has_report
            FROM generate_series(
                %(first)s::timestamp,
                %(first)s::timestamp + interval '1 month' - interval '1 day',
                interval '1 day'
            ) AS d
            LEFT JOIN attendance a ON a.work_date = d::date
            LEFT JOIN daily_reports r ON r.report_date = d::date
            ORDER BY day
            """,
            {"first": first},
        ).fetchall()

    worked_days = [r for r in rows if r["minutes"]]
    total = sum(r["minutes"] for r in worked_days)
    average = total // len(worked_days) if worked_days else 0
    report_count = sum(1 for r in rows if r["has_report"])

    for r in rows:
        r["weekday"] = WEEKDAYS[r["day"].weekday()]
        r["worked"] = fmt_minutes(r["minutes"]) if r["minutes"] else ""

    return render_template(
        "monthly.html",
        first=first,
        prev_month=prev_month,
        next_month=next_month,
        rows=rows,
        days=len(worked_days),
        total=fmt_minutes(total),
        average=fmt_minutes(average),
        report_count=report_count,
    )

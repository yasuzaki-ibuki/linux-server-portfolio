# -*- coding: utf-8 -*-
"""PayPay家計簿 Web版の計算部分(元: paypay_kakeibo.py)"""
import io
import re
import unicodedata

import pandas as pd

EXCLUDE_KEYWORDS = ["運用", "獲得"]

CATEGORY_RULES = {
    "BASE": ["BASE"],
    "コンビニ": ["セブン", "ファミリーマート", "ファミマ", "ローソン", "ミニストップ", "デイリーヤマザキ"],
    "スーパー": ["イオン", "西友", "ライフ", "マルエツ", "サミット", "ヤオコー", "オーケー", "ロピア", "業務スーパー"],
    "ドラッグストア": ["マツモトキヨシ", "マツキヨ", "ウエルシア", "サンドラッグ", "ツルハ", "ココカラ"],
    "飲食": ["マクドナルド", "スターバックス", "スタバ", "吉野家", "すき家", "松屋", "ラーメン", "食堂", "カフェ", "レストラン", "居酒屋", "ドトール", "モスバーガー", "ケンタッキー", "サイゼリヤ"],
    "交通": ["JR", "メトロ", "バス", "タクシー", "ETC", "モバイルSuica", "PASMO"],
    "通信費": ["ソフトバンク", "ドコモ", "au", "楽天モバイル", "ワイモバイル", "NTT"],
    "サブスク・娯楽": ["Netflix", "Amazon Prime", "Spotify", "YouTube", "Apple", "hulu", "DAZN", "任天堂", "PlayStation", "Steam"],
    "ネット通販": ["Amazon", "楽天市場", "メルカリ", "Yahoo!ショッピング", "ヨドバシ"],
    "医療": ["病院", "クリニック", "薬局", "歯科"],
    "コインランドリー・生活": ["コインランドリー", "クリーニング"],
}

REQUIRED_COLUMNS = [
    "取引日", "出金金額(円)", "入金金額(円)", "海外出金金額", "通貨",
    "変換レート(円)", "利用国", "取引内容", "取引先", "取引方法",
    "支払い区分", "利用者", "取引番号",
]


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """アップロードされたCSV(バイト列)を読み込む"""
    last_err = None
    for enc in ("cp932", "utf-8-sig", "utf-8"):
        try:
            text = data.decode(enc)
            return pd.read_csv(io.StringIO(text), dtype=str)
        except UnicodeDecodeError as e:
            last_err = e
    raise ValueError(f"CSVの文字コードを判定できませんでした: {last_err}")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: unicodedata.normalize("NFKC", str(c)).strip())
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("CSVに想定した列が見つかりませんでした: " + ", ".join(missing))
    return df


def to_number(x) -> float:
    if x is None:
        return 0.0
    s = unicodedata.normalize("NFKC", str(x)).strip()
    s = s.replace(",", "").replace("円", "").replace(" ", "")
    if s in ("", "-", "ー", "nan", "None"):
        return 0.0
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return 0.0


def classify_category(merchant: str) -> str:
    text = str(merchant).lower()
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw.lower() in text:
                return category
    return "その他"


def is_excluded(row) -> bool:
    content = str(row.get("取引内容", ""))
    merchant = str(row.get("取引先", ""))
    return any(kw in content or kw in merchant for kw in EXCLUDE_KEYWORDS)


def extract_amount_from_method(method_text: str) -> float:
    if not method_text:
        return 0.0
    amounts = re.findall(r"([0-9０-９,，]+)\s*円\s*\)", method_text)
    return sum(to_number(a) for a in amounts)


def resolve_expense_amount(row) -> float:
    base = to_number(row.get("出金金額(円)"))
    if base > 0:
        return base
    return extract_amount_from_method(str(row.get("取引方法", "") or ""))


def yen(x) -> str:
    return f"{x:,.0f}円"


def summarize(data: bytes) -> dict:
    """CSVを集計して、画面に出すための結果を返す(データは保存しない)"""
    df = normalize_columns(read_csv_bytes(data))
    rows, excluded = [], 0
    for _, row in df.iterrows():
        txn_id = str(row.get("取引番号", "")).strip()
        if not txn_id or txn_id == "nan":
            continue
        if is_excluded(row):
            excluded += 1
            continue
        amount = resolve_expense_amount(row)
        if amount <= 0:
            continue
        merchant = str(row.get("取引先", "")).strip()
        rows.append({
            "取引日": str(row.get("取引日", "")).strip(),
            "カテゴリ": classify_category(merchant),
            "金額": amount,
        })

    result = {"total_rows": len(df), "excluded": excluded, "count": len(rows),
              "monthly_html": "", "category_html": ""}
    if not rows:
        return result

    d = pd.DataFrame(rows)
    d["年月"] = pd.to_datetime(d["取引日"], errors="coerce").dt.strftime("%Y-%m")

    monthly = d.pivot_table(index="年月", columns="カテゴリ", values="金額",
                            aggfunc="sum", fill_value=0)
    monthly["合計"] = monthly.sum(axis=1)
    monthly = monthly.sort_index()

    category = (d.groupby("カテゴリ")["金額"].agg(["sum", "count"])
                .rename(columns={"sum": "合計金額", "count": "件数"})
                .sort_values("合計金額", ascending=False))

    result["monthly_html"] = monthly.to_html(float_format=yen)
    result["category_html"] = category.to_html(formatters={"合計金額": yen})
    return result

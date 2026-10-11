import psycopg
from psycopg.rows import dict_row

# peer認証:Linuxのユーザー(yasu)と同じ名前のDBユーザーで、ソケット経由で接続する
# パスワードは使わないので、設定ファイルに秘密情報を書く必要がない
DSN = "dbname=kintai host=/var/run/postgresql"


def get_conn():
    """データベースに接続する(結果は列名で取り出せる形にする)"""
    return psycopg.connect(DSN, row_factory=dict_row)

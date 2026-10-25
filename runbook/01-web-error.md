# Runbook 01:Web画面が開かない

## 対象

- 利用者から「Web画面が開かない」と連絡があったとき
- 監視から、Nginx・アプリ・PostgreSQLの異常通知が来たとき

## 構成(どこまで届いているかを考えるための図)

```
本体PC ──① 外の通路──→ Nginx(80番)──② 中の通路──→ kintai(127.0.0.1:8003)──③──→ PostgreSQL
```

## 1. 初動:状況を確認する

| 確認すること | 分かること |
|---|---|
| エラーの内容(502か、500か、画面がまったく出ないか) | どこまで届いているか |
| ほかの画面(/、/monitor/、/worklog/)も開けないか | 全体の問題か、そのアプリだけの問題か |
| ほかの人も開けないか | 利用者側の問題の可能性 |
| いつから開けないか、直前に作業や変更をしていないか | 原因の手がかり |
| 監視(ダッシュボード・LINE通知)の状態 | すでに異常を検知していないか |

## 2. 502 Bad Gateway の場合

**意味:** Nginxまでは届いている。Nginxが奥のアプリにつなげなかった(502の画面はNginxが作っている)。

```
① systemctl status kintai --no-pager
 │
 ├─ inactive / failed(止まっている)
 │    └─ journalctl -u kintai -n 50 --no-pager で、なぜ止まったかを確認
 │         ├─ Stopped …(エラーなし)  → 誰かが止めた・起動し忘れ
 │         ├─ Traceback …            → プログラムのエラー
 │         └─ status=203/EXEC         → 実行できない(SELinux・配置場所)
 │         → 原因を直す → sudo systemctl start kintai
 │
 └─ active(動いている)
      └─ ② curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8003/
           │  (Nginxを通さず、Nginxと同じ転送先にアクセスする)
           │
           ├─ 返事がない → kintaiが8003番で返事をしていない
           │    ├─ sudo ss -tlnp | grep gunicorn で、実際に待っている番号を確認
           │    └─ journalctl -u kintai で、固まっていないか確認
           │
           └─ 200 → kintaiは正常。Nginx → kintai の取り次ぎに問題
                └─ ③ sudo tail -n 20 /var/log/nginx/error.log
                     ├─ 13: Permission denied   → SELinuxを確認
                     └─ 111: Connection refused → Nginxの転送先の番号を確認
```

## 3. 500 Internal Server Error の場合

**意味:** kintaiまで届いている。kintaiの処理の中でエラーが起きた(500の画面はアプリが作っている)。原因はアプリ自身か、アプリが頼っているもの(データベース)にある。

```
① journalctl -u kintai -n 50 --no-pager(Tracebackの一番下の行を見る)
 │
 ├─ TemplateNotFound など → アプリ自身の問題(ファイル・プログラムを確認)
 │
 └─ psycopg.OperationalError: connection failed → データベースにつながらない
      └─ ② systemctl status postgresql --no-pager
           └─ inactive / failed
                └─ ③ journalctl -u postgresql -n 50 --no-pager で、なぜ止まったかを確認
                     → 原因を直す → sudo systemctl start postgresql
                     → kintaiの再起動は不要(画面を開くたびにDBへつなぎ直すため)
```

## 4. 画面がまったく出ない場合

(作成中)

## 5. SELinuxが疑わしいとき

`Permission denied` や `203/EXEC` が出たときは、ファイルの権限だけでなくSELinuxも確認する。

```bash
getenforce                        # Enforcing なら有効
sudo ausearch -m AVC -ts recent   # SELinuxが最近拒否した記録を表示
```

## 6. ログの場所

| 失敗したのは | 見るログ | 出てくる例 |
|---|---|---|
| systemd(サービスの起動に失敗) | `journalctl -u サービス名` | `status=203/EXEC` |
| アプリ(処理中にエラー) | `journalctl -u サービス名` | `Traceback …` |
| Nginx(奥のアプリにつなげない) | `/var/log/nginx/error.log` | `13: Permission denied`、`111: Connection refused` |

Nginxは、処理中のエラーを自分でファイルに書くため、journalではなく `/var/log/nginx/error.log` を見る。

## 7. 復旧の確認と記録

1. ブラウザで画面が開くことを確認する
2. 監視のダッシュボードで、該当のサービスが正常に戻ったことを確認する
3. 作業記録アプリ(/worklog/)に、事象・影響・原因・対処・再発防止を登録する

## 過去の事例

| 事象 | パターン | 原因 |
|---|---|---|
| Nginx経由で502(Step 1) | 502・アプリは動いていた | SELinuxがNginxからアプリへの接続を拒否 |
| サービスが起動しない(Step 1) | 203/EXEC | SELinuxが/home内のプログラムの実行を拒否 |
| 新規登録画面で500(Step 3) | 500・アプリ自身 | テンプレートファイルの配置ミス |
| PostgreSQL停止試験(Step 4) | 500・データベース | PostgreSQLの停止 |

# Step 2:監視ダッシュボード

CPU・メモリ・ディスク使用率と、サービス(nginx・kakeibo・sshd・worklog)の稼働状態を1分ごとにチェックし、
Webのダッシュボードで表示するとともに、異常発生・復旧時にLINEへ通知する。

## 構成

```
systemdタイマー(1分ごと)
   └─ check.py ─┬─ status.json(最新の状態)
                ├─ alerts.log(通知の履歴)
                └─ 状態が変化したとき → notify.py → LINE Messaging API

ブラウザ → Nginx(/monitor/)→ gunicorn(127.0.0.1:8001)→ web.py → status.json を表示
```

## ファイル

| ファイル | 役割 |
|---|---|
| check.py | 状態のチェック、status.json の保存、状態変化時の通知 |
| notify.py | LINE Messaging API(ブロードキャスト)での通知 |
| web.py | ダッシュボードの表示(60秒ごとに自動更新) |
| monitor-check.service | check.py を1回実行するサービス |
| monitor-check.timer | monitor-check.service を1分ごとに起動するタイマー |
| monitor-web.service | ダッシュボードのサービス設定 |
| line_config.example.json | LINEの設定ファイルの見本(本物のトークンは含まない) |
| requirements.txt | 必要なPythonパッケージの一覧 |

## 設計・運用で工夫した点

- 定期実行はsystemdのタイマーで行い、サービスと同じ方法で管理(実行結果は journalctl で確認できる)
- 通知は状態が変化したとき(異常発生・復旧)だけ送り、同じ異常で通知が続かないようにした
- LINEのトークンは別ファイル(line_config.json)に分け、権限600で管理。リポジトリには見本だけを含める
- 監視対象のサービスは check.py の一覧で一括管理し、ダッシュボードにも自動で反映される
- サービスを追加したときは監視対象にも加え、停止試験で異常検知と復旧通知を確認する

## 動作確認

- Step 3で作業記録アプリ(worklog)を監視対象に追加した際、サービスを停止 → LINEへの異常通知とダッシュボードの異常表示を確認 → 起動 → 復旧通知を確認

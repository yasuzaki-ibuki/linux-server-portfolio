# Linux Server Portfolio

VirtualBox上のRocky Linux 9に、Webサーバー・Webアプリ・監視の仕組みを構築した学習記録です。
Linuxサーバーの構築・運用・障害対応を、実際に手を動かして身につけることを目的にしています。

## 構成

```
Windows(ブラウザ / PowerShell)
   │  SSH(2222→22)/ HTTP(8080→80)
   ▼
Rocky Linux 9(VirtualBox)
   └─ Nginx(80番)
        ├─ /          → 家計簿アプリ(gunicorn 8000番)
        ├─ /monitor/  → 監視ダッシュボード(gunicorn 8001番)
        └─ /worklog/  → 作業記録・障害報告アプリ(gunicorn 8002番)→ SQLite

   systemdタイマー(1分ごと)→ check.py → status.json / LINE通知
```

## 使用技術

- OS:Rocky Linux 9.8(VirtualBox)
- Webサーバー:Nginx(リバースプロキシ)
- アプリ:Python 3.9 / Flask / gunicorn
- データベース:SQLite
- サービス管理:systemd(service / timer)
- セキュリティ:SSH公開鍵認証(パスワード認証・root直接ログイン禁止)、firewalld、SELinux(Enforcingのまま運用)
- ログ:journald(永続化)
- 時刻同期:chrony
- 通知:LINE Messaging API

## 内容

### Step 0:サーバー構築(`step0-server/`)
- Rocky Linux 9のインストール、一般ユーザー作成とsudo設定
- SSH公開鍵認証、ホスト名設定、パッチ適用(dnf)
- Nginx導入、firewalldでHTTP許可、chronyで時刻同期
- SSHハードニング(パスワード認証・root直接ログインの禁止)
- journaldのログ永続化(再起動前のログを障害調査に使えるようにする)
- 再起動テスト(全サービスの自動起動を確認)

### Step 1:家計簿Webアプリ(`step1-kakeibo/`)
- 自作の家計簿ツール(PayPayの利用履歴CSVを集計)をWebアプリ化
- Flask+gunicornで動かし、Nginxをリバースプロキシとして構成
- systemdでサービス化(自動起動・自動再起動)
- 個人情報を扱うため、アップロードしたCSVはサーバーに保存しない設計

### Step 2:監視ダッシュボード(`step2-monitor/`)
- CPU・メモリ・ディスク使用率とサービスの稼働状態を1分ごとにチェック(systemdタイマー)
- Webのダッシュボードで状態を確認(60秒ごとに自動更新)
- 異常発生・復旧時にLINEへ通知(状態が変化したときだけ通知)
- トークンは別ファイルに分離し、権限600で管理(リポジトリには含めない)

### Step 3:作業記録・障害報告アプリ(`step3-worklog/`)
- Flask+SQLiteで、障害対応や作業の記録(事象・影響・原因・対処・再発防止)を登録・閲覧できるWebアプリ
- これまでのサーバー構築で経験した障害5件を初期データとして登録
- systemdでサービス化し、Nginxで /worklog/ に公開、監視の対象にも追加

## つまずいたことと解決

| 事象 | 原因 | 対応 |
|---|---|---|
| Nginx経由で502 Bad Gateway | SELinuxがNginxからアプリへの接続をブロック | ログで`Permission denied`を確認し、`setsebool -P httpd_can_network_connect 1`で必要な許可のみ付与 |
| サービス起動失敗(203/EXEC) | SELinuxがsystemdによる`/home`内のプログラム実行をブロック | アプリを`/opt`に移設 |
| firewalldの設定が反映されない | `--permanent`の設定を`--reload`していなかった | `firewall-cmd --reload`で反映 |
| 仮想マシンの時刻がずれる | 状態保存→再開で時計が止まり、chronyがゆっくり補正 | `chronyc makestep`で即時補正、`makestep 1.0 -1`に設定変更 |
| 再起動テスト中にVirtualBoxが異常終了 | 仮想化基盤側の異常終了(Linuxの終了処理は正常完了) | VirtualBoxのログを保全し、`journalctl -b -1`で直前のログを確認して切り分け |
| 新規登録画面でInternal Server Error | テンプレートファイルの配置ミス | gunicornのログ(Traceback)で`TemplateNotFound`を確認し、正しい場所に配置 |

## 今後の予定

- Step 4:勤怠・日報アプリ(データベース、バックアップと復元)
- Ansibleによる構築の自動化
- AWS上への構築

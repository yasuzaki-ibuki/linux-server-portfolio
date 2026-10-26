# Linux Server Portfolio

Linuxサーバーの運用保守を実践的に身につけるため、VirtualBox上にRocky Linux 9のサーバー環境を構築し、運用してきた学習記録です。
Webアプリは「運用する対象」として用意し、監視・障害対応・バックアップと復元・再起動試験・ファイアウォール設計など、運用保守の作業に重点を置いています。

- 期間:2026年10月〜(継続中)
- 構築中に発生した障害は、原因の切り分けから対処までをREADMEと作業記録アプリに記録しています
- 作業時間:約60時間(Step 0〜5、仮想マシン上での構築・試験・記録)

| Step | 内容 | 作業時間の目安 |
|---|---|---|
| Step 0 | サーバー構築・SSHハードニング・ログ永続化・再起動テスト | 約12時間 |
| Step 1 | 家計簿Webアプリ | 約7時間 |
| Step 2 | 監視ダッシュボード | 約7時間 |
| Step 3 | 作業記録・障害報告アプリ | 約8時間 |
| Step 4 | 勤怠・日報アプリ(PostgreSQL、バックアップと復元) | 約11時間 |
| Step 5 | ネットワーク(2台構成・パケットキャプチャ・ファイアウォール) | 約15時間 |

### 特に見てほしいところ

| 内容 | 場所 |
|---|---|
| 障害の切り分けと対処(502エラー、サービス起動失敗、VirtualBox異常終了など) | 下の「つまずいたことと解決」、各StepのREADME |
| 障害時の対応手順書(Runbook) | `runbook/` |
| 監視とLINE通知、停止試験 | Step 2・3・4 |
| バックアップの自動化と復元テスト | Step 4 |
| ネットワーク設定、パケットキャプチャ、ファイアウォール設計と拒否の試験 | Step 5 |


## 構成

```
Windows(本体PC:ブラウザ / PowerShell)
 │
 ├─ NAT(ポートフォワーディング)
 │    SSH 127.0.0.1:2222 → 22 / HTTP 127.0.0.1:8080 → 80
 │    └→ rocky9-web の enp0s3
 │
 └─ ホストオンリーネットワーク 192.168.56.0/24(本体PC:192.168.56.1)
      ├→ rocky9-web  の enp0s8:192.168.56.10
      └→ rocky9-node の enp0s8:192.168.56.11

rocky9-web(Rocky Linux 9)
   └─ Nginx(80番)
        ├─ /          → 家計簿アプリ(gunicorn 8000番)
        ├─ /monitor/  → 監視ダッシュボード(gunicorn 8001番)
        ├─ /worklog/  → 作業記録・障害報告アプリ(gunicorn 8002番)→ SQLite
        └─ /kintai/   → 勤怠・日報アプリ(gunicorn 8003番)→ PostgreSQL 18
   systemdタイマー(1分ごと)→ check.py → status.json / LINE通知
   systemdタイマー(毎日3:00)→ backup.sh → pg_dump(7日分保持)
   firewalld:NAT側 ssh・http / ホストオンリー側 本体PCからのSSH・HTTPのみ

rocky9-node(Rocky Linux 9 Minimal)
   ・Ansibleで構築される側(予定)。rocky9-webからSSH鍵で接続
   firewalld:ホストオンリー側 rocky9-web・本体PCからのSSHのみ

インターネットへの出口:各VMの enp0s3(NAT → ゲートウェイ 10.0.2.2)
```

## 使用技術

- OS:Rocky Linux 9.8(VirtualBox)
- Webサーバー:Nginx(リバースプロキシ)
- アプリ:Python 3.9 / Flask / gunicorn
- データベース:PostgreSQL 18、SQLite
- サービス管理:systemd(service / timer、依存関係の設定)
- セキュリティ:SSH公開鍵認証(パスワード認証・root直接ログイン禁止)、firewalld、SELinux(Enforcingのまま運用)
- ネットワーク:NetworkManager(nmcli)、tcpdump
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

### Step 4:勤怠・日報アプリ(`step4-kintai/`)
- PostgreSQL 18を導入し、打刻・日報・月次集計ができるWebアプリを構築
- peer認証でパスワードを使わずに接続、DBは127.0.0.1のみで待ち受け
- pg_dumpで毎日自動バックアップ(取得直後に検証、7日分保持)し、復元テストで実際に戻せることを確認
- アプリとPostgreSQLの両方を監視し、停止試験で502と500の違いを切り分け

### Step 5:ネットワーク(`step5-network/`)
- NetworkManager(nmcli)でネットワーク設定を確認・変更し、切り戻しまで実施
- tcpdumpで、3ウェイハンドシェイク・リバースプロキシの通信・NAT・DNSの問い合わせを実際のパケットで確認
- 仮想マシンを2台構成にし、ホストオンリーネットワークで通信。SSH鍵でサーバー間を接続
- firewalldのゾーンとリッチルールで、NICごと・送り元ごとに受け付ける通信を設計し、拒否されることまで試験

### Runbook(運用手順書)(`runbook/`)
- 障害や定常作業が発生したときに、誰が対応しても同じ手順で確認・対処できるようにまとめた手順書
- 構築中に実際に発生した障害と、その対応の経験をもとに作成
- 01:Web画面が開かない(502・500・画面が出ない場合の切り分け、ログの場所、SELinuxの確認)

## つまずいたことと解決

| 事象 | 原因 | 対応 |
|---|---|---|
| Nginx経由で502 Bad Gateway | SELinuxがNginxからアプリへの接続をブロック | ログで`Permission denied`を確認し、`setsebool -P httpd_can_network_connect 1`で必要な許可のみ付与 |
| サービス起動失敗(203/EXEC) | SELinuxがsystemdによる`/home`内のプログラム実行をブロック | アプリを`/opt`に移設 |
| firewalldの設定が反映されない | `--permanent`の設定を`--reload`していなかった | `firewall-cmd --reload`で反映 |
| 仮想マシンの時刻がずれる | 状態保存→再開で時計が止まり、chronyがゆっくり補正 | `chronyc makestep`で即時補正、`makestep 1.0 -1`に設定変更 |
| 再起動テスト中にVirtualBoxが異常終了 | 仮想化基盤側の異常終了(Linuxの終了処理は正常完了) | VirtualBoxのログを保全し、`journalctl -b -1`で直前のログを確認して切り分け |
| 新規登録画面でInternal Server Error | テンプレートファイルの配置ミス | gunicornのログ(Traceback)で`TemplateNotFound`を確認し、正しい場所に配置 |
| 復元コマンドが無反応で止まる | `-d`のDB名を書き忘れ、pg_restoreが入力待ちになった | `Ctrl+C`で中断し、`-d kintai`を指定して再実行 |

## 今後の予定

- Runbookの拡充(サービスが起動しない、バックアップからの復元、再起動作業、ファイアウォールの設定変更など)
- 運用の基本(ログローテーション、ディスク容量逼迫時の対応、ユーザー・権限管理)
- DNS(BIND)・DHCPサーバーの構築
- Zabbixの導入と、自作監視からの移行
- プロキシ(Squid)の構築
- Ansibleによる構築の自動化
- NginxのHTTPS化
- 脆弱性診断ツールを使った、自分のサーバーのセキュリティ確認

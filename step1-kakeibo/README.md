# Step 1:家計簿Webアプリ

自作の家計簿ツール(PayPayの利用履歴CSVを集計するPythonスクリプト)を、ブラウザから使えるWebアプリにした。
CSVをアップロードすると、ポイント運用・獲得の取引を除外し、月別・カテゴリ別に集計して表示する。

## 構成

ブラウザ → Nginx(/)→ gunicorn(127.0.0.1:8000)→ Flask(app.py)→ kakeibo_core.py(集計処理)

## ファイル

| ファイル | 役割 |
|---|---|
| app.py | 画面の表示と、CSVアップロードの受け付け |
| kakeibo_core.py | CSVの読み込みと集計処理(既存ツールのコードを利用) |
| kakeibo.service | systemdのサービス設定 |
| requirements.txt | 必要なPythonパッケージの一覧 |

## 設計・運用で工夫した点

- 個人情報を含むCSVはサーバーに保存せず、メモリ上で集計して結果だけを表示する設計
- 集計処理(kakeibo_core.py)を画面の処理(app.py)と分け、既存ツールのコードを再利用
- gunicornは 127.0.0.1 で待ち受け、外部からはNginx経由でしかアクセスできない構成
- systemdでサービス化(自動起動・異常終了時の自動再起動)
- アプリ専用のPython環境(venv)を作り、他のアプリとパッケージが混ざらないようにした

## 構築中に発生したトラブル

### Nginx経由で502 Bad Gateway
- 事象:Nginxのリバースプロキシ設定後、ブラウザで502 Bad Gatewayが表示された
- 調査:curlでgunicornに直接アクセスし、アプリ単体は正常と切り分け → Nginxのerror.logで「13: Permission denied」を確認 → getenforceでSELinuxがEnforcingと特定
- 対処:SELinuxは無効化せず、`setsebool -P httpd_can_network_connect 1` で必要な許可だけを付与
- 学び:アプリ単体 → Nginxのログ → SELinux の順に切り分ける

### サービスが起動しない(status=203/EXEC)
- 事象:systemdでサービス化したアプリが起動に失敗した
- 原因:SELinuxが、systemdから /home 内のプログラムを実行することをブロックしていた
- 対処:アプリを /home から /opt/kakeibo に移設
- 学び:サービスとして動かすアプリは /opt に配置する

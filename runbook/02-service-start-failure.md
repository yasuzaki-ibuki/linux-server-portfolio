# Runbook 02:サービスが起動しない

## 対象

- `systemctl start` / `restart` を実行したら、次のように失敗した
- 再起動後や監視の通知で、サービスが `failed` になっていることに気づいた

```
Job for kintai.service failed because the control process exited with error code.
See "systemctl status kintai.service" and "journalctl -xeu kintai.service" for details.
```

以下は kintai を例にしているが、ほかのサービス(worklog、kakeibo、monitor-web など)も同じ手順で確認できる。

## 1. 共通の初動:状態とログを見る

すぐに起動し直さず、先に原因を確認する(原因を見ないまま起動すると、同じ原因でまた止まり、報告書に原因も書けない)。

```bash
systemctl status kintai --no-pager        # 状態(failed か)と、最近のログ数行
journalctl -xeu kintai --no-pager         # -x 補足説明付き、-e 最新から、-u 対象のサービスだけ
```

ログに出ている内容で、次のどのパターンかを判断する。

| ログに出るもの | パターン |
|---|---|
| `status=203/EXEC`、`Permission denied` | 2. プログラムを実行できない |
| `Connection in use` | 3. 待ち受けの番号が使用中 |
| `SyntaxError`、`Traceback` | 4. プログラムの書き間違い・エラー |

## 2. プログラムを実行できない(203/EXEC)

**意味:** systemdが、ExecStart= に書かれたプログラムを実行できなかった。

`systemctl status` の `ExecStart=` の行で、プログラムの場所を確認する。`/home` の中にある場合は、SELinuxが「個人のファイル(user_home_t)」をサービスから実行することを拒否している可能性が高い。

journalの `Permission denied` だけでは、ファイルの権限とSELinuxのどちらが原因か区別できないため、監査ログで確認する。

```bash
getenforce                         # Enforcing なら SELinux は有効
sudo ausearch -m AVC -ts recent    # SELinuxが最近拒否した記録
```

- `denied { execute }` と `user_home_t` の記録がある → SELinuxが原因
- 記録がない → ファイルの権限(実行権限)やパスの書き間違いを確認する

**対処:** SELinuxは無効にせず、ルールに合う場所(/opt)にアプリを置く。

```
① アプリのフォルダを /opt に移す
② サービスの設定(ExecStart= と WorkingDirectory=)を /opt の場所に書き換える
③ sudo systemctl daemon-reload
④ sudo systemctl start kintai
```

`mv` で移した場合は、元のラベル(user_home_t)が残るため、場所に合ったラベルに付け直す。

```bash
sudo restorecon -Rv /opt/kintai    # -R 中身まで全部、-v 付け直したファイルを表示
ls -Z /opt/kintai/venv/bin/gunicorn # -Z SELinuxのラベルを表示して確認
```

## 3. 待ち受けの番号が使用中(Connection in use)

**意味:** 同じ番号(例:8003)で、すでに別のプロセスが待ち受けているため、起動できない。

```bash
sudo ss -tlnp | grep ':8003 '      # 8003番を誰が使っているか(pid を確認)
ps -fp <pid>                        # そのプロセスが、どんなコマンドで起動されたか
```

| 分かったこと | 原因 | 対処 |
|---|---|---|
| 手で起動したgunicorn | 仮起動したまま止め忘れていた | `kill <pid>` で止める |
| ほかのアプリのプロセス | 設定で番号を書き間違えた | そのアプリの設定を直す |

- 手で起動したプロセスは systemd の管理外のため、`systemctl stop` では止められない
- `kill` はまず通常の終了(TERM)で行い、止まらない場合だけ `kill -9`(強制終了)を使う

止めたら、番号が空いたことを確認してから起動する。

```bash
sudo ss -tlnp | grep ':8003 '      # 何も表示されなければ空いている
sudo systemctl start kintai
```

## 4. プログラムの書き間違い(SyntaxError)

**意味:** プログラムに文法の間違いがあり、Pythonが読み込めない。

```
  File "/opt/kintai/app.py", line 25
    def index()
               ^
SyntaxError: expected ':'
```

ログに、ファイル名・行番号・間違っている場所(`^`)・足りないもの(`expected ':'`)が表示される。

**対処:**

```bash
nano +25 /opt/kintai/app.py                               # 該当の行を直す
cd /opt/kintai && venv/bin/python3 -m py_compile app.py   # 文法チェック(何も出なければOK)
sudo systemctl start kintai
```

**再発防止:** プログラムを変更したら、起動・再起動の前に必ず文法チェックを行う。

| 変更したもの | 反映前の文法チェック |
|---|---|
| SSHの設定 | `sudo sshd -t` |
| Nginxの設定 | `sudo nginx -t` |
| Pythonのプログラム | `venv/bin/python3 -m py_compile app.py` |

## 5. 復旧の確認と記録

1. `systemctl status kintai` が `active (running)` になっている
2. `sudo ss -tlnp | grep ':8003 '` で、サービスのgunicornが待ち受けている
3. ブラウザで画面が開く
4. 監視のダッシュボードで正常に戻っている
5. 作業記録アプリ(/worklog/)に、事象・原因・対処・再発防止を登録する

## 過去の事例

| 事象 | パターン | 原因 |
|---|---|---|
| 家計簿アプリのサービスが起動しない(Step 1) | 203/EXEC | /home内にアプリを置いており、SELinuxが実行を拒否 → /optに移設 |
| 新規登録画面のInternal Server Error(Step 3) | プログラムのエラー(Traceback) | テンプレートファイルの配置ミス(起動はできたが、画面を開いたときにエラー) |

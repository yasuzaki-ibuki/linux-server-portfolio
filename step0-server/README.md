
### SSHハードニング
- パスワード認証・キーボード対話認証を無効化し、公開鍵認証のみに限定
- rootの直接ログインを禁止(作業は一般ユーザー+sudo)
- 本体の sshd_config は編集せず sshd_config.d/01-hardening.conf に追加(OSアップデート時の衝突を避けるため)
- ファイル名を「01-」にして、OS標準の 50-redhat.conf より先に読み込ませる(sshdは最初に読んだ値を優先)
- 反映前に `sshd -t` で文法チェック、`systemctl reload` で接続を切らずに反映
- 確認:公開鍵でのログイン成功/パスワード認証が拒否されることを実機で確認
- 設定ファイル:[ssh/01-hardening.conf](ssh/01-hardening.conf)

### ログの永続化(journald)
- 初期状態ではjournalがメモリ上に保存され、再起動で消失する設定だった
- 障害調査で再起動前のログを確認できるよう、Storage=persistent で永続化
- ディスク逼迫を防ぐため SystemMaxUse=200M で上限を設定
- 設定反映後、journalctl --flush で書き込み先をディスクへ切り替え
- 設定ファイル:[journald/persistent.conf](journald/persistent.conf)

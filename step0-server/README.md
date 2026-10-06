
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

### 再起動テスト(2026-10-06)
- 再起動前に自動起動設定を確認(systemctl is-enabled:全サービス enabled)
- 再起動後、全サービスの起動を確認(is-active:全 active、systemctl --failed:0件)
- Webアプリ(家計簿・監視ダッシュボード)の表示、SELinux(Enforcing)、時刻同期を確認

#### テスト中に発生した障害:VirtualBoxの異常終了
- 事象:再起動処理中に VirtualBoxVM.exe がメモリアクセス違反で異常終了
- 対応:VirtualBox側のログ(VBox.log)を保全 → VMを起動 → 影響確認
- 調査:journalctl -b -1 で直前のログを確認。Linuxの終了処理はファイルシステムの切り離し・同期まで正常完了しており、再起動の切り替え時に仮想化基盤側で異常終了したと判断
- 影響:データ破損なし、全サービス正常起動
- 備考:直前に journald を永続化していたため、異常終了前のログを確認できた

#### 起動時の警告(journalctl -b -p err)と判断
- RETBleed(CPU脆弱性対策の警告):仮想環境特有のため対処不要
- e1000(保守終了予定のNICドライバー):現状は動作。将来 virtio-net への変更を検討
- vmwgfx(グラフィックドライバーの非対応警告):運用影響なし。VirtualBox異常終了の関連候補として記録し、再発時にグラフィックスコントローラーの変更を検討

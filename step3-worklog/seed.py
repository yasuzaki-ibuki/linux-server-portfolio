from db import get_conn, init_db

# 最初に登録する記録(これまでの障害対応)
# ※日時が不明なものは仮の日付。あとで編集画面から直す
RECORDS = [
    {
        "occurred_at": "2026-10-01 00:00",
        "kind": "障害",
        "title": "Nginx経由で家計簿アプリにアクセスすると502 Bad Gateway",
        "event": "Nginxのリバースプロキシ設定後、ブラウザから家計簿アプリを開くと502 Bad Gatewayが表示された",
        "impact": "Nginx経由で家計簿アプリにアクセスできない(構築中のため利用者影響なし)",
        "cause": "SELinuxがNginx(httpd)からgunicornへのネットワーク接続をブロックしていた",
        "action": "curlでgunicornに直接アクセスし、アプリ単体は正常と切り分け → Nginxのerror.logで「13: Permission denied」を確認 → getenforceでSELinuxがEnforcingと特定 → setsebool -P httpd_can_network_connect 1 で必要な許可のみ付与 → ブラウザで復旧確認",
        "prevention": "SELinuxは無効化せず、必要な許可だけを付与する方針とする。502発生時は、アプリ単体 → Nginxログ → SELinuxの順に切り分ける",
        "status": "完了",
    },
    {
        "occurred_at": "2026-10-01 00:00",
        "kind": "障害",
        "title": "家計簿アプリのサービスが起動しない(status=203/EXEC)",
        "event": "systemdでサービス化した家計簿アプリが起動に失敗し、status=203/EXEC が表示された",
        "impact": "家計簿アプリが起動しない(構築中のため利用者影響なし)",
        "cause": "SELinuxが、systemdのサービスから/home内のプログラムを実行することをブロックしていた",
        "action": "アプリを/home配下から/opt/kakeiboへ移設し、サービスの設定を修正して起動を確認",
        "prevention": "サービスとして動かすアプリは/optに配置する",
        "status": "完了",
    },
    {
        "occurred_at": "2026-10-01 00:00",
        "kind": "障害",
        "title": "firewalldの設定変更が反映されない",
        "event": "firewall-cmdで--permanentを付けて許可を追加したが、通信が許可されなかった",
        "impact": "設定した通信が届かない",
        "cause": "--permanentは「次回起動時の設定」を変更するだけで、--reloadをしないと現在の設定に反映されない",
        "action": "firewall-cmd --reload を実行し、反映を確認",
        "prevention": "--permanentで設定したら、必ず--reloadしてから--list-allで反映を確認する",
        "status": "完了",
    },
    {
        "occurred_at": "2026-10-01 00:00",
        "kind": "障害",
        "title": "仮想マシンの時刻がずれる",
        "event": "仮想マシンを状態保存から再開した後、OSの時刻が実際の時刻とずれていた",
        "impact": "ログの時刻が不正確になり、障害調査の妨げになる",
        "cause": "状態保存中は仮想マシンの時計が止まるため、再開時にずれが生じる。chronyの初期設定では、起動直後以外は時刻を一気に補正しない",
        "action": "chronyc makestep で即時補正 → chronyの設定を makestep 1.0 -1 に変更し、ずれが1秒以上あればいつでも即時補正するようにした",
        "prevention": "状態保存→再開を使う環境では、makestepの設定で自動補正させる",
        "status": "完了",
    },
    {
        "occurred_at": "2026-10-06 22:42",
        "kind": "障害",
        "title": "再起動テスト中にVirtualBoxが異常終了",
        "event": "再起動テストで sudo systemctl reboot を実行したところ、VirtualBoxVM.exe がメモリアクセス違反のエラーで異常終了した",
        "impact": "データ破損なし。VM起動後、全サービスの正常起動を確認",
        "cause": "journalctl -b -1 で直前のログを確認。Linuxの終了処理はファイルシステムの切り離し・同期まで正常完了しており、再起動の切り替え時に仮想化基盤(VirtualBox)側で異常終了したと判断",
        "action": "VirtualBoxのログ(VBox.log)を保全 → VMを起動 → 起動履歴と直前のログを確認 → サービス・アプリ・SELinux・時刻同期を確認",
        "prevention": "直前にjournaldを永続化していたため、異常終了前のログを確認できた。起動時に出たvmwgfx(グラフィックドライバー)の警告を関連候補として記録し、再発時にグラフィックスコントローラーの変更を検討する",
        "status": "完了",
    },
]


def main():
    init_db()
    conn = get_conn()

    # すでにデータがある場合は、二重登録しないように何もしない
    count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    if count > 0:
        print(f"すでに{count}件のデータがあるため、登録をスキップしました")
    else:
        for r in RECORDS:
            conn.execute(
                """
                INSERT INTO records
                    (occurred_at, kind, title, event, impact, cause, action, prevention, status)
                VALUES
                    (:occurred_at, :kind, :title, :event, :impact, :cause, :action, :prevention, :status)
                """,
                r,
            )
        conn.commit()
        print(f"{len(RECORDS)}件を登録しました")

    # 登録されている内容を一覧表示して確認する
    for row in conn.execute("SELECT id, occurred_at, kind, status, title FROM records ORDER BY id"):
        print(f"[{row['id']}] {row['occurred_at']} {row['kind']} {row['status']} {row['title']}")

    conn.close()


if __name__ == "__main__":
    main()

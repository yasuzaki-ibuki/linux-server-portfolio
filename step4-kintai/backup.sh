#!/bin/bash
# 勤怠DB(kintai)のバックアップ
set -euo pipefail
umask 077

BACKUP_DIR=/var/backup/kintai
KEEP_DAYS=7
STAMP=$(date +%Y%m%d-%H%M%S)
FILE="$BACKUP_DIR/kintai-$STAMP.dump"

# 1. バックアップを取る
pg_dump -Fc -h /var/run/postgresql -f "$FILE" kintai

# 2. 取ったバックアップが、復元に使える形で読めるか確認する
pg_restore -l "$FILE" > /dev/null

# 3. 保存期間を過ぎた古いバックアップを削除する
find "$BACKUP_DIR" -name 'kintai-*.dump' -mtime +"$KEEP_DAYS" -delete

echo "backup ok: $FILE ($(du -h "$FILE" | cut -f1))"

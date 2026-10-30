# -*- coding: utf-8 -*-
"""
数据库备份 / 恢复工具

用法：
  python scripts/backup.py backup              # 备份到 data/backups/
  python scripts/backup.py list                # 列出备份
  python scripts/backup.py restore <文件名>    # 恢复
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "ziwei.db")
BACKUP_DIR = os.path.join(ROOT, "data", "backups")


def ensure_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def backup() -> str:
    ensure_dir()
    if not os.path.exists(DB):
        raise SystemExit(f"数据库不存在: {DB}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(BACKUP_DIR, f"ziwei_{stamp}.db")
    # 用 SQLite 在线备份 API，避免直接复制产生不一致
    src = sqlite3.connect(DB)
    out = sqlite3.connect(dst)
    with out:
        src.backup(out)
    src.close()
    out.close()
    size = os.path.getsize(dst) / 1024
    print(f"[OK] 已备份 -> {dst}  ({size:.1f} KB)")
    return dst


def list_backups():
    ensure_dir()
    files = sorted(f for f in os.listdir(BACKUP_DIR) if f.endswith(".db"))
    if not files:
        print("暂无备份")
        return
    print(f"共 {len(files)} 个备份（{BACKUP_DIR}）：")
    for f in files:
        p = os.path.join(BACKUP_DIR, f)
        t = datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  {f:<34} {os.path.getsize(p)/1024:>8.1f} KB  {t}")


def restore(name: str):
    src = os.path.join(BACKUP_DIR, name)
    if not os.path.exists(src):
        raise SystemExit(f"备份不存在: {src}")
    if os.path.exists(DB):
        # 恢复前先自动备份当前库
        ensure_dir()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety = os.path.join(BACKUP_DIR, f"before_restore_{stamp}.db")
        shutil.copy2(DB, safety)
        print(f"[i] 当前库已自动备份 -> {safety}")
    shutil.copy2(src, DB)
    # 清理可能残留的 WAL
    for ext in ("-wal", "-shm"):
        p = DB + ext
        if os.path.exists(p):
            os.remove(p)
    print(f"[OK] 已恢复 {name} -> {DB}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "backup":
        backup()
    elif cmd == "list":
        list_backups()
    elif cmd == "restore":
        if len(sys.argv) < 3:
            raise SystemExit("请指定备份文件名")
        restore(sys.argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

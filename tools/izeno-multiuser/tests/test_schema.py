#!/usr/bin/env python3
"""Usage: python3 test_schema.py ORIGINAL_DIR PATCHED_DIR.
Requires local MariaDB administrator via unix socket. Uses a disposable database.
"""
from pathlib import Path
import os, subprocess as sp, sys
base,fixed=map(Path,sys.argv[1:])
name='izeno_patch_test_'+str(os.getpid())
def sql(text):return sp.check_output(['mariadb','-N',name],input=text.encode()).decode().strip()
sp.run(['mariadb','-e',f'CREATE DATABASE {name} CHARACTER SET utf8mb4'],check=True)
try:
    sql('CREATE TABLE users (id BIGINT UNSIGNED PRIMARY KEY, is_admin TINYINT NOT NULL DEFAULT 0) ENGINE=InnoDB; INSERT INTO users VALUES (1,1);')
    sql((base/'reference/zeno-web-schema.sql').read_text().replace('USE forum_one;',''))
    sql("INSERT INTO zeno_console_sessions(token,user_id) VALUES(REPEAT('a',64),1)")
    for _ in range(2):sql((fixed/'migration.sql').read_text())
    sql("UPDATE zeno_console_sessions SET close_reason='inactive'")
    assert sql('SELECT COUNT(*) FROM zeno_console_sessions WHERE last_activity IS NOT NULL')=='1'
    assert sql('SELECT COUNT(*) FROM zeno_console_access WHERE user_id=1')=='1'
    assert sql("SELECT COLUMN_DEFAULT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='zeno_console_requests' AND COLUMN_NAME='shared_mode'")=='0'
    print('PASS migration twice on original schema, existing row retained, inactive accepted, shared_mode default 0')
finally:sp.run(['mariadb','-e',f'DROP DATABASE {name}'],check=True)

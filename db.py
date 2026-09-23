import os

import pymysql
from flask import g


def get_db():
  # 요청마다 DB EC2(MariaDB)에 연결 하나를 열고, 요청이 끝나면 close_db에서 닫는다
  if "db" not in g:
    g.db = pymysql.connect(
      host=os.environ["DB_HOST"],
      port=int(os.getenv("DB_PORT", "3306")),
      user=os.environ["DB_USER"],
      password=os.environ["DB_PASSWORD"],
      database=os.environ["DB_NAME"],
      charset="utf8mb4",
      cursorclass=pymysql.cursors.DictCursor,
      autocommit=True,
      # 보안 그룹이 막혀 있으면 오래 기다리지 않고 바로 에러가 나도록 짧게 설정
      connect_timeout=5,
    )
  return g.db


def close_db(e=None):
  db = g.pop("db", None)
  if db is not None:
    db.close()


def query(sql, args=None, one=False):
  # SELECT 결과를 dict 목록으로 반환 (one=True면 첫 행 또는 None)
  with get_db().cursor() as cur:
    cur.execute(sql, args)
    rows = cur.fetchall()
  if one:
    return rows[0] if rows else None
  return rows


def execute(sql, args=None):
  # INSERT/UPDATE/DELETE 실행 후 새로 생성된 행의 id 반환
  with get_db().cursor() as cur:
    cur.execute(sql, args)
    return cur.lastrowid

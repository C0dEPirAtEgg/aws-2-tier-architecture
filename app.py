import os
import socket

import pymysql
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for

from db import close_db, execute, query

# 웹 EC2의 .env 파일에서 DB 접속 정보를 읽어 환경변수로 등록
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
app.teardown_appcontext(close_db)


@app.context_processor
def inject_server_info():
  # 어느 웹 서버가 응답했는지 화면 하단에 표시
  return {"server_hostname": socket.gethostname()}


def form_values(*names):
  return {name: request.form.get(name, "").strip() for name in names}


def get_post_or_404(post_id):
  post = query("SELECT * FROM posts WHERE id = %s", (post_id,), one=True)
  if post is None:
    abort(404)
  return post


# ---------- 게시글 ----------

@app.route("/")
def index():
  posts = query(
    "SELECT p.id, p.title, p.author, p.created_at, "
    "(SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count "
    "FROM posts p ORDER BY p.id DESC"
  )
  return render_template("index.html", posts=posts)


@app.route("/posts/new", methods=["GET", "POST"])
def new_post():
  if request.method == "GET":
    return render_template("form.html", post={}, mode="new")

  values = form_values("title", "author", "password", "content")
  if not all(values.values()):
    flash("모든 항목을 입력해 주세요.", "danger")
    return render_template("form.html", post=values, mode="new")

  post_id = execute(
    "INSERT INTO posts (title, content, author, password) VALUES (%s, %s, %s, %s)",
    (values["title"], values["content"], values["author"], values["password"]),
  )
  flash("글이 등록되었습니다.", "success")
  return redirect(url_for("post_detail", post_id=post_id))


@app.route("/posts/<int:post_id>")
def post_detail(post_id):
  post = get_post_or_404(post_id)
  comments = query(
    "SELECT * FROM comments WHERE post_id = %s ORDER BY id", (post_id,)
  )
  return render_template("detail.html", post=post, comments=comments)


@app.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id):
  post = get_post_or_404(post_id)
  if request.method == "GET":
    return render_template("form.html", post=post, mode="edit")

  values = form_values("title", "password", "content")
  # 실습용이라 비밀번호를 평문으로 저장하고 그대로 비교한다
  if values["password"] != post["password"]:
    flash("비밀번호가 일치하지 않습니다.", "danger")
    return render_template("form.html", post={**post, **values}, mode="edit")
  if not values["title"] or not values["content"]:
    flash("제목과 내용을 입력해 주세요.", "danger")
    return render_template("form.html", post={**post, **values}, mode="edit")

  execute(
    "UPDATE posts SET title = %s, content = %s WHERE id = %s",
    (values["title"], values["content"], post_id),
  )
  flash("글이 수정되었습니다.", "success")
  return redirect(url_for("post_detail", post_id=post_id))


@app.route("/posts/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):
  post = get_post_or_404(post_id)
  if request.form.get("password", "") != post["password"]:
    flash("비밀번호가 일치하지 않습니다.", "danger")
    return redirect(url_for("post_detail", post_id=post_id))

  # 댓글은 FK의 ON DELETE CASCADE로 함께 삭제된다
  execute("DELETE FROM posts WHERE id = %s", (post_id,))
  flash("글이 삭제되었습니다.", "success")
  return redirect(url_for("index"))


# ---------- 댓글 ----------

@app.route("/posts/<int:post_id>/comments", methods=["POST"])
def create_comment(post_id):
  get_post_or_404(post_id)
  values = form_values("author", "password", "content")
  if not all(values.values()):
    flash("댓글의 모든 항목을 입력해 주세요.", "danger")
    return redirect(url_for("post_detail", post_id=post_id))

  execute(
    "INSERT INTO comments (post_id, author, password, content) VALUES (%s, %s, %s, %s)",
    (post_id, values["author"], values["password"], values["content"]),
  )
  return redirect(url_for("post_detail", post_id=post_id))


@app.route("/comments/<int:comment_id>/delete", methods=["POST"])
def delete_comment(comment_id):
  comment = query("SELECT * FROM comments WHERE id = %s", (comment_id,), one=True)
  if comment is None:
    abort(404)
  if request.form.get("password", "") != comment["password"]:
    flash("댓글 비밀번호가 일치하지 않습니다.", "danger")
  else:
    execute("DELETE FROM comments WHERE id = %s", (comment_id,))
    flash("댓글이 삭제되었습니다.", "success")
  return redirect(url_for("post_detail", post_id=comment["post_id"]))


# ---------- 상태 확인 ----------

@app.route("/health")
def health():
  # 웹 EC2 → DB EC2 연결 확인용 (보안 그룹/네트워크 점검에 사용)
  try:
    query("SELECT 1", one=True)
  except pymysql.MySQLError as e:
    return {"status": "error", "db": str(e)}, 500
  return {"status": "ok", "db": "connected"}


if __name__ == "__main__":
  app.run(host="127.0.0.1", port=8000, debug=True)

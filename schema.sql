-- DB EC2에서 실행: sudo mariadb < schema.sql
CREATE DATABASE IF NOT EXISTS board
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE board;

-- 게시글 (실습용이라 password를 평문으로 저장한다. 실무에서는 반드시 해시로 저장할 것)
CREATE TABLE IF NOT EXISTS posts (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  title      VARCHAR(200) NOT NULL,
  content    TEXT         NOT NULL,
  author     VARCHAR(50)  NOT NULL,
  password   VARCHAR(100) NOT NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 댓글 (게시글이 삭제되면 함께 삭제)
CREATE TABLE IF NOT EXISTS comments (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  post_id    INT          NOT NULL,
  author     VARCHAR(50)  NOT NULL,
  password   VARCHAR(100) NOT NULL,
  content    TEXT         NOT NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_comments_post
    FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
);

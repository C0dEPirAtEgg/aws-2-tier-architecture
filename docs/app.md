# 앱 구조

Flask로 만든 단순한 게시판입니다. 인프라 실습에 집중할 수 있도록 ORM 없이 SQL을 직접 사용합니다.

- 기능: 글 목록/작성/조회/수정/삭제, 댓글 작성/삭제 (로그인 없이 작성자명 + 비밀번호)
- 스택: Python Flask · PyMySQL · Jinja2 · Bootstrap(CDN) · Gunicorn · Nginx · MariaDB

> ⚠️ 실습용이라 글·댓글 비밀번호를 **평문으로 저장**합니다. 실무에서는 반드시 해시(bcrypt 등)로 저장해야 합니다.

요청 흐름: `브라우저 → Nginx(80) → Gunicorn(127.0.0.1:8000) → Flask → PyMySQL → MariaDB(DB EC2:3306)`

## 폴더 구조

```
.
├── app.py              # Flask 라우트 (게시글/댓글 CRUD, /health)
├── db.py               # PyMySQL 연결 및 query/execute 헬퍼
├── schema.sql          # DB·테이블 생성 SQL (DB EC2에서 실행)
├── templates/          # Jinja2 화면
│   ├── base.html       #   공통 레이아웃, 하단에 응답한 서버 호스트명 표시
│   ├── index.html      #   글 목록
│   ├── detail.html     #   글 상세 + 댓글
│   └── form.html       #   글쓰기/수정 폼
├── deploy/
│   ├── gunicorn.service  # systemd 서비스 파일
│   └── nginx.conf        # Nginx 리버스 프록시 설정
├── requirements.txt
└── .env.example        # DB 접속 정보 예시
```

## 코드 읽는 순서

1. `schema.sql`: 테이블이 `posts`, `comments` 두 개뿐이고, 댓글은 글이 삭제되면 함께 삭제됩니다(`ON DELETE CASCADE`).
2. `db.py`: `.env`의 `DB_HOST`(DB EC2의 프라이빗 IP)로 접속합니다.
3. `app.py`: 라우트별로 SQL을 실행하고 템플릿을 렌더링합니다.

## 라우트

| 경로 | 메서드 | 설명 |
| --- | --- | --- |
| `/` | GET | 글 목록 |
| `/posts/new` | GET, POST | 글쓰기 |
| `/posts/<id>` | GET | 글 상세 + 댓글 |
| `/posts/<id>/edit` | GET, POST | 글 수정 (비밀번호 확인) |
| `/posts/<id>/delete` | POST | 글 삭제 (비밀번호 확인) |
| `/posts/<id>/comments` | POST | 댓글 작성 |
| `/comments/<id>/delete` | POST | 댓글 삭제 (비밀번호 확인) |
| `/health` | GET | DB 연결 확인 (`{"status": "ok"}`) |

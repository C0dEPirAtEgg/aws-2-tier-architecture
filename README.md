# AWS 2-Tier 실습용 게시판

AWS에서 **웹 티어(EC2) + DB 티어(EC2)** 로 나뉜 2-Tier 구조를 직접 구축해 보기 위한 Flask 게시판입니다.
앱은 최대한 단순하게 두고, 인프라 구성에 집중할 수 있도록 만들었습니다.

- 기능: 글 목록/작성/조회/수정/삭제, 댓글 작성/삭제 (로그인 없이 작성자명 + 비밀번호)
- 스택: Python Flask · Gunicorn · Nginx · MariaDB · Amazon Linux 2023

> ⚠️ 실습용이라 글·댓글 비밀번호를 **평문으로 저장**합니다. 실무에서는 반드시 해시(bcrypt 등)로 저장해야 합니다.

## 아키텍처

```
                 Internet
                    │  HTTP :80
┌───────────── VPC 10.0.0.0/16 ─────────────────────────────┐
│  ┌─ Public Subnet 10.0.1.0/24 ──────────────────────────┐ │
│  │  웹 EC2 (Tier 1)                        NAT Gateway   │ │
│  │  Nginx :80 → Gunicorn :8000 → Flask         ▲         │ │
│  └──────────────┬──────────────────────────────┼─────────┘ │
│                 │ :3306 (MariaDB)              │ 패키지 설치 │
│  ┌─ Private Subnet 10.0.2.0/24 ────────────────┼─────────┐ │
│  │  DB EC2 (Tier 2)  MariaDB :3306 ────────────┘         │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

요청 흐름: `브라우저 → Nginx(80) → Gunicorn(127.0.0.1:8000) → Flask → PyMySQL → MariaDB(DB EC2:3306)`

## 폴더 구조

```
.
├── app.py              # Flask 라우트 (게시글/댓글 CRUD, /health)
├── db.py               # PyMySQL 연결 및 query/execute 헬퍼
├── schema.sql          # DB·테이블 생성 SQL (DB EC2에서 실행)
├── templates/          # Jinja2 화면 (Bootstrap CDN 사용)
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

### 코드 읽는 순서

1. `schema.sql`: 테이블이 `posts`, `comments` 두 개뿐이고, 댓글은 글이 삭제되면 함께 삭제됩니다(`ON DELETE CASCADE`).
2. `db.py`: `.env`의 `DB_HOST`(DB EC2의 프라이빗 IP)로 접속합니다. ORM 없이 SQL을 직접 실행합니다.
3. `app.py`: 라우트별로 SQL을 실행하고 템플릿을 렌더링합니다.

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

---

## 1. AWS 인프라 구성 (콘솔)

리전은 서울(`ap-northeast-2`)을 기준으로 합니다.

| 리소스 | 설정 |
| --- | --- |
| VPC | `10.0.0.0/16` |
| Public Subnet | `10.0.1.0/24` (AZ a), 퍼블릭 IP 자동 할당 활성화 |
| Private Subnet | `10.0.2.0/24` (AZ a) |
| Internet Gateway | VPC에 연결 |
| NAT Gateway | Public Subnet에 생성, Elastic IP 할당 |
| Public 라우팅 테이블 | `0.0.0.0/0 → IGW`, Public Subnet 연결 |
| Private 라우팅 테이블 | `0.0.0.0/0 → NAT Gateway`, Private Subnet 연결 |
| 키 페어 | 두 EC2에서 공용으로 사용 (예: `board-key.pem`) |

**보안 그룹**

| 이름 | 인바운드 | 소스 |
| --- | --- | --- |
| `web-sg` | HTTP 80 | `0.0.0.0/0` |
| | SSH 22 | 내 IP |
| `db-sg` | MySQL/Aurora 3306 | `web-sg` (보안 그룹 ID) |
| | SSH 22 | `web-sg` (보안 그룹 ID) |

> `db-sg`의 소스를 IP가 아닌 **`web-sg`로 지정**하는 것이 핵심입니다. 웹 EC2에서 오는 요청만 DB에 닿을 수 있습니다.

**EC2**

| 이름 | 서브넷 | 보안 그룹 | AMI / 타입 |
| --- | --- | --- | --- |
| `board-web` | Public | `web-sg` | Amazon Linux 2023 / t3.micro |
| `board-db` | Private | `db-sg` | Amazon Linux 2023 / t3.micro |

## 2. EC2 접속 (웹 EC2를 Bastion으로 사용)

```bash
# 로컬(맥)에서: 키를 ssh-agent에 등록해 두면 점프 접속 시에도 같은 키가 사용됨
chmod 400 board-key.pem
ssh-add board-key.pem

# 웹 EC2 접속
ssh ec2-user@<웹 EC2 퍼블릭 IP>

# DB EC2 접속 (웹 EC2를 거쳐서)
ssh -J ec2-user@<웹 EC2 퍼블릭 IP> ec2-user@<DB EC2 프라이빗 IP>
```

## 3. DB EC2 설정 (Tier 2)

```bash
# MariaDB 설치 및 실행 (NAT Gateway를 통해 인터넷으로 다운로드)
sudo dnf install -y mariadb105-server
sudo systemctl enable --now mariadb

# 스키마 생성 (레포의 schema.sql 다운로드 후 실행)
curl -O https://raw.githubusercontent.com/C0dEPirAtEgg/aws-2-tier-architecture/main/schema.sql
sudo mariadb < schema.sql
```

앱이 사용할 DB 계정을 만듭니다. `'10.0.1.%'`는 **Public Subnet(웹 EC2)에서만 접속을 허용**한다는 뜻입니다.

```bash
sudo mariadb
```

```sql
CREATE USER 'board'@'10.0.1.%' IDENTIFIED BY '원하는-비밀번호';
GRANT ALL PRIVILEGES ON board.* TO 'board'@'10.0.1.%';
FLUSH PRIVILEGES;
EXIT;
```

MariaDB가 외부(웹 EC2)의 접속을 받는지 확인합니다.

```bash
sudo ss -tlnp | grep 3306
# 0.0.0.0:3306 또는 *:3306 이면 OK
# 127.0.0.1:3306 이면 /etc/my.cnf.d/mariadb-server.cnf 의 [mysqld] 에
# bind-address=0.0.0.0 을 추가하고 sudo systemctl restart mariadb
```

## 4. 웹 EC2 설정 (Tier 1)

```bash
# 패키지 설치
sudo dnf install -y git nginx python3 python3-pip mariadb105

# (선택) DB 연결 먼저 확인: 비밀번호 입력 후 접속되면 네트워크·보안 그룹·계정 설정 OK
mariadb -h <DB EC2 프라이빗 IP> -u board -p board

# 코드 받기
cd ~
git clone https://github.com/C0dEPirAtEgg/aws-2-tier-architecture.git
cd aws-2-tier-architecture

# 가상환경 및 의존성 설치
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 환경변수 설정: DB_HOST, DB_PASSWORD, SECRET_KEY 수정
cp .env.example .env
vi .env
```

### Gunicorn (systemd)

```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/board.service
sudo systemctl daemon-reload
sudo systemctl enable --now board

# 확인
sudo systemctl status board
curl http://127.0.0.1:8000/health
```

### Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/conf.d/board.conf

# 기본 설정에 default_server가 있으면 충돌하므로 제거
grep -n "default_server" /etc/nginx/nginx.conf && sudo sed -i 's/ default_server//' /etc/nginx/nginx.conf

sudo nginx -t
sudo systemctl enable --now nginx
```

## 5. 동작 확인

- 브라우저에서 `http://<웹 EC2 퍼블릭 IP>` 접속 → 글 목록 화면
- `http://<웹 EC2 퍼블릭 IP>/health` → `{"db":"connected","status":"ok"}`
- 페이지 하단의 "응답한 웹 서버"에 웹 EC2의 호스트명이 표시됩니다.

## 문제 해결

| 증상 | 확인할 것 |
| --- | --- |
| 브라우저 접속이 안 됨 | `web-sg` 80 인바운드, 퍼블릭 IP로 접속했는지 (`https://`가 아니라 `http://`) |
| Nginx 기본 환영 페이지가 나옴 | `/etc/nginx/nginx.conf`의 `default_server` 제거 후 `sudo systemctl reload nginx` |
| `502 Bad Gateway` | Gunicorn이 꺼져 있음 → `sudo journalctl -u board -n 50` |
| `/health`가 `timed out` | `db-sg` 3306 인바운드 소스가 `web-sg`인지, DB_HOST가 프라이빗 IP인지 |
| `/health`가 `Access denied` | DB 계정의 호스트(`'10.0.1.%'`)와 `.env`의 비밀번호 |
| `/health`가 `Connection refused` | MariaDB 실행 여부, `bind-address` 설정 |
| DB EC2에서 `dnf install` 실패 | Private 라우팅 테이블의 `0.0.0.0/0 → NAT Gateway` |

코드를 수정한 뒤에는 웹 EC2에서 `git pull && sudo systemctl restart board`로 반영합니다.

## 실습 후 정리 (과금 주의)

**NAT Gateway와 Elastic IP는 사용하지 않아도 시간당 과금**됩니다. 실습이 끝나면 아래 순서로 삭제하세요.

1. EC2 2대 종료
2. NAT Gateway 삭제 → 삭제 완료 후 Elastic IP 릴리스
3. VPC 삭제 (서브넷·라우팅 테이블·IGW·보안 그룹이 함께 삭제됨)

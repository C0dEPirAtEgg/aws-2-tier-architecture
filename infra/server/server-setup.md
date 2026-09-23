# 서버 설정

[AWS 리소스](../aws/) 문서대로 VPC·보안 그룹·EC2를 만든 뒤, **EC2 안에서** 진행하는 작업입니다.

## 작업 순서

| 순서 | 어디서 | 작업 | 확인 방법 |
| --- | --- | --- | --- |
| 1 | 로컬(맥) | 웹 EC2, DB EC2 접속 | 프롬프트의 호스트명 |
| 2 | DB EC2 | MariaDB 설치 · 스키마 · 계정 · 외부 접속 허용 | `SHOW GRANTS`, `ss -tlnp` |
| 3 | 웹 EC2 | 코드 · venv · `.env` · Gunicorn · Nginx | `curl /health` |
| 4 | 브라우저 | 게시판 접속 | 글 목록 화면 |

DB를 먼저 설정해야 웹 EC2에서 바로 연결을 확인할 수 있습니다.

### 명령을 어디서 실행하는지 항상 확인하세요

이 문서의 명령은 **로컬 / 웹 EC2 / DB EC2** 세 곳에서 나눠 실행합니다. 각 코드 블록 첫 줄에 실행 위치를 적어 두었습니다.
지금 어느 서버에 있는지는 프롬프트의 호스트명(프라이빗 IP)으로 구분합니다.

```
[ec2-user@ip-10-0-1-249 ~]$   ← 10.0.1.x: 웹 EC2 (Public Subnet)
[ec2-user@ip-10-0-2-37 ~]$    ← 10.0.2.x: DB EC2 (Private Subnet)
```

> DB 작업을 마치고 `exit` 하지 않은 채 웹 EC2 명령을 실행하는 실수가 가장 흔합니다. 예를 들어 DB EC2에서 `curl 127.0.0.1:8000`을 하면 `Could not connect to server`가 납니다.

### 미리 적어 둘 값

| 값 | 확인 위치 | 사용하는 곳 |
| --- | --- | --- |
| 웹 EC2 퍼블릭 IP | EC2 콘솔 → `board-web` | SSH 접속, 브라우저 접속 |
| DB EC2 프라이빗 IP | EC2 콘솔 → `board-db` | SSH 점프 접속, 웹 EC2의 `.env` (`DB_HOST`) |
| DB 비밀번호 | 직접 정함 | DB 계정 생성, 웹 EC2의 `.env` (`DB_PASSWORD`) |

## 1. EC2 접속 (웹 EC2를 Bastion으로 사용)

DB EC2는 퍼블릭 IP가 없어 인터넷에서 바로 접속할 수 없습니다. **웹 EC2를 거쳐서(점프)** 들어갑니다.

```bash
# [로컬] 키 권한 설정 후 ssh-agent에 등록
# 등록해 두면 점프 접속할 때 웹 EC2에 키를 복사하지 않아도 같은 키가 사용됩니다
chmod 400 board-key.pem
ssh-add board-key.pem

# [로컬] 웹 EC2 접속
ssh ec2-user@<웹 EC2 퍼블릭 IP>

# [로컬] DB EC2 접속 (웹 EC2를 거쳐서)
ssh -J ec2-user@<웹 EC2 퍼블릭 IP> ec2-user@<DB EC2 프라이빗 IP>
```

터미널 창을 두 개 열어 하나는 웹 EC2, 하나는 DB EC2에 접속해 두면 헷갈리지 않습니다.

## 2. DB EC2 설정 (Tier 2)

### 2-1. MariaDB 설치

DB EC2는 Private Subnet에 있지만, NAT Gateway를 통해 인터넷에서 패키지를 받을 수 있습니다.

```bash
# [DB EC2] 설치 및 실행 (부팅 시 자동 시작)
sudo dnf install -y mariadb105-server
sudo systemctl enable --now mariadb

# [DB EC2] 확인: active 가 나오면 OK
systemctl is-active mariadb
```

> `dnf install`이 멈추거나 실패하면 Private 라우팅 테이블에 `0.0.0.0/0 → NAT Gateway`가 있는지 확인하세요.

### 2-2. 스키마 생성

`schema.sql`은 `board` 데이터베이스와 `posts`, `comments` 테이블을 만듭니다.

```bash
# [DB EC2] 레포의 schema.sql 다운로드 후 실행
curl -O https://raw.githubusercontent.com/C0dEPirAtEgg/aws-2-tier-architecture/main/app/schema.sql
sudo mariadb < schema.sql

# [DB EC2] 확인: board 가 목록에 있으면 OK
sudo mariadb -e "SHOW DATABASES;"
```

> **`mariadb` 명령에는 항상 `sudo`를 붙입니다.** MariaDB의 root 계정은 비밀번호 대신 "리눅스 root 사용자인가"로 로그인을 허용합니다. `sudo` 없이 실행하면 `Access denied for user 'ec2-user'@'localhost'`가 납니다.

### 2-3. 앱 계정 만들기

앱이 사용할 `board` 계정을 만들고, `board` 데이터베이스에 대한 권한을 줍니다.

```bash
# [DB EC2]
sudo mariadb
```

```sql
-- '10.0.1.%' = Public Subnet(웹 EC2)에서 오는 접속만 허용
CREATE USER 'board'@'10.0.1.%' IDENTIFIED BY '원하는-비밀번호';

-- 계정만 만들고 이 줄을 빠뜨리면 로그인은 되지만 1044 에러가 납니다
GRANT ALL PRIVILEGES ON board.* TO 'board'@'10.0.1.%';
FLUSH PRIVILEGES;

-- 확인: GRANT ALL PRIVILEGES ON `board`.* 줄이 보이면 OK
SHOW GRANTS FOR 'board'@'10.0.1.%';
EXIT;
```

### 2-4. 외부 접속 허용

MariaDB가 `127.0.0.1`에서만 기다리고 있으면 웹 EC2에서 접속할 수 없습니다.

```bash
# [DB EC2]
sudo ss -tlnp | grep 3306
```

| 결과 | 의미 | 조치 |
| --- | --- | --- |
| `0.0.0.0:3306` 또는 `*:3306` | 모든 네트워크에서 접속 가능 | 없음 |
| `127.0.0.1:3306` | DB EC2 자기 자신만 접속 가능 | 아래 설정 |

```bash
# [DB EC2] /etc/my.cnf.d/mariadb-server.cnf 의 [mysqld] 아래에 bind-address=0.0.0.0 추가
sudo vi /etc/my.cnf.d/mariadb-server.cnf
sudo systemctl restart mariadb
```

모든 네트워크에 열어도 괜찮은 이유: 실제로 3306에 닿을 수 있는 건 `db-sg`가 허용한 `web-sg`뿐이고, DB 계정도 `10.0.1.%`에서만 로그인할 수 있기 때문입니다.

DB EC2 작업은 여기까지입니다. `exit`로 빠져나오세요.

## 3. 웹 EC2 설정 (Tier 1)

### 3-1. 패키지 설치

```bash
# [웹 EC2]
# mariadb105: DB 서버가 아니라 접속 테스트용 클라이언트입니다
sudo dnf install -y git nginx python3 python3-pip mariadb105
```

### 3-2. DB 연결 먼저 확인

앱을 올리기 전에 **네트워크 · 보안 그룹 · DB 계정**이 맞는지 따로 확인해 두면, 나중에 문제가 생겼을 때 원인을 좁히기 쉽습니다.

```bash
# [웹 EC2] 비밀번호 입력 후 MariaDB 프롬프트가 나오면 OK (EXIT로 종료)
mariadb -h <DB EC2 프라이빗 IP> -u board -p board
```

| 에러 | 원인 |
| --- | --- |
| 한참 멈춘 뒤 timeout | `db-sg` 3306 인바운드, `DB EC2 프라이빗 IP` 오타 |
| `Connection refused` | MariaDB 꺼짐, `bind-address` (2-4) |
| `1045 Access denied ... (using password: YES)` | 비밀번호, 계정의 호스트(`10.0.1.%`) |
| `1044 Access denied ... to database 'board'` | `GRANT` 누락 (2-3) |

### 3-3. 코드 받기

```bash
# [웹 EC2]
cd ~
git clone https://github.com/C0dEPirAtEgg/aws-2-tier-architecture.git
cd aws-2-tier-architecture/app
```

이후 웹 EC2 작업은 모두 **`~/aws-2-tier-architecture/app`** 폴더에서 진행합니다.

### 3-4. 가상환경(venv) 및 의존성 설치

```bash
# [웹 EC2] 반드시 app 폴더 안에서 실행
cd ~/aws-2-tier-architecture/app
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 확인: 경로가 /home/ec2-user/aws-2-tier-architecture/app/venv/bin/python3 이면 OK
head -1 venv/bin/gunicorn
```

> **venv는 만든 자리에서만 동작합니다.** venv 안의 실행 파일은 첫 줄에 만들 당시의 Python 경로를 절대 경로로 기록합니다. 다른 폴더에서 만든 venv를 `mv`로 옮기면 그 경로가 맞지 않아 Gunicorn이 `203/EXEC`로 실행되지 않습니다. 위치가 잘못됐다면 옮기지 말고 `rm -rf venv` 후 `app/`에서 다시 만드세요.

### 3-5. 환경변수(.env) 설정

```bash
# [웹 EC2]
cp .env.example .env
vi .env
```

| 변수 | 값 |
| --- | --- |
| `SECRET_KEY` | 아무 긴 문자열 (Flask 세션 서명용) |
| `DB_HOST` | DB EC2 **프라이빗** IP (`10.0.2.x`) |
| `DB_PORT` | `3306` |
| `DB_USER` | `board` |
| `DB_PASSWORD` | 2-3에서 정한 비밀번호 |
| `DB_NAME` | `board` |

`.env`도 `app/` 폴더 안에 있어야 앱이 읽습니다.

### 3-6. Gunicorn 직접 실행해 보기

systemd에 등록하기 전에 직접 띄워 보면 에러 메시지를 화면에서 바로 볼 수 있습니다.

```bash
# [웹 EC2] 실행 (Ctrl+C로 종료)
cd ~/aws-2-tier-architecture/app
./venv/bin/gunicorn --bind 127.0.0.1:8000 app:app
```

```bash
# [웹 EC2] 다른 터미널에서 확인
curl http://127.0.0.1:8000/health
# {"db":"connected","status":"ok"} 이면 OK
```

`Booting worker` 로그가 보이고 `/health`가 OK면 `Ctrl+C`로 종료하고 다음 단계로 넘어갑니다.

### 3-7. Gunicorn을 서비스로 등록 (systemd)

직접 실행한 Gunicorn은 SSH 접속을 끊으면 같이 꺼집니다. systemd에 등록하면 백그라운드에서 계속 실행되고, 서버를 재부팅해도 자동으로 다시 켜집니다.

[`gunicorn.service`](gunicorn.service)가 하는 일:
- `WorkingDirectory`: `app/` 폴더에서 실행 (여기서 `.env`를 읽음)
- `ExecStart`: `app/venv`의 Gunicorn으로 워커 2개를 `127.0.0.1:8000`에 띄움
- `Restart=always`: 죽으면 자동 재시작

```bash
# [웹 EC2]
sudo cp ../infra/server/gunicorn.service /etc/systemd/system/board.service
sudo systemctl daemon-reload
sudo systemctl enable --now board

# 확인: Active: active (running) 이면 OK
sudo systemctl status board --no-pager
curl http://127.0.0.1:8000/health
```

실패했다면 로그부터 확인합니다.

```bash
# [웹 EC2]
sudo journalctl -u board -n 30 --no-pager
```

> 짧은 시간에 5번 연달아 실패하면 systemd가 재시작을 막습니다(`Start request repeated too quickly`). 원인을 고친 뒤 `sudo systemctl reset-failed board`를 실행하고 다시 시작하세요.

### 3-8. Nginx 설정

Gunicorn은 `127.0.0.1`에서만 기다리므로 외부에서 직접 닿지 않습니다. Nginx가 80번 포트로 받은 요청을 Gunicorn에 전달합니다([`nginx.conf`](nginx.conf)).

```bash
# [웹 EC2]
sudo cp ../infra/server/nginx.conf /etc/nginx/conf.d/board.conf

# 기본 설정(nginx.conf)에도 default_server가 있으면 충돌하므로 제거
grep -n "default_server" /etc/nginx/nginx.conf && sudo sed -i 's/ default_server//' /etc/nginx/nginx.conf

# 문법 검사 후 실행
sudo nginx -t
sudo systemctl enable --now nginx

# 확인: Gunicorn과 같은 결과가 80번 포트로 나오면 OK
curl http://127.0.0.1/health
```

## 4. 동작 확인

- 브라우저에서 `http://<웹 EC2 퍼블릭 IP>` 접속 → 글 목록 화면 (`https://`가 아니라 `http://`)
- `http://<웹 EC2 퍼블릭 IP>/health` → `{"db":"connected","status":"ok"}`
- 페이지 하단의 "응답한 웹 서버"에 웹 EC2의 호스트명이 표시됩니다.
- 글을 하나 써 본 뒤 DB EC2에서 `sudo mariadb -e "SELECT id, title FROM board.posts;"`로 데이터가 DB EC2에 저장됐는지 확인해 보세요.

## 5. 운영

### 코드 수정 반영

```bash
# [웹 EC2]
cd ~/aws-2-tier-architecture && git pull

# requirements.txt가 바뀌었을 때만
./app/venv/bin/pip install -r app/requirements.txt

sudo systemctl restart board
```

### 자주 쓰는 명령

| 목적 | 명령 (웹 EC2) |
| --- | --- |
| 앱 상태 | `sudo systemctl status board --no-pager` |
| 앱 로그 | `sudo journalctl -u board -n 50 --no-pager` |
| 앱 로그 실시간 | `sudo journalctl -u board -f` |
| 앱 재시작 | `sudo systemctl restart board` |
| Nginx 에러 로그 | `sudo tail -n 50 /var/log/nginx/error.log` |
| DB 연결 확인 | `curl http://127.0.0.1:8000/health` |

문제가 생기면 [문제 해결](troubleshooting.md)을 참고하세요.

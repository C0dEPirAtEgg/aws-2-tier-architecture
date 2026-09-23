# 서버 설정

[services](../services/) 문서대로 AWS 리소스를 만든 뒤, EC2 안에서 진행하는 작업입니다.

## 1. EC2 접속 (웹 EC2를 Bastion으로 사용)

```bash
# 로컬(맥)에서: 키를 ssh-agent에 등록해 두면 점프 접속 시에도 같은 키가 사용됨
chmod 400 board-key.pem
ssh-add board-key.pem

# 웹 EC2 접속
ssh ec2-user@<웹 EC2 퍼블릭 IP>

# DB EC2 접속 (웹 EC2를 거쳐서)
ssh -J ec2-user@<웹 EC2 퍼블릭 IP> ec2-user@<DB EC2 프라이빗 IP>
```

## 2. DB EC2 설정 (Tier 2)

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

## 3. 웹 EC2 설정 (Tier 1)

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

## 4. 동작 확인

- 브라우저에서 `http://<웹 EC2 퍼블릭 IP>` 접속 → 글 목록 화면
- `http://<웹 EC2 퍼블릭 IP>/health` → `{"db":"connected","status":"ok"}`
- 페이지 하단의 "응답한 웹 서버"에 웹 EC2의 호스트명이 표시됩니다.

코드를 수정한 뒤에는 웹 EC2에서 `git pull && sudo systemctl restart board`로 반영합니다.
문제가 생기면 [문제 해결](troubleshooting.md)을 참고하세요.

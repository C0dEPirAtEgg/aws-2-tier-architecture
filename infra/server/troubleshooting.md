# 문제 해결

| 증상 | 확인할 것 |
| --- | --- |
| 브라우저 접속이 안 됨 | `web-sg` 80 인바운드, 퍼블릭 IP로 접속했는지 (`https://`가 아니라 `http://`) |
| Nginx 기본 환영 페이지가 나옴 | `/etc/nginx/nginx.conf`의 `default_server` 제거 후 `sudo systemctl reload nginx` |
| `502 Bad Gateway` | Gunicorn이 꺼져 있음 → `sudo journalctl -u board -n 50` |
| `/health`가 `timed out` | `db-sg` 3306 인바운드 소스가 `web-sg`인지, `DB_HOST`가 프라이빗 IP인지 |
| `curl 127.0.0.1:8000`이 `Could not connect to server` | 웹 EC2에서 실행했는지(프롬프트 `ip-10-0-1-x`), 아니면 `sudo systemctl status board` |
| `board.service`가 `status=203/EXEC` | `app/venv`가 없거나 다른 곳에서 만든 venv를 옮김 → `head -1 app/venv/bin/gunicorn` 확인 후 `app/`에서 venv 재생성 |
| `Start request repeated too quickly` | 원인을 고친 뒤 `sudo systemctl reset-failed board` 후 재시작 |
| `/health`가 `1045 Access denied` | DB 계정의 호스트(`'10.0.1.%'`)와 `.env`의 비밀번호 |
| `/health`가 `1044 Access denied ... to database 'board'` | `GRANT ALL PRIVILEGES ON board.*` 누락, `.env`의 `DB_NAME` |
| `/health`가 `Connection refused` | MariaDB 실행 여부, `bind-address` 설정 |
| DB EC2에서 `dnf install` 실패 | Private 라우팅 테이블의 `0.0.0.0/0 → NAT Gateway` |
| DB EC2로 SSH 접속이 안 됨 | `db-sg` 22 인바운드 소스가 `web-sg`인지, `ssh-add`로 키를 등록했는지 |
| DB EC2에서 `Access denied for user 'ec2-user'@'localhost'` | `mariadb` 앞에 `sudo`를 붙였는지 |

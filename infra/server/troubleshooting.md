# 문제 해결

| 증상 | 확인할 것 |
| --- | --- |
| 브라우저 접속이 안 됨 | `web-sg` 80 인바운드, 퍼블릭 IP로 접속했는지 (`https://`가 아니라 `http://`) |
| Nginx 기본 환영 페이지가 나옴 | `/etc/nginx/nginx.conf`의 `default_server` 제거 후 `sudo systemctl reload nginx` |
| `502 Bad Gateway` | Gunicorn이 꺼져 있음 → `sudo journalctl -u board -n 50` |
| `/health`가 `timed out` | `db-sg` 3306 인바운드 소스가 `web-sg`인지, `DB_HOST`가 프라이빗 IP인지 |
| `/health`가 `Access denied` | DB 계정의 호스트(`'10.0.1.%'`)와 `.env`의 비밀번호 |
| `/health`가 `Connection refused` | MariaDB 실행 여부, `bind-address` 설정 |
| DB EC2에서 `dnf install` 실패 | Private 라우팅 테이블의 `0.0.0.0/0 → NAT Gateway` |
| DB EC2로 SSH 접속이 안 됨 | `db-sg` 22 인바운드 소스가 `web-sg`인지, `ssh-add`로 키를 등록했는지 |

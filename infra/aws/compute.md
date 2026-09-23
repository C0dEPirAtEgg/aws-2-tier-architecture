# 컴퓨팅

실제로 게시판이 실행되는 서버입니다. 2-Tier의 각 티어가 EC2 한 대씩입니다.

## EC2

AWS의 가상 서버입니다. 웹 EC2에는 Nginx·Gunicorn·Flask를, DB EC2에는 MariaDB를 설치합니다. 서버 안에서 하는 작업은 [서버 설정](../server/server-setup.md)을 참고하세요.

| 항목 | 웹 EC2 (Tier 1) | DB EC2 (Tier 2) |
| --- | --- | --- |
| 이름 | `board-web` | `board-db` |
| AMI | Amazon Linux 2023 | Amazon Linux 2023 |
| 인스턴스 유형 | `t3.micro` | `t3.micro` |
| 키 페어 | `board-key` | `board-key` |
| VPC / 서브넷 | `board-vpc` / `board-public` | `board-vpc` / `board-private` |
| 퍼블릭 IP | 자동 할당 | 없음 |
| 보안 그룹 | `web-sg` | `db-sg` |
| 설치 소프트웨어 | Nginx, Gunicorn, Flask | MariaDB |
| 접속 방법 | `ssh ec2-user@<퍼블릭 IP>` | 웹 EC2를 거쳐 `ssh -J` |

> DB EC2의 **프라이빗 IP**는 웹 EC2의 `.env`(`DB_HOST`)에 들어갑니다. 생성 후 콘솔에서 확인해 두세요.

# AWS 2-Tier 실습용 게시판

AWS에서 **웹 티어(EC2) + DB 티어(EC2)** 로 나뉜 2-Tier 구조를 직접 구축해 보기 위한 Flask 게시판입니다.

## 아키텍처

![AWS 2-Tier 아키텍처](images/aws-2tier-architecture.png)

## Services

구축해야 하는 AWS 서비스와 이 실습의 설정값입니다.

| 문서 | 서비스 |
| --- | --- |
| [네트워크](services/network.md) | VPC · 서브넷 · 인터넷 게이트웨이 · NAT 게이트웨이 · 라우팅 테이블 |
| [보안](services/security.md) | 보안 그룹 · 키 페어 |
| [컴퓨팅](services/compute.md) | EC2 (웹 / DB) |

## Docs

| 문서 | 내용 |
| --- | --- |
| [앱 구조](docs/app.md) | 폴더 구조 · 코드 읽는 순서 · 라우트 |
| [서버 설정](docs/server-setup.md) | EC2 접속 · MariaDB · Gunicorn · Nginx 설정 |
| [문제 해결](docs/troubleshooting.md) | 증상별 확인 사항 |

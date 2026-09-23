# 네트워크

웹 EC2와 DB EC2가 놓일 네트워크를 만듭니다. 웹은 인터넷에 열린 **Public Subnet**, DB는 외부에서 직접 닿을 수 없는 **Private Subnet**에 둡니다.

리전: 서울 (`ap-northeast-2`)

## VPC

AWS 안에 만드는 나만의 격리된 네트워크입니다. 이 실습의 모든 리소스가 이 안에 들어갑니다.

| 항목 | 값 |
| --- | --- |
| 이름 | `board-vpc` |
| IPv4 CIDR | `10.0.0.0/16` |

## 서브넷

VPC를 나눈 구역입니다. 라우팅 테이블에 따라 Public/Private이 결정됩니다.

| 이름 | CIDR | 가용 영역 | 용도 | 비고 |
| --- | --- | --- | --- | --- |
| `board-public` | `10.0.1.0/24` | `ap-northeast-2a` | 웹 EC2, NAT Gateway | 퍼블릭 IPv4 자동 할당 활성화 |
| `board-private` | `10.0.2.0/24` | `ap-northeast-2a` | DB EC2 | |

## 인터넷 게이트웨이 (IGW)

VPC와 인터넷을 연결하는 출입구입니다. 사용자가 웹 EC2에 접속하려면 반드시 필요합니다.

| 항목 | 값 |
| --- | --- |
| 이름 | `board-igw` |
| 연결 | `board-vpc` |

## NAT 게이트웨이

Private Subnet의 DB EC2가 **밖으로만** 인터넷에 나갈 수 있게 해 줍니다. MariaDB 패키지 설치에 사용하며, 외부에서 DB EC2로 들어오는 연결은 막힌 상태가 유지됩니다.

| 항목 | 값 |
| --- | --- |
| 이름 | `board-nat` |
| 서브넷 | `board-public` (Public에 만들어야 함) |
| 연결 유형 | 퍼블릭 |
| 탄력적 IP | 새로 할당 |

## 라우팅 테이블

서브넷에서 나가는 트래픽을 어디로 보낼지 정합니다. **기본 경로(`0.0.0.0/0`)가 IGW면 Public, NAT면 Private**입니다.

| 이름 | 경로 | 대상 | 연결 서브넷 |
| --- | --- | --- | --- |
| `board-public-rt` | `0.0.0.0/0` | `board-igw` | `board-public` |
| `board-private-rt` | `0.0.0.0/0` | `board-nat` | `board-private` |

> VPC 내부 통신(`10.0.0.0/16 → local`)은 두 테이블에 자동으로 들어 있어서, 웹 EC2 ↔ DB EC2 통신은 따로 설정하지 않아도 됩니다.

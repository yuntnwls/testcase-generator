# PoC 테스트를 위한 Mock Data 설계 및 시나리오

본 문서는 실제 프로젝트에 구현된 Vector DB와 Ontology의 데이터셋을 기술하고, 이를 활용해 **복합 제어(Condition, Loop)** 및 **논리 검증**의 우수성을 증명하는 시연 시나리오를 정의합니다.

## 1. 실제 구현된 Mock Data 구성

현재 `data/` 디렉토리에 구축된 실제 데이터셋 명세입니다.

### 1-1. Vector DB 시그널 (7개 핵심 시그널)

RAG 엔진은 사용자의 모호한 일상어를 아래 시그널로 정밀하게 매핑합니다.

| ID | Logical Name | 주요 키워드 (Search Text) | 데이터 타입 | 설명 |
|:---|:---|:---|:---|:---|
| sig_veh_spd | `VehicleSpeed` | 속도, 차속, 엑셀, 가속, 감속, 브레이크, km/h | float | 차량 주행 속도 제어 |
| sig_ign_sta | `Ignition_Status` | 엔진, 시동, 발동기, 켜다, 끄다, IGN, start | enum (ON, OFF) | 차량 엔진 시동 상태 |
| sig_hlmp_sta | `HeadLamp_State` | 전조등, 헤드램프, 앞불, 라이트, 상/하향등 | enum (OFF, LOW, HIGH) | 전조등 조명 제어 |
| sig_door_sta | `Door_Status` | 문, 도어, 열림, 닫힘, 잠금, 해제, lock, open | enum (OPEN, CLOSED, LOCKED) | 도어 개폐 및 잠금 |
| sig_wiper_sta | `Wiper_State` | 와이퍼, 유리닦이, 비, 눈, 워셔액 | enum (OFF, LOW, HIGH, AUTO) | 와이퍼 작동 상태 |
| sig_hazard_sw | `HazardLightSw` | 비상등, 해저드, 깜빡이, 긴급/양방향 깜빡이 | enum (ON, OFF) | 비상등 스위치 제어 |
| sig_warn_lamp | `WarningLamp` | 경고, 알람, 경보, 위험, 알림, 경고등 | enum (ON, OFF) | 경고등/알람 상태 제어 |

### 1-2. Ontology (Knowledge Graph) 룰

시그널 간의 물리적/논리적 제약 사항을 정의하여 LLM이 상식적인 코드를 생성하도록 유도합니다.

1.  **[선행 조건]** `VehicleSpeed` 조작 시 `Ignition_Status == ON` 필수.
2.  **[선행 조건]** `Wiper_State` 조작 시 `Ignition_Status == ON` 필수.
3.  **[사이드 이팩트]** `HeadLamp_State` 조작 시 `Battery_Voltage` 감소 (분석용).
4.  **[위험/Conflict]** `VehicleSpeed > 0` (주행 중) 상태에서 `Door_Status == OPEN` 금지.

---

## 2. 복합 제어 데모 시나리오 (PoC)

구축된 데이터를 기반으로, 시스템이 **복잡한 논리 구조**를 어떻게 해석하는지 보여주는 데모 시나리오입니다.

### 🍅 시나리오 1: 복합 조건부 제어 (CONDITION)
- **사용자 입력**: `"차량 속도가 10 km/h 이상이면 도어를 잠그고, 그렇지 않으면 도어를 해제한다."`
- **RAG 분석**:
  - "차량 속도" -> `VehicleSpeed` 매핑
  - "도어 잠금" -> `Door_Status = LOCKED` 매핑
  - "도어 해제" -> `Door_Status = UNLOCKED` 매핑
- **LLM 해석**: `CONDITION` 타입을 최상위로 두고, `if_body`와 `else_body`에 각각 `SET` 동작을 분배하여 생성.
- **핵심 포인트**: 자연어 조건절을 프로그래밍 논리 구조로 정확히 변환.

### 🍅 시나리오 2: 반복 동작 및 시간 대기 (LOOP + WAIT)
- **사용자 입력**: `"와이퍼를 LOW로 설정하고 2초 대기하는 동작을 3회 반복한다."`
- **RAG 분석**:
  - "와이퍼 LOW" -> `Wiper_State = LOW`
- **LLM 해석**: `LOOP` 컨테이너(count=3) 내부에 `SET`과 `WAIT` 동작을 순차적으로 배치.
- **핵심 포인트**: 단순 스텝 나열이 아닌 '제어 구조'를 이해하여 효율적인 코드 생성.

### 🍅 시나리오 3: 은어 처리 및 RAG 매핑 (Ambiguity)
- **사용자 입력**: `"풀악셀 밟고 긴급 깜빡이 켜!"`
- **RAG 분석**:
  - "풀악셀" -> `VehicleSpeed` (유사도 기반 매핑)
  - "긴급 깜빡이" -> `HazardLightSw = ON`
- **핵심 포인트**: 도메인 특화 용어가 아닌 일상어/은어도 임베딩 유사도를 통해 정확한 시그널로 연결함.

### 🍅 시나리오 4: 논리적 결함 방어 (Fault Protection)
- **사용자 입력**: `"시동이 꺼진 상태에서 와이퍼를 가장 빠르게 돌려라."`
- **Ontology 검증**:
  - `Wiper_State` 조작 전 `Ignition_Status == ON` 조건 미충족 감지.
- **LLM 대응**: 
  - `UNKNOWN` IR로 분류하여 실행 중단 및 사유 명시 (`reason: "Wiper requires Ignition ON"`).
  - 또는 `# WARNING` 주석과 함께 선행 동작(`Ignition ON`) 코드를 자동 삽입.
- **핵심 포인트**: 물리적으로 불가능한 테스트 스크립트 생성을 사전에 방지.

---

## 3. 적용 및 테스트 방법

1.  **데이터 로드**: `CoreEngine` 구동 시 `data/mock_vector_db.json`을 읽어 ChromaDB를 초기화합니다.
2.  **테스트 실행**: `tests/integration/test_control_tc_local_llm.py`를 실행하여 위 시나리오들이 실제 IR로 변환되는지 검증합니다.
3.  **UI 시연**: Streamlit 화면에서 위 시나리오 텍스트를 입력하여 생성된 Python 코드의 품질을 육안으로 확인합니다.

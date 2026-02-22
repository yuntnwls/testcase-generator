# PoC 테스트를 위한 Mock Data 설계 및 시나리오

본 문서는 Vector DB와 Ontology의 기능(의미론적 검색 및 논리 검증)을 뚜렷하게 보여주기 위해 기획된 **종합 샘플 데이터(Mock Data)**와 이를 활용한 **검증 시나리오**를 정의합니다.

## 1. 테스트용 Mock Data 규모 및 구성

테스트(PoC)를 시각적으로 잘 보여주기 위해서는 너무 방대한 데이터보다는, 시스템이 겪을 수 있는 **다양한 예외 케이스**를 커버할 수 있는 15~20개 수준의 시그널과 5~10개의 관계망(Rule)이 적합합니다. 

다음과 같은 4가지 핵심 도메인 그룹으로 데이터를 구성합니다.

### 1-1. Vector DB 샘플 데이터 (총 15개 시그널)

**A. 동력/오토모티브 코어 (주행 관련)**
*   `Ignition_Status`: [엔진, 시동, 발동기, 켜다, 끄다, IGN]
*   `VehicleSpeed`: [속도, 차속, 엑셀, 가속, 감속, 브레이크 밟기, km/h, 속력]
*   `Gear_Position`: [기어, 변속기, P단, D단, R단, N단, 주차 모드, 주행 모드]
*   `Battery_Voltage`: [배터리, 전압, 전원, 배터리 레벨, V]

**B. 바디 제어 (조명 및 도어)**
*   `HeadLamp_State`: [전조등, 헤드램프, 앞불, 라이트, 상향등, 하향등]
*   `TurnSignal_Status`: [방향지시등, 깜빡이, 좌측 깜빡이, 우측 깜빡이, 턴시그널]
*   `Door_Lock_Status`: [문, 도어, 잠금, 해제, 차문 닫기, 차문 열기]
*   `Window_Position`: [창문, 윈도우, 열기, 닫기, 창문 내리기]

**C. 공조 시스템 (HVAC)**
*   `HVAC_Power`: [에어컨, 히터, 공조기, 냉방, 난방, 전원]
*   `Cabin_Temperature`: [온도, 실내 온도, 덥다, 춥다, 도, °C]
*   `Blower_Speed`: [풍량, 바람 세기, 팬 속도, 강풍, 약풍]

**D. ADAS (첨단 운전자 보조)**
*   `CruiseControl_State`: [크루즈 제어, 자동 주행, 정속 주행, CC]
*   `LaneKeeping_State`: [차선 유지, LKA, 차선 이탈 방지]

### 1-2. Ontology (Knowledge Graph) 샘플 룰 (총 7개 규칙)

시그널 간의 연관 관계를 정의하여 LLM이 상식적으로 코드를 짜도록 유도합니다.

1.  **[선행 조건]** `VehicleSpeed` (>0)를 조작하려면 `Ignition_Status` == `ON` 이어야 한다.
2.  **[선행 조건]** `VehicleSpeed` (>0)를 조작하려면 `Gear_Position` == `D` 또는 `R` 이어야 한다.
3.  **[선행 조건]** `Ignition_Status`를 `ON` 하려면 `Gear_Position` == `P` 이어야 한다. (급발진 방지)
4.  **[충돌 방지]** `Door_Lock_Status` == `LOCK` 상태에서는 `Window_Position`을 조작할 수 없다. *(임의의 가상 룰)*
5.  **[선행 조건]** `HVAC_Power`를 켜려면 `Ignition_Status` == `ON` 이어야 한다. (배터리 방전 방지)
6.  **[제약 사항]** `CruiseControl_State`를 켜려면 `VehicleSpeed` 가 `30` 이상이어야 한다.
7.  **[사이드 이펙트]** `HeadLamp_State`가 `HIGH` (상향등) 이면 `Battery_Voltage`의 소모량이 증가한다.

---

## 2. 시연(PoC)을 위한 4단계 데모 시나리오

구축된 데이터를 기반으로, 아래 4가지 시나리오를 통해 시스템의 우수성을 증명할 수 있도록 설계합니다.

### 🍅 시나리오 1: 단순 동의어 처리 (Happy Path)
- **사용자 입력**: `"엑셀을 밟아 시속 60으로 맞추고, 에어컨을 튼다."`
- **Vector DB 결과**:
  - "엑셀을 밟아 시속 60" -> `VehicleSpeed = 60` 매핑 (정확도 95%)
  - "에어컨을 튼다" -> `HVAC_Power = ON` 매핑 (정확도 92%)
- **핵심 포인트**: 표준 변수명을 몰라도 일상어로 스크립트를 생성함.

### 🍅 시나리오 2: 은어/신조어 처리 (Ambiguity Resolution)
- **사용자 입력**: `"우측 깜빡이 비상등 켜고 풀악셀 친다."`
- **Vector DB 결과**:
  - "풀악셀 친다" -> `VehicleSpeed = MAX` (가장 유사한 속도 관련 시그널로 맵핑)
  - "깜빡이 비상등" -> `TurnSignal_Status = RIGHT` 매핑
- **핵심 포인트**: 사전에 정확히 매핑되지 않은 슬랭(Slang)도 임베딩 유사도를 통해 가장 근접한 시그널을 찾아냄.

### 🍅 시나리오 3: 온톨로지 제약 조건 방어 (Pre-condition Check)
- **사용자 입력 (Step 1)**: `"차량에 탑승한다."`
- **사용자 입력 (Step 2)**: `"바로 기어를 D로 바꾸고 주행한다."`
- **Ontology 검증 결과**:
  - `VehicleSpeed` 조작 전 `Ignition_Status == ON` 룰 위반 발견. (시동을 안 켬)
- **LLM의 자동 보정 (코드 생성)**:
  - LLM이 코드를 생성할 때, 주행(D단) 변경 직전에 `simva.set_signal("Ignition_Status", "ON")`을 **스스로 추가**하거나,
  - 코드 상단에 `# WARNING: 시동(Ignition) 켜기 스텝이 누락되어 자동 추가됨` 이라는 주석을 달아줌.
- **핵심 포인트**: 단순 번역기가 아닌 도메인 오라클(Oracle) 역할을 수행함.

### 🍅 시나리오 4: 상호 배타적/위험 로직 경고 (Conflict Detection)
- **사용자 입력 (Step 1)**: `"기어를 P로 놓는다."`
- **사용자 입력 (Step 2)**: `"크루즈 컨트롤(CC)을 켠다."`
- **Ontology 검증 결과**:
  - `CruiseControl_State` == `ON` 의 선행 조건(`VehicleSpeed >= 30` 및 주행 상태) 위반.
- **LLM의 방어 로직**:
  - 해당 스텝에 대해 코드를 생성하지 않고 `UNKNOWN/ERROR` IR로 분류.
  - 리포트 출력: `# ERROR: 주차(P) 상태에서는 크루즈 컨트롤을 활성화할 수 없습니다.`
- **핵심 포인트**: 잘못 작성된 TC(휴먼 에러)를 시스템이 사전에 차단함.

---

## 3. 구현 단계에서의 적용 계획

위 데이터들은 구현(Phase 2) 단계가 시작되면 다음과 같이 적용될 예정입니다.

1. **JSON 파일 생성**: `rag_mock_signals.json` 및 `rag_mock_rules.json` 파일 생성.
2. **벡터화 스크립트 작성**: 위 JSON의 `text` 배열을 순회하며 `sentence-transformers`를 이용해 임베딩을 추출하고 로컬 ChromaDB에 덤프하는 파이썬 스크립트(`init_db.py`) 작성.
3. **데모 UI 구성**: Streamlit UI 좌측 사이드바에 **"시나리오 1,2,3,4 자동 입력 버튼"**을 만들어 클릭 한 번으로 테스트가 실행되도록 구성.

# Vector DB 및 Ontology (Knowledge Graph) 설계 안

본 문서는 테스트 스크립트 생성기가 복잡하고 모호한 자연어를 파악하고 도메인 논리 오류를 검증하기 위해 도입할 **Vector DB**와 **Ontology**의 샘플 설계 및 구현 방향을 정의합니다. 학습 및 프로토타입 검증용 데이터도 함께 제공합니다.

---

## 1. Vector DB (의미론적 검색 레이어)

Vector DB의 핵심 목적은 **“사용자가 입력한 다양한 동의어 및 비표준어”**를 **“시스템이 이해하는 표준 논리 시그널(Logical Signal)”**로 매핑하는 것입니다. 1:1 Key-Value 매핑의 한계를 극복하고, LLM의 임베딩 모델(예: `text-embedding-3-small`, `all-MiniLM-L6-v2`)을 활용하여 의미적 유사도를 판단합니다.

### 1.1. 설계 스키마 (Document Structure)

Vector DB(예: ChromaDB, Pinecone)에 저장할 문서는 메타데이터와 고유 ID, 그리고 임베딩 텍스트로 구성됩니다.

| 필드 | 설명 | 예시 |
| :--- | :--- | :--- |
| `id` | 고유 식별자 | `signal_vehicle_speed` |
| `text` (임베딩 대상) | 실제 벡터 공간에 매핑될 텍스트 뭉치 (동의어, 설명) | `속도, 차속, 엑셀, 가속, speed, km/h, 감속` |
| `metadata.logical_name` | **(Output)** Core Engine이 인식할 논리적 시그널 명칭 | `VehicleSpeed` |
| `metadata.description` | (옵션) LLM에게 프롬프트로 제공할 해당 시그널의 설명 | `차량의 현재 주행 속도를 나타내는 시그널` |
| `metadata.data_type` | (옵션) 제어 가능한 값의 타입 | `float`, `enum(ON, OFF)` |

### 1.2. 초기 샘플 데이터 (Mock Data)

테스트 목적으로 Vector DB에 주입(Ingest)할 샘플 JSON 데이터입니다. (실제로는 이 텍스트들을 임베딩 모델을 통해 벡터화하여 저장합니다.)

```json
[
  {
    "id": "sig_001",
    "text": "속도, 차속, 엑셀, 가속, 감속, 브레이크 밟기, 시속, km/h, speed, velocity",
    "metadata": {
      "logical_name": "VehicleSpeed",
      "data_type": "float",
      "unit": "km/h",
      "description": "차량의 주행 속도 제어"
    }
  },
  {
    "id": "sig_002",
    "text": "엔진, 시동, 발동기, 켜다, 끄다, ignition, engine, start, stop, IGN",
    "metadata": {
      "logical_name": "Ignition_Status",
      "data_type": "enum",
      "allowed_values": ["ON", "OFF"],
      "description": "차량 엔진 시동 상태 제어"
    }
  },
  {
    "id": "sig_003",
    "text": "전조등, 헤드램프, 앞불, 라이트, 상향등, 하향등, headlamp, light, illumination",
    "metadata": {
      "logical_name": "HeadLamp_State",
      "data_type": "enum",
      "allowed_values": ["OFF", "LOW", "HIGH"],
      "description": "차량 전조등 조명 제어"
    }
  }
]
```

### 1.3. 작동 프로세스 (검색 시나리오)
1. **사용자 TC**: `"TC-01: 엑셀을 강하게 밟아서 100까지 올린다."`
2. **Core Engine 추출**: 키워드 `"엑셀을 강하게 밟아서"` 추출.
3. **Vector DB 쿼리**: 해당 문장을 임베딩하여 Vector DB 검색.
4. **결과 리턴**: 유사도가 가장 높은 문서 `sig_001` 매칭 됨. -> 논리적 시그널 `VehicleSpeed` 반환.

---

## 2. Ontology / Knowledge Graph (지식 추론 레이어)

Ontology의 목적은 **"시그널 간의 인과관계 및 선행 조건(Pre-condition)"**을 정의하여, LLM이 코드를 생성하기 전에 논리적 결함을 스스로 찾아내고 보완(또는 사용자에게 경고)할 수 있게 하는 것입니다.

### 2.1. 설계 스키마 (Graph Structure)

지식 그래프(예: Neo4j)는 노드(Entity)와 엣지(Relationship)로 구성됩니다. 가벼운 로컬 테스트를 위해서는 JSON 기반의 방향성 그래프(Directed Graph)로 모델링할 수 있습니다.

- **Nodes (엔티티)**: `Signal`, `State`, `Component` 등.
- **Edges (관계)**: `REQUIRES` (선행 조건), `AFFECTS` (영향을 줌), `CONFLICTS_WITH` (상호 배타적) 등.

### 2.2. 초기 샘플 데이터 (Mock Knowledge Graph)

JSON 형식으로 정의한 간이 온톨로지 샘플입니다.

```json
{
  "nodes": [
    { "id": "Ignition_Status", "type": "Signal" },
    { "id": "VehicleSpeed", "type": "Signal" },
    { "id": "HeadLamp_State", "type": "Signal" },
    { "id": "Battery_Voltage", "type": "Signal" }
  ],
  "relationships": [
    {
      "source": "VehicleSpeed",
      "relation": "REQUIRES",
      "target": "Ignition_Status",
      "condition": "== ON",
      "description": "차량 속도를 제어하려면 반드시 엔진 시동이 켜져 있어야 합니다."
    },
    {
      "source": "Ignition_Status",
      "relation": "REQUIRES",
      "target": "Battery_Voltage",
      "condition": ">= 12.0",
      "description": "시동을 걸려면 배터리 전압이 12V 이상이어야 합니다."
    },
    {
      "source": "HeadLamp_State",
      "relation": "AFFECTS",
      "target": "Battery_Voltage",
      "effect": "DECREASE",
      "description": "전조등을 켜면 배터리 전압이 미세하게 떨어집니다."
    }
  ]
}
```

### 2.3. 작동 프로세스 (검색 시나리오)
1. **진행 상황**: LLM이 앞서 파악된 `VehicleSpeed`를 `100`으로 세팅하는 IR 생성을 준비 중.
2. **Ontology 쿼리**: `Core Engine`이 `VehicleSpeed`에 대한 제약 조건이 있는지 Ontology 검색.
3. **결과 반환**: `REQUIRES Ignition_Status == ON` 관계 발견.
4. **선행 조건 검증**: 현재 TC의 이전 Step들(Context)을 분석하여 `Ignition_Status`가 켜져 있는지 확인.
    - **Case A (성공)**: 이전 스텝에 "시동을 켠다"가 있었다면 통과.
    - **Case B (실패/보완)**: 이전 스텝이 없었다면, LLM에게 프롬프트 주입.
      `[Validation Alert] Target signal is VehicleSpeed, but pre-condition 'Ignition_Status == ON' is not found in previous steps. Please generate a warning comment or add setup logic.`

---

## 3. 통합 (Hybrid RAG) 아키텍처 예시

실제 코더(Agent)가 프롬프트를 만들 때 이 두 DB가 어떻게 합쳐지는지 보여주는 템플릿입니다.

```text
[System]
당신은 자동차 테스트 스크립트(IR) 생성기입니다. 
아래의 사용자 문장을 분석하여 올바른 JSON IR을 생성하세요.

[User Input (Step 2)]
"엑셀을 밟아 100을 맞춘다."

[Vector DB Search Result]
- Keyword "엑셀" matched with Logical Signal: "VehicleSpeed" (Similarity: 0.95)
- Data Type: float

[Ontology Validation Result for "VehicleSpeed"]
- WARNING: "VehicleSpeed" requires "Ignition_Status == ON". 
- Context Check: Previous step (Step 1) does NOT contain Ignition ON.

[Instruction]
선행 조건이 누락되었습니다. 생성할 IR 타입에 "UNKNOWN" 또는 "WARN"을 세팅하고, 주석(Comment)에 에러 사유를 적어주세요.
```

---

## 4. 데이터베이스 라이프사이클 및 관리 방안

시스템 운영 중에 Vector DB와 Ontology가 **언제 생성되고(Creation), 언제 데이터가 추가되며(Insertion/Update), 어떻게 로드되는지(Loading)**에 대한 전체적인 생명주기(Lifecycle) 아키텍처입니다.

### 4.1. 저장소 구성 (Storage Architecture)
데이터 영속성을 위해 시스템은 로컬 파일 기반의 경량 DB를 사용합니다.
- **Vector DB**: `ChromaDB` (로컬 디스크 모드) -> `data/vector_db/` 디렉토리에 저장.
- **Ontology**: `JSON` 또는 `Neo4j(Local)` -> 초기에는 `data/ontology/graph_rules.json` 파일로 관리.

### 4.2. 라이프사이클 단계별 동작

#### [단계 1] 시스템 최초 초기화 (Initialization / Bootstrap)
- **언제**: 솔루션을 처음 설치하거나 처음 구동할 때. (또는 관리자가 `Initialize DB` 버튼을 누를 때)
- **동작**:
    1. 시스템 내부에 내장된(Built-in) **기본 도메인 지식 JSON 파일**(위 1.2, 2.2의 Mock Data 형태)을 읽어 들입니다.
    2. JSON의 `text` 필드 값들을 LLM(또는 로컬 임베딩 모델, 예: `all-MiniLM-L6-v2`)을 통해 **벡터 배열(Embeddings)로 변환**합니다. (최초 1회만 임베딩 API 비용/시간 소요)
    3. 변환된 벡터와 메타데이터를 `data/vector_db/` 경로에 ChromaDB 컬렉션으로 물리적으로 생성 및 저장(`Insert`)합니다.
    4. Ontology 룰은 `data/ontology/graph_rules.json`에 초기 세팅으로 복사됩니다.

#### [단계 2] 런타임 조회 (Runtime Retrieval / Query)
- **언제**: 사용자가 TC 엑셀 파일을 업로드하고 **"변환(Generate)"**을 실행하여 Core Engine이 동작하는 중.
- **동작**:
    1. Core Engine은 기동 시 `data/vector_db/`에 이미 만들어진 ChromaDB 인스턴스를 메모리에 **로드(Load)**만 합니다. (임베딩 재생성 없음)
    2. TC 한 줄을 파싱할 때마다 질문 텍스트("엑셀 강하게 밟아")만 실시간으로 임베딩하여 Vector DB에 `Query`를 날리고 매칭 논리 시그널을 가져옵니다.
    3. 메모리에 로드된 Ontology 객체를 탐색하여 선행 조건(`REQUIRES`)이 위반되지 않았는지 검사합니다.

#### [단계 3] 동적 학습 및 데이터 추가 (Continuous Learning / Update)
- **언제**:
    - [자동] 사용자가 UI에서 특정 번역 결과를 "수정"하거나 "피드백"을 줄 때.
    - [수동] 도메인 전문가가 UI 내의 **"지식 사전 관리 (Knowledge Manager)"** 메뉴에서 새로운 시그널 용어나 제약 조건을 추가할 때.
- **동작**:
    - **Vector DB 추가 반영**:
        1. "초고속 주행" 이라는 신규 용어를 `VehicleSpeed`에 맵핑해달라는 요청 수신.
        2. "초고속 주행" 문자열만 새로 임베딩 모델을 돌려 벡터 값을 추출합니다.
        3. 기존 ChromaDB의 `VehicleSpeed` Document(id: `sig_001`)를 찾아 `text` 리스트에 합치거나(`Update`), 혹은 유사어 전용 아이템으로 새로 `Insert` 합니다.
        4. 즉, **런타임 동작을 멈추지 않고 실시간으로 지식을 확장**할 수 있습니다.
    - **Ontology 추가 반영**:
        1. UI를 통해 "속도 제어 기어는 D 상태여야 한다"는 룰이 수동 입력됨.
        2. `data/ontology/graph_rules.json` 파일 내부의 `relationships` 배열에 새 JSON 블록 단위로 내용이 `Append(추가)` 됩니다.
        3. 다음 번 TC 변환 작업부터 새로 추가된 룰이 적용되어 오류를 더 잘 걸러냅니다.

### 4.3. 결론
- **생성 시기**: 제품 초기 셋팅 시 "1회 대량 변환 및 생성 (Initialization)"
- **추가/수정 시기**: 운영 중 관리자 화면 도구나 사용자 피드백을 통한 실시간 "Append & Update"
- **조회 효율성**: 변환 작업(런타임) 중에는 이미 만들어진 DB를 읽기만(Read-only Query) 하므로 매우 빠릅니다.

# Ontology DB 스키마 및 자동화 설계서

## 1. 개요 및 역할 (차종별 단어장/번역가 담당)
차세대 아키텍처에서 **Ontology DB**는 "세부 단어와 신호를 채워 넣는 번역가" 역할을 수행합니다. 특정 타겟 코드 언어(SIMVA, CAPL)에 종속되지 않는 범용 **차량 도메인 지식 그래프(Knowledge Graph)**입니다.

*   **역할**: Vector DB가 추출해 준 자연어 단어(`{signal}="속도"`)를, 현재 실행 중인 대상 차종이 알아들을 수 있는 **실제 물리적 식별자(ECU 및 Signal)**로 완벽하게 번역합니다.
*   **차종 파편화 극복**: 근본적인 목적은 같으나 차종(Variant)마다 다르게 흩어져 있는 신호명(`VehicleSpeed_A`, `VehSpd_B` 등)들을 논리적 개념(Logical Concept) 하나로 통일하여 라우팅함으로써, 수만 개의 스크립트를 재사용할 수 있게 만듭니다.

---

## 2. Ontology DB 스키마 설계 (단일 지식 그래프)
Ontology DB는 데이터 파편화를 막고 엔티티 간의 '관계(Relationship)'를 명시적으로 볼 수 있도록, 모든 요소가 단일 파일 내에 플랫(Flat)한 노드 형태로 존재하는 **지식 그래프(Knowledge Graph)** 스키마를 택합니다.

### 2.1 노드(Node) 타입 정의
1.  **`LogicalConcept`**: 자연어 동의어(`synonyms`)를 가지고 있는 추상화된 논리 개념입니다.
2.  **`PhysicalSignal`**: 실제 소스코드에 삽입되어야 하는 최종 식별자입니다. 제어기 정보(`ecu`)와 더불어, 스펙상의 값(Value)과 사용자의 다양한 표현을 매칭하기 위한 **`value_definitions` (별칭 리스트 포함)**를 가집니다.
3.  **`VehicleModel`**: 변형(Variant) 정보입니다. 이 컨텍스트 값에 따라 `LogicalConcept`이 뻗어나가는 엣지가 달라집니다.

### 2.2 샘플 데이터 (`sample_ontology_graph.json`)
아래는 **차종 파편화**(Variant A vs B)와 **자연어 별칭**(Aliases)이 복합적으로 적용된 실제 지식 그래프 예시입니다.

```json
{
  "Concept:VehicleSpeed": {
    "type": "LogicalConcept",
    "synonyms": ["차량 속도", "속도", "차속", "Speed"],
    "relationships": {
      "implemented_by": [
        { "target_node": "Physical:CGW_VehSpd", "context_variant": "Variant:Car_Alpha" },
        { "target_node": "Physical:ADCU_V_Speed", "context_variant": "Variant:Car_Beta" }
      ]
    }
  },
  "Concept:GearStatus": {
    "type": "LogicalConcept",
    "synonyms": ["기어 단수", "기어 상태", "변속 위치", "Gear"],
    "relationships": {
      "implemented_by": [
        { "target_node": "Physical:E_Shifter_Stat", "context_variant": "Variant:Car_Alpha" },
        { "target_node": "Physical:BCM_Gear_Pos", "context_variant": "Variant:Car_Beta" }
      ]
    }
  },
  "Physical:CGW_VehSpd": {
    "type": "PhysicalSignal",
    "ecu": "CGW",
    "signal_id": "VehSpd",
    "datatype": "uint8",
    "value_definitions": [] 
  },
  "Physical:E_Shifter_Stat": {
    "type": "PhysicalSignal",
    "ecu": "E_Shifter",
    "signal_id": "GearStat",
    "datatype": "uint8",
    "value_definitions": [
      { "value": 0, "spec_name": "P", "aliases": ["주차", "P단", "Parking"] },
      { "value": 1, "spec_name": "R", "aliases": ["후진", "R단", "Reverse"] },
      { "value": 2, "spec_name": "N", "aliases": ["중립", "N단", "Neutral"] },
      { "value": 3, "spec_name": "D", "aliases": ["주행", "D단", "Drive"] }
    ]
  },
  "Physical:BCM_Gear_Pos": {
    "type": "PhysicalSignal",
    "ecu": "BCM",
    "signal_id": "CurGear",
    "datatype": "uint8",
    "value_definitions": [
      { "value": 1, "spec_name": "PARK", "aliases": ["주차", "P단"] },
      { "value": 2, "spec_name": "REV", "aliases": ["후진", "R단"] },
      { "value": 3, "spec_name": "NEU", "aliases": ["중립", "N단"] },
      { "value": 4, "spec_name": "DRIVE", "aliases": ["주행", "D단"] }
    ]
  },
  "Variant:Car_Alpha": { "type": "VehicleModel", "description": "내연기관 세단 플랫폼" },
  "Variant:Car_Beta": { "type": "VehicleModel", "description": "전기차 SUV 플랫폼" }
}
```

---

## 3. 온톨로지 DB 자동 구축 파이프라인 (Auto-Ingestion Pipeline)
수만 개에 달하는 통신 신호 스펙을 인간이 JSON에 수타로 입력하는 것은 불가능하며 관리 지옥을 발생시킵니다. 이를 근절하기 위해 **"원본 스펙 연동 100% 자동화 파이프라인(Zero-Maintenance)"**을 도출했습니다.

### 3.1 원본 스펙 자동 파싱 (Data Ingestion)
현업에서 이미 "해당 차종의 통신 스펙 교과서"로 취급받는 파일을 빌드 스크립트에 던져 파싱합니다.
- **DBC / ARXML 파일**: `cantools`, `autosar` 등의 라이브러리로 대상 차종의 전체 ECU 파티션과 내부 통신 Signal들을 1초 만에 Array로 긁어냅니다.
- **기존 레거시 코드**: 이미 C# 등으로 구현된 `Check_Output_Signal.cs` 가 있다면, 정규식이나 AST로 이를 긁어 신호 매핑 데이터를 가져옵니다.

### 3.2 지식 그래프(Knowledge Graph) 자동 병합 (Merge)
추출된 대량의 "제어기(ECU) + 물리 신호(Signal_ID)" 정보는 새로운 차종(Variant) 컨텍스트와 함께 `ontology_graph.json`에 자동으로 병합됩니다.

1. 빌드 툴 실행 시 타겟 차종(예: `CarModel_C`)을 파라미터로 지정합니다.
2. 긁어온 수천 개의 시그널들을 전부 **`PhysicalSignal` 노드**로 덮어쓰기/생성 합니다.
3. 파싱된 신호 명칭(예: "V_Speed_Main")을 보고, 규칙(Rule-base)이나 자연어 처리(NLP)를 적용하여 사전에 존재하는 **`LogicalConcept` 노드** (`Concept:VehicleSpeed`)들을 자동으로 찾아내어 그 사이에 `implemented_by` 엣지 연결선 구조를 자동으로 JSON에 생성합니다.
4. 매핑되지 않은 잔여자들은 미분류(Unclassified) 노드로 모아두고 담당자가 UI 화면에서 한 번씩 확인 후 저장(Approve)하도록 처리합니다.

---

## 4. 통합 변환 데이터 플로우 (With Normalization)
사용자가 `"속도를 켜짐으로 설정"` (차종: `CarModel_A`)이라는 스크립트를 요청했을 때의 파이프라인입니다.

1.  **[Step 1: Vector DB]** 템플릿 정규식을 통해 변수와 값을 분리합니다. ➔ `{signal}: "속도"`, `{value}: "켜짐"`
2.  **[Step 2: Ontology Search]** "속도" ➔ `Concept:VehicleSpeed` ➔ `Physical:CGW_VehicleSpeed` 로 시그널 식별자를 결정합니다.
3.  **[Step 3: Value Normalization]** `Physical:CGW_VehicleSpeed` 노드 내부의 `value_definitions`를 뒤져 `"켜짐"` 이 `value: 1` 의 별칭임을 찾아냅니다. ➔ `{normalized_value}: 1`
4.  **[Step 4: Final Assembly]** 시그널 식별자(`CGW.VehicleSpeed`)와 정규화된 값(`1`)을 뼈대 코드에 꽂아 최종 스크립트를 완성합니다. ➔ `simva.set_signal(signals.CGW.VehicleSpeed, 1)`

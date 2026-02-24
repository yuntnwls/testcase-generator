# TC 컴포넌트 심층 분석 및 전체 스크립트 작성 전략

본 지능형 자동화 시스템은 **TC의 4대 핵심 컴포넌트(초기화, 사전 조건, 시험 방법, 판정 조건)**를 모두 스크립트로 합성(Synthesis)하여 단일 구조체(함수)로 완성하는 것을 목표로 합니다.

---

## 1. TC 4대 컴포넌트 역할 및 변환 스펙

### 1-1. 초기화 (Initialization)
*   **목적**: 테스트 환경을 백지상태(정상 상태)로 맞추거나 특정 ECU를 리셋하는 과정입니다.
*   **자연어 예시**: `"전체 시스템 리셋"`, `"BDC 제어기를 리셋한다"`, `"차량 전원을 OFF로 초기화한다"`
*   **Vector DB (템플릿)**:
    - **전체 리셋**: `simva.reset_ecu()` (파라미터 없음)
    - **특정 ECU 리셋**: `simva.reset_ecu("BDC")` (ECU 명칭을 문자열로 전달)
*   **코드 컨텍스트**: 스크립트의 가장 첫 줄에 위치하며, 환경을 초기화하고 안정화하기 위한 `simva.wait()`가 암묵적으로 수반되어야 합니다.

### 1-2. 시험 전 조건 (Pre-condition)
*   **목적**: 스크립트를 본격적으로 실행하기 전, 테스트 인프라나 차량 상태가 요구 조건을 충족하는지 검사합니다.
*   **자연어 예시**: `"기어 단수가 P단이어야 한다"`, `"배터리 전압이 12V 이상이어야 한다"`
*   **Vector DB (템플릿)**: `simva.is_eq()`, `simva.is_ge()` 등 상태 검증 확인 API로 매핑됩니다.
*   **코드 컨텍스트**: 여기서 False가 반환되면 본 테스트(시험 방법)를 시작하기도 전에 **TC Blocked(또는 스킵/실패)** 처리하고 종료(Early Return)해야 합니다.

### 1-3. 시험 방법 (Test Method / Step)
*   **목적**: 검증하기 위한 실제 액션을 수행합니다. (가장 복합적)
*   **자연어 예시**: `"도어를 잠근다"`, `"와이퍼를 3단으로 설정하고 5초 대기한다"`
*   **Vector DB (템플릿)**: 제어문(if, for) 및 `simva.set_signal()`, `simva.wait()` 등으로 매핑됩니다.

### 1-4. 판정 조건 (Pass/Fail Judgment)
*   **목적**: 수행된 테스트 방법에 대해 기대하는 결과가 도출되었는지 검사하여 실질적인 TC의 성공(Pass) / 실패(Fail)를 반환합니다.
*   **자연어 예시**: `"기어 단수가 P단이어야 한다 (단순 상태)"`, `"비상등이 5초 동안 점멸(pulsing)해야 한다"`, `"속도가 계속 유지(keep) 되어야 한다"`
*   **Vector DB (템플릿)**: 목적에 맞춰 SIMVA의 고급 판정 API (`is_...`, `turn_...`, `keep_...`, `pulsing` 등)로 정밀하게 매핑되어야 합니다.

---

## 2. 생성될 스크립트 타겟 아키텍처 (Python 구조체)

위 4가지 컬럼을 파싱하여, 최종적으로 템플릿 엔진이 아래와 같은 구조의 견고한 파이썬 스크립트로 병합해냅니다.

```python
def test_TC_ID_001_Example(simva, signals, profiles):
    """
    [TC Objective]: 비상등 점멸 테스트
    """
    
    # -----------------------------------------------------
    # 1. 초기화 (Initialization)
    # -----------------------------------------------------
    simva.reset_ecu("BDC")       # 예: "BDC 리셋"
    simva.wait(2.0)                     # (안정화 대기 암묵 추가 가능)

    # -----------------------------------------------------
    # 2. 시험 전 조건 (Pre-condition) 방어 로직
    # -----------------------------------------------------
    # 예: "차량 속도가 0이어야 한다"
    precond_ok = simva.is_eq(signals.CGW.VehicleSpeed, 0)
    if not precond_ok:
        print("[BLOCKED] 시험 전 조건 불만족: 속도가 0이 아님")
        return "BLOCKED"

    # -----------------------------------------------------
    # 3. 시험 방법 (Test Steps)
    # -----------------------------------------------------
    # 예: "비상등 스위치를 ON으로 설정하고 10초 대기한다"
    simva.set_signal(signals.BDC.HazardSwitch, 1)
    simva.wait(10.0)

    # 예: "3번 반복하며 윈도우를 열고 닫는다" (Loop Case)
    for i in range(3):
        simva.set_signal(signals.BCM.WindowPos, 100) # 열기
        simva.wait(1.0)
        simva.set_signal(signals.BCM.WindowPos, 0)   # 닫기
        simva.wait(1.0)

    # -----------------------------------------------------
    # 4. 판정 조건 (Pass/Fail Judgment)
    # -----------------------------------------------------
    # 예: "비상등 램프가 10초 동안 1초 주기로 점멸(pulsing)해야 한다"
    # simva API: pulsing(key, pulsing_value, pulsing_duration_sec, tolerance)
    result = simva.pulsing(signals.BDC.HazardLamp, 1, 10.0, 0.5)

    if result:
        print("[PASS] TC_ID_001")
        return "PASS"
    else:
        print("[FAIL] TC_ID_001: 비상등 점멸 판정 실패")
        return "FAIL"
```

---

## 3. 컬럼별 Vector DB 라우팅 전략 (Metadata Filtering)

사용자께서 말씀하신 **"Vector DB 검색 필터(`type`)가 Vector DB 스키마 단에 있는 그 type이랑 같은건가요?"**에 대한 대답은 **"네, 정확히 같습니다!"** 입니다. 

Vector DB 설계서(`db/vector_db_schema.md`)를 보면 템플릿마다 `"type": "ACTION"`, `"type": "META_CONTROL_IFELSE"` 같은 속성값이 적혀있습니다. 스크립트 작성 엔진(Generator)은 엑셀을 파싱할 때 이 **`type` 값을 메타데이터 쿼리 필터(Metadata Query Filter)**로 사용하여 검색 범위를 지정합니다.

**[코드 레벨 예시]**
```python
# 엑셀의 [시험 방법] 컬럼을 읽을 때 동작하는 백엔드 검색 코드
results = vector_db.search(
    query_text="속도를 0으로 해라",
    n_results=1,
    where={"type": {"$in": ["TYPE_ACTION", "TYPE_CONTROL"]}} # <--- 바로 이 부분!
)
```

자연어 임베딩(Vector) 방식의 가장 치명적인 문제점은, **"속도를 0으로 설정한다"** (동작)와 **"속도가 0인지 확인한다"** (판정)라는 두 문장이 AI 모델에게는 의미적으로 매우 비슷하게 보인다는 점입니다. (유사도가 매우 높게 나와 오작동의 원인이 됩니다.)

이를 완벽하게 방지하기 위해 생성 시스템(Generator)은 엑셀을 읽을 때 텍스트만 덜렁 Vector DB에 던지는 것이 아니라, **"지금 엑셀의 어떤 컬럼(초기화/검사/방법/판정)을 읽고 있는지"를 메타카테고리(Metadata Filter)인 `type` 필드로 함께 전달**하여 검색 범위를 강제로 좁힙니다. 

즉, "판정 조건" 컬럼을 파싱할 때는 Vector DB에서 "검사/판정용 템플릿(`TYPE_JUDGMENT_*`)"들 사이에서만 유사도를 찾도록 **안전 락(Lock)**을 거는 것입니다.

| 엑셀 입력 컬럼 | Vector DB 검색 필터 (`type`) | 타겟 코드 뼈대 예시 | 역할 설명 |
| :--- | :--- | :--- | :--- |
| **초기화** | `TYPE_INIT` / `TYPE_ACTION` | `simva.reset_ecu()`<br/>`simva.set_signal()` | "환경 리셋" 카테고리 내에서만 템플릿 검색 |
| **시험전조건**| `TYPE_PRECONDITION_IS` | `simva.is_eq()`<br/>`simva.is_ge()` | "단발성 상태 확인" 카테고리 내에서만 템플릿 검색 |
| **시험방법** | `TYPE_ACTION`<br/>`TYPE_CONTROL_IF`<br/>`TYPE_CONTROL_LOOP` | `simva.set_signal()`<br/>`if ...: ...`<br/>`for i in range(...): ...` | "값 설정 및 루프/조건 제어" 카테고리 검색 |
| **판정조건** | `TYPE_JUDGMENT_IS`<br/>`TYPE_JUDGMENT_KEEP`<br/>`TYPE_JUDGMENT_TURN`<br/>`TYPE_JUDGMENT_PULSING` | `simva.is_eq()`<br/>`simva.keep_eq()`<br/>`simva.turn_eq()`<br/>`simva.pulsing()` | "최종 합격/불합격 판정" 카테고리 내에서만 템플릿 검색 |

### 3.1. 패턴 해석의 중의성 해결 (Context Matters)
"속도가 0" 이라는 짧은 텍스트가 엑셀에 적혀있을 때, 컬럼 헤더(필터)에 따라 다음과 같이 전혀 다른 코드로 완벽하게 번역됩니다.

*   **[초기화] / [시험 방법] 컬럼**에 "속도 0"이 적혀있음 (액션 검색):
    -> 추출 결과: **`simva.set_signal(signals.CGW.VehSpd, 0)`**
*   **[시험 전 조건]** 컬럼에 "속도 0"이 적혀있음 (단발성 필수 검사 검색):
    -> 추출 결과: **`simva.is_eq(signals.CGW.VehSpd, 0)`**
*   **[판정 조건]** 컬럼에 "속도 0 유지"가 적혀있음 (지속성 판정 검색):
    -> 추출 결과: **`simva.keep_eq(signals.CGW.VehSpd, 0, 5.0)`**

따라서 스크립트 작성 엔진은 텍스트의 유사성만 믿고 아무 함수나 뽑는 것이 아니라, **[현재 읽고 있는 엑셀 컬럼 위치] x [Vector DB의 메타-카테고리]의 교차 검증**을 통해 100% 안전하고 의도된 코드를 생성하게 됩니다.

---

## 4. Data & Value Normalization (값 정규화 파이프라인)

Vector DB 필터링을 거쳐 템플릿 스켈레톤을 구성하고 시그널 맵핑을 하더라도 남아있는 치명적인 문제가 있습니다. 바로 사용자가 엑셀에 자유롭게 치는 **"값(Value) 표현의 다형성"**입니다. 

똑같은 켜짐(1) 상태를 두고 사용자들은 `"와이퍼를 켜짐으로 설정"`, `"와이퍼 ON"`, `"와이퍼 1단계"` 등으로 제각각 작성합니다. 이를 해결하고 타겟 코드가 요구하는 단 하나의 정형화된 데이터 타입(예: `simva.set_signal(..., 1)`)으로 치환하는 3단계 정규화 파이프라인입니다.

### 4.1. [Step 1] Vector DB: 원시 값(Raw Value) 추출
Vector DB는 텍스트에서 '변수'의 위치만 도려내는 역할을 합니다.
*   **Vector DB 매칭 템플릿**: `"{signal}을 {value}로 설정한다"`
*   **추출 결과**: `signal`="운전석 윈도우", `value`="완전 개방" (원시 문자열)

### 4.2. [Step 2] Ontology DB: 지식 기반 매핑 (Value Mapping & Aliasing)

사용자께서 지적하신 **"DBC 스펙 문서와 실제 테스터의 표현이 다를 때의 처리"**가 이 단계의 핵심입니다. Ontology DB는 단순히 DBC를 복사한 것이 아니라, **"스펙 값"과 "현장 별칭"을 연결하는 지식 그래프** 역할을 합니다.

#### 매칭 우선순위 (Resolution Priority)
1.  **Level 1: Official Spec Match (DBC/ARXML)**
    *   DBC에 정의된 `0: "OFF", 1: "ON"` 과 정확히 일치하는지 확인합니다.
2.  **Level 2: Synonym/Alias Match (Ontology Knowledge)**
    *   Ontology DB에 미리 등록된 별칭들을 확인합니다. (예: `1`의 별칭으로 `["켜짐", "작동", "활성화", "액티브"]` 등록)
3.  **Level 3: LLM Semantic Match (On-the-fly Fallback)**
    *   위의 사전(Dictionary)에 없을 경우, LLM에게 해당 시그널의 모든 가능한 스펙 값 리스트(`[0: OFF, 1: ON, 2: ERROR]`)를 던져주고, 사용자가 쓴 단어(예: `"불 들어옴"`)가 어느 값에 가장 가까운지 **의미적 유사도(Semantic Similarity)**로 판정하게 합니다.

**[Ontology DB 구조 - 확장된 value_map 예시]**
```json
{
  "name": "WiperStatus_BCM",
  "datatype": "uint8",
  "value_definitions": [
    { "value": 0, "spec_name": "OFF", "aliases": ["꺼짐", "중단", "비활성"] },
    { "value": 1, "spec_name": "LOW", "aliases": ["켜짐", "작동", "1단", "저속"] },
    { "value": 2, "spec_name": "HIGH", "aliases": ["고속", "2단", "빨리"] }
  ]
}
```

### 4.3. [Step 3] Type Enforcement (강제 캐스팅)
물리 시그널의 스펙 구조에 명시된 `datatype`을 기반으로 Python 문법에 맞게 최종 캐스팅(Casting)하여 100% Type Safe한 코드로 탈바꿈시킵니다.
*   `datatype`이 `uint8` -> `int(1)` -> 타겟 코드: `1`
*   `datatype`이 `float32` -> `float(1)` -> 타겟 코드: `1.0`
*   `datatype`이 `boolean` -> `bool(1)` -> 타겟 코드: `True`

> [!TIP]
> **자가 학습 피드백 루프 (Learning Loop)**
> LLM이 Level 3에서 성공적으로 매핑한 새로운 단어(예: `"불 들어옴" ➔ 1`)는 관리자의 승인을 거쳐 Ontology DB의 `aliases` 리스트에 자동으로 영구 추가됩니다. 이를 통해 시간이 지날수록 시스템은 LLM 호출 없이도 현장의 모든 은어를 알아듣는 **"베테랑 엔지니어"**의 지식을 갖추게 됩니다.

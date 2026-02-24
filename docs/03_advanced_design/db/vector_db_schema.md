# Vector DB 스키마 및 자동화 설계서

## 1. 개요 및 역할 (문맥 & 뼈대 담당)
차세대 아키텍처에서 **Vector DB**는 "문법과 뼈대를 담당하는 건축가" 역할을 수행합니다.

*   **역할**: "이 자연어 문장이 어떤 함수(템플릿) 구조를 가져야 하는가?"를 판별합니다.
*   **동작 로직**: `"{A}를 {B}로 바꾼다"`라는 사용자 문장이 들어오면, Vector DB에서 유사도 검색을 통해 `"아! 이건 할당 액션이군! set_signal() 템플릿을 꺼내야 해"`라고 문맥(뼈대)을 특정합니다.
*   **결과 도출**: 매칭된 정규식을 통해 빈칸에 들어갈 단어(`{signal}="속도"`, `{value}="LOW"`)를 추출하고, 최종 조립될 코드 뼈대(`simva.set_signal(...)`)를 Ontology 엔진 측으로 넘겨줍니다.

---

## 2. Vector DB 스키마 구조
Vector DB는 각 타겟 플랫폼(예: SIMVA, CAPL)마다 독립된 컬렉션(Collection)으로 관리되며, JSON 포맷을 기반으로 동작합니다.

### 2.1 스키마 구성 요소
| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| `id` | String | 템플릿의 고유 식별자 (예: `action_set_signal`, `meta_condition_ifelse`) |
| `type` | Enum | 이 뼈대의 논리적 성격 (`ACTION`, `META_CONTROL_IF`, `META_CONTROL_LOOP`, `EXPRESSION`) |
| `vector_source` | String | 사용자 자연어 문장과 유사도를 비교(Cosine Similarity)할 때 사용되는 임베딩 원본 텍스트 |
| `regex_pattern` | String | 변수 추출용. 정규식의 Named Group(`(?P<var_name>...)`)을 통해 정확한 변수 영역 캡처 |
| `variables` | Array | 템플릿이 요구하는 빈칸(변수)의 식별자 리스트 (주로 `["signal", "value"]`) |
| `target_code` | String | 최종적으로 조립될 언어별 코드 뼈대. (내부에 `{signal}`, `{value}` 등 치환 토큰 포함) |

### 2.2 샘플 데이터
SIMVA 타겟 환경에서의 제어는 결국 하나의 단일 API(`set_signal`)로 귀결되므로 뼈대는 고정적입니다.
```json
[
  {
    "id": "action_set_signal",
    "type": "ACTION",
    "vector_source": "{signal}를 {value}로 설정한다",
    "regex_pattern": "^.*?(?P<signal>[a-zA-Z가-힣0-9_\\s]+?)(?:을|를|은|는)?\\s+(?P<value>[a-zA-Z0-9_\\s\\.]+?)(?:으로|로)?\\s+(?:설정|세팅|변경).*$",
    "variables": ["signal", "value"],
    "target_code": "simva.set_signal(signals.{ecu}.{signal}, \"{value}\")"
  },
  {
    "id": "action_reset_full",
    "type": "TYPE_INIT",
    "vector_source": "전체 시스템을 리셋한다",
    "regex_pattern": "^(?:전체|시스템|차량|전부)\\s+리셋한다$",
    "variables": [],
    "target_code": "simva.reset_ecu()"
  },
  {
    "id": "action_reset_specific",
    "type": "TYPE_INIT",
    "vector_source": "{ecu}를 리셋한다",
    "regex_pattern": "^(?P<ecu>[a-zA-Z0-9_]+?)(?:\\s+제어기)?(?:를|을)\\s+리셋한다$",
    "variables": ["ecu"],
    "target_code": "simva.reset_ecu(\"{ecu}\")"
  },
  {
    "id": "meta_condition_ifelse",
    "type": "META_CONTROL_IFELSE",
    "vector_source": "{condition}이면 {true_action}한다. 그렇지 않으면 {false_action}한다.",
    "regex_pattern": "^(?P<condition>.+?)(?:이?면|인\\s*경우)\\s+(?P<true_action>.+?)(?:한다)[\\.\\s]*(?:그렇지\\s*않으면)\\s+(?P<false_action>.+?)(?:한다)$",
    "variables": ["condition", "true_action", "false_action"],
    "target_code": "if {condition}:\n    {true_action}\nelse:\n    {false_action}"
  },
  {
    "id": "meta_control_loop",
    "type": "META_CONTROL_LOOP",
    "vector_source": "{count}번 반복하며 {action}한다.",
    "regex_pattern": "^(?P<count>[0-9]+?)(?:번|회)\\s+반복하며\\s+(?P<action>.+?)(?:한다)$",
    "variables": ["count", "action"],
    "target_code": "for i in range({count}):\n    {action}"
  }
]
```

---

## 3. Vector DB 자동 구축 파이프라인 (Auto-Generation Pipeline)
Vector DB는 "정규표현식"과 "JSON 스키마"라는 고난이도의 구조를 띄고 있으므로, 사용자가 직접 코드를 짜는 고통에서 벗어날 수 있도록 **LLM-Assisted No-Code Pipeline**을 구축합니다.

### 3.1 예제 기반 템플릿 추출 (Few-Shot Inference)
관리자는 복잡한 정규식을 짤 필요 없이, 시스템에 직관적인 예제 한 줄만 던집니다.
*   **사용자 입력 예시**: `"블랙박스 전원을 ON 상태로 입력한다" -> simva.set_signal("{signal}", "{value}")`
*   **시스템 동작**: LLM이 사용자의 입력문을 분석하여 Vector DB 스키마에 정확히 들어맞는 정규식 세트(`(?P<signal>...)`)를 자동으로 역합성(Reverse Engineering)하여 DB에 Auto-Merge 합니다.

### 3.2. No-Code Template Builder UI (사용자 주도 확장)
현업 테스트 엔지니어가 시스템 로직을 1%도 알 필요 없이 즉각적으로 DB를 확장할 수 있는 파워풀한 Web UI 설계안입니다.

#### [Web UI Mockup 컨셉]
```text
================================================================================
🛠️ [Vector DB Template Builder] - 신규 패턴 학습
================================================================================

1️⃣ [Input] 새롭게 추가할 자연어 테스트 문장을 입력하세요.
📝 자연어 입력: [ 시트 열선을 3단으로 가동한다                            ]

--------------------------------------------------------------------------------
2️⃣ [Mapping] 문장에서 가변적인 단어를 마우스로 드래그하여 변수를 지정하세요.
🖱️ 드래그한 문장: [시트 열선]을 [3]단으로 가동한다
   └─ 우클릭 메뉴: [ 📌 (Signal)로 지정 ]
                  [ 📌 (Value) 로 지정 ]

✨ 파싱 결과:    [ {signal} ]을 [ {value} ]단으로 가동한다
--------------------------------------------------------------------------------
3️⃣ [Target] 변환될 SIMVA 코드를 확인하고 저장하세요.
💻 타겟 코드:   [ simva.set_signal(signals.{ecu}.{signal}, "{value}")    ] 🔒 (고정)

[ 💾 Vector DB에 즉시 배포 (Hot-Reload) ]
================================================================================
```

**워크플로우**:
1. 사용자가 웹 화면에서 문장을 적고, 동적으로 바뀌는 단어 두 개를 드래그하여 `[Signal]`과 `[Value]` 태그를 붙입니다.
2. 하단의 타겟 코드는 SIMVA 규칙상 `simva.set_signal()`로 이미 고정되어 있습니다.
3. [배포] 버튼을 누르면 내부 LLM 및 구문 분석기가 **어떤 문맥에서도 먹히는 정규식을 자동 생성하여 Vector DB에 즉시 삽입**합니다. 즉시 다음 스크립트 실행부터 적용됩니다.

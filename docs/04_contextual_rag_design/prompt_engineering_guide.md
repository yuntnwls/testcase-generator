# Contextual RAG — 프롬프트 엔지니어링 가이드 (방안 C)

본 문서는 방안 C (Contextual RAG 기반 Direct Synthesis)에서 생성형 LLM이 **실제로 호출되는 4가지 지점**에 대한 공식 시스템 프롬프트 템플릿을 정의합니다.

방안 C의 핵심 철학은 **"LLM은 최소한으로, 그러나 호출될 때는 최고의 컨텍스트로"**입니다. 방안 B(`docs/03_advanced_design/prompt_engineering_guide.md`) 대비 아래 두 가지를 개선합니다.

| 개선 항목 | 방안 B | 방안 C (본 문서) |
| :--- | :--- | :--- |
| **Ontology Router** | 전체 후보 목록을 LLM에 전달 | **Fuzzy Top-5 사전 필터링** 후 소량만 전달 |
| **Self-Correction** | 전체 코드 + 전체 Traceback 전달 | **Error Compressor** 적용 (±3줄 + 핵심 1줄) |
| **Context 품질** | type_source 텍스트만 임베딩 | **context_prefix** 포함 임베딩으로 검색 정확도↑ |
| **오프라인 인덱싱** | 없음 | **LLM이 사전 맥락 요약** (런타임 비용 0) |

---

## 1. 설계 원칙

- **역할 부여 (Persona)**: 모든 프롬프트에 명확한 역할(예: "변수 추출기", "코드 교정기")을 부여하여 도메인 특화 응답을 유도합니다.
- **JSON 모드 강제**: 모든 응답은 파이썬에서 100% 안전하게 파싱될 수 있도록 엄격한 JSON 스키마를 지정합니다.
- **후보 범위 사전 제한**: Ontology Router 호출 전 반드시 Fuzzy Filter로 Top-5 이하로 후보를 좁혀 전달합니다. 전체 목록을 LLM에 절대 주입하지 않습니다.
- **에러 컨텍스트 압축**: Self-Correction 시 전체 코드가 아닌 에러 발생 위치 ±3줄만 제공합니다.

---

## 2. LLM 호출 지점별 프롬프트 상세

### 2-1. [Extractor Tier 3] 변수 추출기 — Regex/Alignment 실패 시

Regex Named Capture(Tier 1)와 Sequence Alignment(Tier 2)가 모두 실패했을 때, 입력 문장과 템플릿을 비교 분석하여 변수를 추출합니다.

- **호출 시점**: 템플릿 매칭은 성공(Score ≥ 0.75)했으나, 변수 딕셔너리 추출 실패 시
- **예상 빈도**: 전체 Step의 약 5% (방안 B 10%에서 context_prefix 적용으로 감소)
- **예상 비용**: Input ~600 tok + Output ~50 tok / 호출

**System Prompt**:
```text
당신은 자율주행 차량 소프트웨어 검증 시스템의 "변수 추출기(Variable Extractor)"입니다.
주어진 [입력 문장]과 이 문장이 매핑되는 [타겟 템플릿]을 비교 분석하세요.
[타겟 템플릿] 내의 가변 슬롯(예: {signal}, {value}, {duration})에 맞는
원시 문자열을 [입력 문장]에서 정확히 도출해야 합니다.

[제약 사항]
1. 오직 JSON 형식으로만 응답하세요. 부연 설명은 금지합니다.
2. 템플릿에 없는 변수 키(Key)를 임의로 생성하지 마세요.
3. 추출된 값(Value)은 입력 문장의 원래 단어를 최대한 그대로 유지하세요.
4. 변수를 특정할 수 없으면 해당 키의 값을 null로 반환하세요.

[예시 1]
입력 문장: "와이퍼 속도를 가장 빠른 단계인 3단으로 작동시켜라"
타겟 템플릿: "{signal}을 {value}로 설정한다"
=> {"signal": "와이퍼 속도", "value": "가장 빠른 단계인 3단"}

[예시 2]
입력 문장: "IG ON 상태에서 5초 머무르고 다음으로 넘어감"
타겟 템플릿: "{state} 상태에서 {duration}초 간 대기한다"
=> {"state": "IG ON", "duration": "5"}
```

**User Prompt (런타임 주입)**:
```text
[입력 문장]: "{user_input}"
[타겟 템플릿]: "{matched_type_source}"
[템플릿 설명]: "{context_prefix}"

결과를 JSON으로 반환하세요.
```

> [!NOTE]
> 방안 C에서 `[템플릿 설명]` 필드에 `context_prefix`를 추가로 주입합니다. 이는 LLM이 템플릿의 의도를 더 정확히 파악하여 변수 경계를 올바르게 구분하도록 돕습니다. (+50 tok 증가, 정확도 향상 효과)

---

### 2-2. [Ontology Router] 은어 매핑 — Fuzzy Filter 통과 후 호출

Extractor가 추출한 원시 단어가 Ontology DB의 synonyms 목록에 정확히 일치하지 않을 때, Fuzzy Top-5 후보만 LLM에 전달하여 가장 적합한 매핑을 선택합니다.

- **호출 시점**: Fuzzy Filter 점수 < 80 (불확실한 경우)
- **예상 빈도**: 전체 Step의 약 3% (방안 B 5%에서 Fuzzy Filter 개선으로 감소)
- **예상 비용**: Input ~300 tok + Output ~30 tok / 호출 (방안 B ~800 tok에서 62% 절감)

**System Prompt**:
```text
당신은 차량 테스터들이 사용하는 현장 은어를 공식 DBC/ARXML 스펙 용어로 번역하는
"온톨로지 라우터(Ontology Router)"입니다.
사용자가 입력한 [원시 단어]를 아래 [후보 개념 목록] 중 의미상 가장 일치하는
하나의 항목으로 매핑하세요.

[제약 사항]
1. 반드시 제공된 [후보 개념 목록] 내의 concept_id 중 하나만 선택하세요.
2. 목록에 없는 값을 절대 생성하지 마세요.
3. 신뢰도(confidence)를 0.0~1.0 범위의 소수로 함께 반환하세요.
4. confidence가 0.8 미만이면 "unsure"를 true로 설정하세요.

[예시]
후보 개념 목록:
  [{"concept_id": "Concept:LowBeam", "label": "하향등", "synonyms": ["로빔", "하이빔", "dim light"]},
   {"concept_id": "Concept:HighBeam", "label": "상향등", "synonyms": ["하이빔", "high beam", "원거리등"]}]
원시 단어: "불 들어옴"
=> {"concept_id": "Concept:LowBeam", "confidence": 0.82, "unsure": false}
```

**User Prompt (런타임 주입)**:
```text
[후보 개념 목록]: {fuzzy_top5_candidates_json}
[원시 단어]: "{raw_alias}"
```

> [!IMPORTANT]
> **`{fuzzy_top5_candidates_json}`은 반드시 Fuzzy Filter가 사전 추려낸 5개 이하의 후보만 포함**해야 합니다. 전체 Ontology 노드 목록을 절대 그대로 주입하지 마세요. `unsure: true`인 결과는 즉시 코드 생성을 중단하고 관리자 UI의 **Approval Queue**에 등록합니다.

---

### 2-3. [Self-Correction] 코드 교정기 — Error Compressor 통과 후 호출

조립된 Python 코드가 `ast.parse()` 검증에 실패했을 때, 에러 컨텍스트를 압축하여 LLM에 전달하고 수정된 코드를 반환받습니다. **최대 3회 반복됩니다.**

- **호출 시점**: `ast.parse()` 또는 신호 이름 검증 실패 시
- **예상 빈도**: 전체 Step의 약 10%
- **예상 비용**: Input ~500 tok + Output ~100 tok / 호출 (방안 B ~1,500 tok에서 67% 절감)

**System Prompt**:
```text
당신은 파이썬 디버깅 및 자가 복구를 수행하는 "코드 교정기(Self-Correction Engine)"입니다.
AI가 생성했던 코드가 [에러 발생 위치 코드]에서 [에러 메시지]와 함께 실패했습니다.
에러 원인을 파악하여 올바르게 수정된 전체 코드를 반환하세요.

[제약 사항]
1. Syntax Error는 들여쓰기, 괄호, 콜론 등을 바로잡으세요.
2. NameError/AttributeError는 에러에 제시된 올바른 신호명으로 교체하세요.
3. 수정된 파이썬 코드의 내용만 순수 텍스트로 반환하세요.
   (```python 같은 마크다운 블록을 사용하지 마세요)
4. 수정하지 않아도 되는 라인은 절대 변경하지 마세요.
```

**User Prompt (런타임 주입)**:
```text
[원본 TC 목적]: "{original_tc_text}"

[에러 발생 위치 코드 (±3줄)]:
{compressed_error_context}

[핵심 에러 메시지]:
{error_one_liner}

위 에러를 수정한 전체 코드를 반환하세요.
```

**Error Compressor가 생성하는 `compressed_error_context` 예시**:
```
      L10: result = simva.is_eq(signals.BCM.Wiper_Staus, "ON")
>>>>> L11: simva.set_signal(signals.BCM.Wiper_Staus, "HIGH")
      L12: simva.wait(3.0)
```

> [!TIP]
> `{compressed_error_context}`는 `src/core/validator.py`의 `compress_error_context()` 함수([01_architecture.md §2.4](./01_architecture.md) 참조)가 자동 생성합니다. 에러 발생 줄(Line Number)을 기준으로 앞뒤 3줄만 추출하여 ~150 tokens로 압축합니다.

---

### 2-4. [Template Rescue] 패턴 뼈대 추론 — 미등록 문장 처리

Vector DB 검색 결과의 최고 Score가 임계값(0.75) 미만일 때, LLM이 문장 유형을 추론하고 초안 템플릿을 생성합니다.

- **호출 시점**: `retrieve_templates()` 결과가 비어 있을 때 (`score_threshold` 미통과)
- **예상 빈도**: 전체 Step의 약 2% (방안 B 3%에서 context_prefix 적용으로 감소)
- **예상 비용**: Input ~400 tok + Output ~150 tok / 호출

**System Prompt**:
```text
당신은 자동차 제어 테스트 스크립트 패턴을 추론하는 "패턴 유추기(Template Rescue Engine)"입니다.
다음 [미등록 자연어 TC]를 분석하여 아래 [허용 패턴 유형] 중 가장 적합한 것을 고르고,
이 문장에서 추출해야 할 변수 슬롯을 포함한 초안 코드 템플릿을 작성하세요.

[허용 패턴 유형]
- ACTION: 단발적 값 설정 (ex: simva.set_signal(...))
- TYPE_WAIT: 특정 시간 대기 (ex: simva.wait(...))
- TYPE_CHECK: 상태 일치 판정 (ex: simva.is_eq(...))
- META_CONTROL_IFELSE: if/else 조건 분기 구조
- META_CONTROL_LOOP: 일정 횟수 반복 구조

[제약 사항]
1. JSON으로만 응답하세요.
2. draft_template의 슬롯 이름은 의미 있는 영문 소문자로 작성하세요.
3. 해당 결과는 확정 코드가 아닌 관리자 UI의 초안으로 제출됩니다.

[예시]
미등록 자연어 TC: "썬루프를 절반만 열고 3초 기다리기를 5번 실시할 것"
=> {
    "recommended_type": "META_CONTROL_LOOP",
    "type_source": "{action}동작을 {count}번 반복한다",
    "draft_template": "for _ in range({count}):\n    simva.set_signal(signals.{ecu}.{signal}, {value})\n    simva.wait({wait_time})"
   }
```

**User Prompt (런타임 주입)**:
```text
[미등록 자연어 TC]: "{user_input}"
```

> [!NOTE]
> Template Rescue 결과는 확정 코드로 즉시 사용되지 않습니다. 반환된 `type_source`와 `draft_template`은 관리 UI의 **No-Code Template Builder** 탭에 초안으로 자동 등록되며, 테스트 엔지니어가 검토·확정 후 Vector DB에 추가됩니다.

---

## 3. 오프라인 전용 — Contextual Indexer 프롬프트

이 프롬프트는 **런타임이 아닌 오프라인 DB 구축 배치**에서만 사용됩니다. `scripts/build_vector_db.py` 실행 시 각 템플릿에 `context_prefix`를 생성하는 데 사용하며, 런타임 비용에 영향을 주지 않습니다.

- **실행 시점**: 신규 템플릿 추가 또는 DB 재인덱싱 시 (1회성)
- **예상 비용**: 템플릿 200개 기준 총 $0.006 (일회성)

**System Prompt**:
```text
당신은 자동차 소프트웨어 테스트 자동화 시스템의 "템플릿 맥락 요약기"입니다.
```

**User Prompt (배치 스크립트 주입)**:
```text
아래 코드 생성 템플릿 정보를 보고 3문장 이내로 요약하세요.
이 요약은 임베딩 검색에 사용되므로, 관련 동의어와 용도를 풍부히 포함하세요.
특히 아래 내용을 포함하세요:
1. 이 템플릿은 어떤 상황에서 쓰이는가?
2. 전기/전자 제어 관점에서 어떤 ECU나 물리 부품과 관련되는가?
3. 이 문장 유형을 지칭하는 현장 은어나 동의어는 어떤 것이 있는가?

[템플릿 데이터]
id: {id}
type: {type}
type_source: "{type_source}"
target_code: "{target_code}"
```

---

## 4. 프롬프트 버전 관리 및 파일 구조

프롬프트는 **코드와 동일하게 Git으로 버전 관리**되어야 합니다.

```
src/prompts/
├── extractor_tier3.jinja       ← 변수 추출기 (2-1)
├── ontology_router.jinja       ← 은어 매핑 (2-2)
├── self_correction.jinja       ← 코드 교정기 (2-3)
├── template_rescue.jinja       ← 패턴 뼈대 추론 (2-4)
└── contextual_indexer.jinja    ← 오프라인 맥락 요약 (3)
```

각 파일은 Jinja2 템플릿 형식으로 작성하여 `{user_input}`, `{context_prefix}` 등의 변수를 런타임에 주입받습니다. LangChain의 `PromptTemplate` 또는 `ChatPromptTemplate`에 직접 로드하여 사용합니다.

```python
from langchain.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_file("src/prompts/ontology_router.jinja")
response = llm.invoke(prompt.format(
    fuzzy_top5_candidates_json=candidates_json,
    raw_alias=raw_alias
))
```

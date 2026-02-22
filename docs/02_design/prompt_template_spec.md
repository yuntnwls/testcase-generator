# 동적 프롬프트(Dynamic Prompt) 템플릿 설계서

본 문서는 Core Engine이 사용자 자연어(TC)를 수용하고, Vector DB 및 Ontology의 검색 결과를 결합하여 최종적으로 LLM에게 전달하는 **프롬프트의 구성 및 템플릿**을 정의합니다. 

이 프롬프트 아키텍처는 **고정된 지시어(System Prompt)**와 **동적으로 삽입되는 문맥(Dynamic Context)**으로 분리되어 설계되었습니다.

---

## 1. 프롬프트 구조 (Prompt Architecture)

LLM에 전달되는 전체 입력(Payload)은 크게 3가지 계층으로 나뉩니다.

1. **System Prompt (시스템 프롬프트)**: LLM의 역할, 응답 형식(JSON), 예외 처리 규칙 등 절대 변하지 않는 핵심 지시사항.
2. **Context Injection (동적 문맥 주입)**: Vector DB와 Ontology에서 현재 스텝(문장)을 분석하여 얻어낸 '참고 자료' 및 '과거 스텝 요약'.
3. **User Input & Instruction (사용자 입력 및 지시)**: 실제 변환해야 할 대상 텍스트.

---

## 2. System Prompt 템플릿

시스템 프롬프트는 LLM에게 명확한 페르소나를 부여하고, 반드시 **우리가 설계한 Pydantic JSON 모델 (IR)** 포맷으로만 응답하도록 강제합니다.

```text
[SYSTEM]
당신은 자동차 도메인 테스트 스크립트의 "중간 표현(Intermediate Representation, IR)"을 생성하는 전문 AI 오라클입니다. 
당신의 유일한 임무는 사용자의 자연어 테스트 스텝을 분석하여 지정된 JSON 스키마에 맞는 순수한 JSON 객체 1개를 반환하는 것입니다. 
코드, 설명, 인사말을 절대 포함하지 마십시오.

# IR JSON Schema Types:
- SET: 시그널 값을 변경할 때 (필드: logical_signal, value)
- CHECK: 상태를 확인할 때 (필드: logical_signal, operator, expected_value, duration_sec)
- WAIT: 대기할 때 (필드: duration_sec)
- MACRO_CALL: 복합 함수를 호출할 때 (필드: macro_name)
- UNKNOWN: 해석 불가 또는 논리적 오류 발생 시 (필드: reason)

# Rules:
1. 제공되는 [Context] 영역의 RAG(VectorDB/Ontology) 데이터를 최우선으로 신뢰하여 logical_signal을 선택할 것.
2. 도메인 제약조건(Pre-condition)을 위반한 조작이 발견되면, 무리하게 SET으로 변환하지 말고 반드시 UNKNOWN 타입으로 분류하고 reason에 위반 사유를 명시할 것.
3. 시그널 값(value)은 [Context]에 제공된 Data Type에 맞게 변환할 것. (예: enum 일 경우 해당 문자열로)
```

---

## 3. Dynamic Context Injection 템플릿 (RAG 기반)

이 영역은 **Python Core Engine 로직에 의해 런타임에 동적으로 채워지는(Formatting)** 부분입니다. 사용자 문장을 사전에 Vector DB와 Ontology에 찔러보고 얻은 결과를 삽입합니다.

```text
[CONTEXT]
### 1. Vector DB Match Results (유사어 검색 결과)
(Core Engine이 사용자 문장에서 찾은 키워드의 Vector DB 매칭 결과를 넣어줍니다)
- 매칭 후보 1: Logical Signal = `{vd_logical_signal}` (유사도: {vd_score})
  - 설명: {vd_desc}
  - 허용 타입: {vd_type} / {vd_allowed_values}

### 2. Ontology Validation (제약 조건 검증 결과)
(Core Engine이 해당 시그널 조작 전 과거 상황(History)을 분석한 결과를 넣어줍니다)
- 연관 제약 조건: `{onto_rule_desc}`
- 제약 조건 충족 여부 검사 결과: `{onto_validation_result}` 
  (예: "PASS" 또는 "FAIL: 이전 스텝에서 Ignition_Status == ON 조작이 발견되지 않음")

### 3. Previous Steps Summary (과거 상태 문맥)
(이전까지 진행된 TC 스텝들의 간략한 상태(State)를 요약하여 암묵적 대명사('그것') 추론을 돕습니다)
- 최근 조작된 시그널: `{history_recent_signals}`
- 현재 주요 차량 상태: `{history_current_state}`
```

## 4. User Input 템플릿 및 Few-Shot 예시

마지막으로 변환해야 할 실제 문장을 제공합니다. **Few-Shot Prompting**(몇 가지 정답 예시를 미리 보여주는 기법)을 삽입하여 LLM의 JSON 출력 품질을 극적으로 높입니다.

```text
[INSTRUCTION]
위 규칙 및 문맥 데이터를 바탕으로 아래 [Target Step]에 대한 IR JSON을 하나만 반환하세요.

# Few-Shot Examples
User: "3초 대기한다."
Assistant: {"type": "WAIT", "duration_sec": 3.0}
User: "아무말 대잔치 출력해"
Assistant: {"type": "UNKNOWN", "reason": "No matching signal or logic found"}

# Target Step
Text: "{user_raw_text}"

생성 결과(JSON):
```

---

## 5. 파이썬 코드 레벨 조립 예시 (Python f-string)

Core Engine 내의 `PromptBuilder` 클래스는 위 3가지 템플릿을 조합하여 최종 String을 만듭니다.

```python
def build_prompt(user_text: str, rag_context: dict) -> str:
    system_prompt = get_system_prompt()
    
    # RAG 데이터가 있을 때만 Context 영역 생성
    context_str = ""
    if rag_context.get("vector_db_match"):
        context_str += f"- Vector DB 매칭: {rag_context['vector_db_match']}\n"
    if rag_context.get("ontology_validation"):
        context_str += f"- 제약 조건 검증: {rag_context['ontology_validation']}\n"
        
    dynamic_context = f"[CONTEXT]\n{context_str}\n" if context_str else ""
    
    user_instruction = f"[INSTRUCTION]\nTarget Step: '{user_text}'\n생성 결과(JSON):\n"
    
    return f"{system_prompt}\n{dynamic_context}\n{user_instruction}"
```

---

## 6. 프롬프트의 작동 시점 (Timing of Execution)

사용자가 헷갈리기 쉬운 **"이 프롬프트가 정확히 언제 쓰이는가?"**에 대한 시스템 흐름(시퀀스 다이어그램 기준)은 다음과 같습니다.

1. **[사용자 동작]** 사용자가 엑셀 파일(혹은 텍스트)로 TC를 업로드하고 "변환" 버튼을 누릅니다.
2. **[반복문 시작]** Core Engine은 TC를 한 줄씩 분리하여 반복문을 돕니다. (예: `Step 1: 엑셀을 밟는다`, `Step 2: 에어컨을 튼다`)
3. **[RAG 검색]** 1번 스텝인 `"엑셀을 밟는다"` 텍스트를 우선 Vector DB와 Ontology에 던져서 관련된 지식(Context)을 뽑아냅니다.
4. **[프롬프트 조립]** 바로 이 시점! 방금 뽑아낸 지식과 원본 텍스트(`"엑셀을 밟는다"`)를 합쳐서 **본 문서에 정의된 거대한 프롬프트 1개**를 프로그래밍 방식으로 조립(String Formatting)합니다.
5. **[LLM 호출]** 조립된 프롬프트를 LLM(Ollama/OpenAI)에 보냅니다.
6. **[IR 생성]** LLM이 이 프롬프트를 읽고, 결과물로 단 1개의 JSON(`{"type": "SET", ...}`)을 반환합니다.
7. **[다음 스텝]** 2번 스텝(`"에어컨을 튼다"`)으로 넘어가 구조적으로 동일하지만 내용만 바뀐 프롬프트를 다시 조립하여 LLM을 호출합니다.

결론적으로 이 동적 프롬프트는 **"TC의 각 스텝(한 줄)을 분석하여 IR(JSON) 하나를 뽑아내야 할 때마다 (Phase 2 단계에서) 방금 찾은 최신 지식을 꾹꾹 눌러 담아 매번 새롭게 조립되어 LLM으로 전송되는 일회용 작업 지시서"**입니다. 전체 스크립트를 한 번에 던지는 것이 아닙니다.

이 프롬프트 아키텍처를 통해, LLM은 백지 상태에서 추측('환각')하는 대신, **우리가 제공하는 족보(Vector DB)와 법전(Ontology) 그리고 엄격한 답안지 양식(JSON Schema) 안에서만 안전하게 동작**하게 됩니다.

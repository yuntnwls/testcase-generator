# Template Rescue Flow & UI 연동 설계

본 문서는 방안 C 아키텍처에서 Retriever 검색 결과가 미달되거나, 모든 검증 로직이 실패했을 때 **테스트 엔지니어가 직접 개입하는 Rescue Flow 및 No-Code UI 연동의 상세 설계**를 다룹니다.

*   **관련 문서**: [architecture.md](architecture.md) | [execution_sequence.md](execution_sequence.md) §6 | [prompt_engineering_guide.md](prompt_engineering_guide.md) §2-4

---

## 1. "미등록 패턴" 발생 조건

방안 C는 LLM을 활용한 완전 자동화를 지향하지만, **시스템이 학습하지 못한 완전히 새로운 동작(New Action)**이 처음 등장했을 때 이를 스스로 창조하도록 방치하면 환각(Hallucination) 리스크가 큽니다.

`Template Rescue Flow`가 트리거되는 시점은 다음 두 가지입니다.

1.  **Retriever Score 미달**: Vector DB 검색 시 `score_threshold=0.75`를 넘는 템플릿이 단 1개도 없을 때.
    *   이는 사용자가 입력한 문장이 기존 패턴과 완전히 다른 의미를 지님을 뜻합니다.
2.  **Self-Correction 3회 초과 실패**: 템플릿 자체는 검색되었고 Regex, LLM을 통해 변수 추출도 시도했지만 `Validator`를 3회 이상 통과하지 못했을 때.
    *   보통 입력 문장이 너무 복잡하게 꼬여 있어 조립된 코드가 계속 파이썬 문법 에러를 유발하는 경우입니다.

---

## 2. Template Rescue Engine의 동작 (초안 생성)

위 조건에 해당하여 시스템 변환이 불가능하다고 판단되면, 즉시 에러를 내고 멈추는 대신 **LLM을 호출하여 '이 문장이 어떤 구조를 가져야 하는지 최소한의 뼈대(Draft)'를 유추**하게 합니다.

```python
def rescue_unknown_template(user_text: str, llm_client) -> dict:
    """새로운 유형의 패턴 등장 시, LLM으로 초안만 작성하여 큐에 넘김"""
    from src.prompts import TEMPLATE_RESCUE_PROMPT
    prompt = TEMPLATE_RESCUE_PROMPT.format(user_input=user_text)
    
    response = llm_client.invoke(prompt)
    import json
    return json.loads(response.content)

# LLM 반환 예시 (JSON):
# {
#     "recommended_type": "META_CONTROL_LOOP",
#     "type_source": "{action}동작을 {count}번 반복한다",
#     "draft_template": "for _ in range({count}):\n    simva.set_signal(signals.{ecu}.{signal}, {value})\n    simva.wait({wait_time})"
# }
```

> **주의**: 이 결과물(`draft_template`)은 절대 실행 코드로 즉시 삽입되지 않습니다. 오로지 관리자의 편의를 돕는 초안(Draft) 목적으로만 사용됩니다.

---

## 3. Approval Queue (승인 대기열) 및 No-Code Builder UI

변환에 실패한 원문(`user_text`)과 Rescue Engine이 생성한 초안(`draft_template`)은 데이터베이스의 **Approval Queue(승인 대기열 테이블)**에 로깅됩니다.

테스트 엔지니어(사용자)는 다음과 같은 흐름으로 UI를 통해 개입합니다.

### 3.1. 관리자 뷰 (Review Dashboard)

사용자는 대시보드에서 `[Status: Action Required]`가 뜬 TC 항목들을 확인합니다.
클릭하면 "이 문장을 시스템이 이해하지 못했습니다. 새로운 템플릿 규칙으로 등록하시겠습니까?" 라는 창이 뜹니다.

### 3.2. No-Code Template Builder 동작 흐름

1.  **UI 전시**: LLM이 유추한 `type_source`(예: `{action}동작을 {count}번 반복한다`)와 `target_code` 뼈대가 화면에 자동으로 채워져 있습니다. 빈 칸부터 시작하지 않아도 되므로 사용자 편의성이 크게 향상됩니다.
2.  **사용자 수정 및 태깅**: 사용자는 코드가 프로젝트 표준에 맞는지 약간 수정하고, 드래그&드롭 혹은 버튼을 통해 가변 변수(`{count}`, `{action}`)를 지정합니다.
3.  **저장 및 즉시 배포**: 저장을 누르는 순간, 백그라운드에서는 아래 작업이 수행됩니다.
    *   ① [오프라인 문서의 Contextual Indexer 호출](offline_pipeline_design.md): 변경된 템플릿에 대한 `context_prefix` 요약본을 LLM이 다시 만듭니다.
    *   ② 정규식 합성을 거쳐 **Vector DB에 실시간 Insert(Upsert)** 됩니다.
    *   ③ 이전에 실패했던 동일 패턴의 TC 변환 Job이 재개됩니다.

---

## 4. 자가 성장 플라이휠 (Self-Improving Flywheel)

이 Rescue Flow 덕분에, 본 시스템은 새로운 프로젝트나 완전히 새로운 차종 기능이 추가되더라도 코드를 하드코딩으로 고칠 필요가 없습니다.

```
새로운 스펙 문서 등장 -> 
TC 변환 실패 빈도 증가 -> 
Approval Queue에 쌓임 + LLM이 초안 제안 -> 
테스터가 UI에서 클릭 몇 번으로 Confirm -> 
Vector DB 업데이트 -> 
동일 패턴 전부 Pattern Cache Hit로 처리 속도 폭증 (환각 0%)
```

**"LLM이 스스로 학습 도구(초안)를 제공하고, 인간이 검문(No-Code UI)하며, 패턴 캐시가 그것을 복제(빠른 재실행)하는 자가 증식 아키텍처"**가 완성됩니다.

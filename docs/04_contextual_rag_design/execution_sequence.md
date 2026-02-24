# Contextual RAG — 실행 시퀀스 설계서 (방안 C)

본 문서는 방안 C (Contextual RAG 기반 Direct Synthesis) 아키텍처의 **실제 런타임 실행 흐름**을 시퀀스 다이어그램과 함께 상세히 설명합니다. 방안 B(`docs/03_advanced_design/execution_sequence.md`)와 달리 **Pattern Cache**, **Contextual Vector DB**, **Fuzzy Filter**, **Error Compressor** 모듈이 추가된 흐름입니다.

---

## 1. 핵심 변환 시퀀스 — 단순 Action 문장 (Happy Path)

가장 빈번한 케이스인 **Tier 1 (Regex) 성공 경로**입니다. 생성형 LLM을 전혀 사용하지 않습니다.

```mermaid
sequenceDiagram
    participant User as Core Engine
    participant Cache as Pattern Cache
    participant Ret as Retriever
    participant VDB as Contextual Vector DB
    participant Ext as Extractor (Tier 1)
    participant Asm as Assembler
    participant ODB as Ontology DB
    participant Val as Validator

    User->>Cache: 1. 입력 문장 캐시 조회
    Cache-->>User: 2. 캐시 미스 (최초 처리)

    User->>Ret: 3. retrieve_templates("좌측 헤드램프를 상향등으로 켜라")
    Ret->>VDB: 4. Embedding 검색 (top_k=3)
    VDB-->>Ret: 5. action_set_signal (score=0.89 > 0.75 통과)
    Ret-->>User: 6. TemplateMatch 반환 (regex_pattern, target_code 포함)

    User->>Ext: 7. Tier 1 Regex 실행
    Note over Ext: 정규식 매칭 성공<br/>signal=좌측 헤드램프, value=상향등

    Ext-->>User: 8. variables = {signal, value} 반환

    User->>Asm: 9. Ontology 매핑 요청
    Asm->>ODB: 10. Fuzzy Filter (TheFuzz, Top-5 추출)
    ODB-->>Asm: 11. Left_HeadLamp 매핑 (score:94), HIGH 값 정규화
    Asm-->>User: 12. 완성 코드 반환<br/>simva.set_signal(signals.BCM.Left_HeadLamp, "HIGH")

    User->>Val: 13. ast.parse() 검증
    Val-->>User: 14. 검증 통과

    User->>Cache: 15. 결과 캐싱 (LRU)
    User-->>User: 16. 최종 코드 확정
```

**비용**: Embedding 호출 1회 + 모든 나머지 처리 로컬 (생성형 LLM 0회)

---

## 2. 핵심 변환 시퀀스 — 복합 조건문 (재귀적 메타-템플릿)

`"차량 속도가 100이면 와이퍼를 작동한다"` 같은 조건문의 재귀 파싱 흐름입니다.

```mermaid
sequenceDiagram
    participant User as Core Engine
    participant Ret as Retriever
    participant VDB as Contextual Vector DB
    participant Ext as Extractor (Tier 1)
    participant Asm as Assembler
    participant ODB as Ontology DB

    Note over User: 입력: "차량 속도가 100이면 와이퍼를 작동한다"

    User->>Ret: 1. retrieve_templates (메인 문장)
    Ret->>VDB: 2. Embedding 검색
    VDB-->>Ret: 3. meta_condition_ifelse 반환 (score=0.91)
    Ret-->>User: 4. META_CONTROL_IFELSE 템플릿 반환

    User->>Ext: 5. Tier 1 Regex 파싱
    Note over Ext: condition = "차량 속도가 100"<br/>true_action = "와이퍼를 작동한다"

    Note over User: === 재귀 1차: condition 파싱 ===
    User->>Ret: 6. retrieve_templates("차량 속도가 100")
    VDB-->>Ret: 7. action_compare_signal 반환 (EXPRESSION 타입)
    Ret-->>User: 8. signals.{ecu}.{signal} {op} {value} 템플릿

    Asm->>ODB: 9. "차량 속도" Fuzzy 검색 → Concept:VehicleSpeed
    ODB-->>Asm: 10. CGW.V_Spd_Main (Variant:CarModel_B 기준)
    Note over User: condition_code = "signals.CGW.V_Spd_Main == 100"

    Note over User: === 재귀 2차: true_action 파싱 ===
    User->>Ret: 11. retrieve_templates("와이퍼를 작동한다")
    VDB-->>Ret: 12. action_set_signal 반환
    Asm->>ODB: 13. "와이퍼" Fuzzy → Concept:Wiper → BCM.Wiper_State
    Note over User: action_code = "simva.set_signal(signals.BCM.Wiper_State, 'ON')"

    Note over User: === 최종 조립 ===
    Note over User: if signals.CGW.V_Spd_Main == 100:<br/>    simva.set_signal(signals.BCM.Wiper_State, "ON")
```

---

## 3. Fallback 시퀀스 — Tier 3 SLM 변수 추출

Tier 1 (Regex), Tier 2 (Alignment)가 모두 실패하여 **생성형 LLM을 사용하는 경로**입니다.

```mermaid
sequenceDiagram
    participant User as Core Engine
    participant Ext1 as Extractor Tier 1 (Regex)
    participant Ext2 as Extractor Tier 2 (Alignment)
    participant SLM as SLM (생성형 LLM)
    participant Asm as Assembler

    Note over User: 입력: "100을 타겟 속도로 맞춰주세요"
    Note over User: (일치하는 템플릿: {signal}를 {value}로 설정한다)

    User->>Ext1: 1. Regex Named Capture 시도
    Ext1-->>User: 2. 실패 (어순 역전으로 패턴 미매칭)

    User->>Ext2: 3. Sequence Alignment (LCS 차분) 시도
    Ext2-->>User: 4. 실패 (공통 부분이 너무 짧아 특정 불가)

    User->>SLM: 5. Tier 3 Fallback 호출
    Note over SLM: System Prompt: 변수 추출기 역할 부여<br/>Few-Shot 2개 주입<br/>Input ~600 tokens
    SLM-->>User: 6. {"signal": "VehicleSpeed", "value": "100"} 반환

    User->>Asm: 7. 추출된 변수로 Assembler 진행
```

**비용**: 생성형 LLM 1회 (~600 Input + ~50 Output tokens)

---

## 4. Self-Correction 시퀀스 — Error Compressor 활용

Validator가 Syntax 오류를 감지했을 때 **에러 압축 후 LLM 재호출**하는 흐름입니다.

```mermaid
sequenceDiagram
    participant Asm as Assembler
    participant Val as Validator
    participant ErrComp as Error Context Compressor
    participant SLM as SLM (생성형 LLM)

    Asm-->>Val: 1. 조립된 코드 전달
    Val->>Val: 2. ast.parse() 실행
    Val-->>Val: 3. NameError: 'Wiper_Staus' is not defined (Line 12)

    Val->>ErrComp: 4. 전체 코드 + 에러 전달
    Note over ErrComp: 에러 발생 Line 12 기준 ±3줄만 추출<br/>에러 마지막 줄 1줄만 요약
    ErrComp-->>Val: 5. 압축된 컨텍스트 반환 (~150 tokens)

    Val->>SLM: 6. Self-Correction 호출
    Note over SLM: System Prompt: 코드 교정기 역할 부여<br/>User: 원본 목적 + 압축 에러 컨텍스트<br/>Input ~500 tokens (기존 방안 ~1,500 대비 67% 절감)
    SLM-->>Val: 7. 수정된 코드 반환 (Wiper_Status 오타 교정)

    Val->>Val: 8. ast.parse() 재검증
    Val-->>Val: 9. 통과
    Note over Val: 최대 3회 반복 후 실패 시<br/>Approval Queue에 등록
```

---

## 5. Pattern Cache 히트 시퀀스 (비용 제로)

동일 문장이 반복 등장할 때 **모든 파이프라인을 건너뛰는** 흐름입니다.

```mermaid
sequenceDiagram
    participant User as Core Engine
    participant Cache as Pattern Cache (LRU)

    Note over User: 입력: "시동을 ON으로 설정한다" (두 번째 이상 등장)

    User->>Cache: 1. 캐시 조회 (입력 문장 해시 Key)
    Cache-->>User: 2. 캐시 히트! 코드 즉시 반환<br/>"simva.set_signal(signals.BCM.IG_Status, 'ON')"

    Note over User: Retriever, Extractor, Assembler,<br/>Validator 모두 건너뜀<br/>비용: 0 token, 처리 시간: ~0.1ms
```

---

## 6. Vector DB 유지보수 시퀀스 — No-Code 템플릿 등록

테스트 엔지니어가 관리 UI에서 새 패턴을 직접 등록하는 흐름입니다.

```mermaid
sequenceDiagram
    actor TE as 테스트 엔지니어
    participant UI as No-Code Builder UI
    participant Backend as Vector DB Builder
    participant LLM as LLM (gpt-4o-mini)
    participant VDB as Contextual Vector DB

    TE->>UI: 1. 자연어 예시 입력 ("시트 열선을 3단으로 켜라")
    TE->>UI: 2. 가변 단어 태깅<br/>[signal=시트 열선], [value=3단]
    TE->>UI: 3. 저장 및 배포 버튼 클릭

    UI->>Backend: 4. 태깅된 패턴 정보 전송

    Backend->>Backend: 5. Named Group 정규식 자동 합성
    Backend->>LLM: 6. context_prefix 생성 요청
    Note over LLM: 템플릿 의미와 제약사항 3문장 요약<br/>~200 Input + ~100 Output tokens
    LLM-->>Backend: 7. context_prefix 반환

    Backend->>Backend: 8. vector_source 조합<br/>(context_prefix + type_source)
    Backend->>VDB: 9. Upsert (임베딩 자동 생성 및 저장)
    VDB-->>Backend: 10. 저장 완료

    Backend-->>UI: 11. 성공 응답
    UI-->>TE: 12. "등록 완료! 즉시 적용됩니다."
```

---

## 7. 방안 B vs 방안 C 시퀀스 비교

| 시퀀스 단계 | 방안 B (03 설계) | 방안 C (04 설계, 추가된 모듈) |
| :--- | :--- | :--- |
| **캐시 조회** | 없음 | ✅ Pattern Cache (LRU) 선행 조회 |
| **Vector DB 검색** | 일반 임베딩 검색 | ✅ context_prefix 포함 Contextual 검색 |
| **Score 필터** | 없음 (모든 결과 사용) | ✅ score_threshold=0.75 노이즈 차단 |
| **Ontology 매핑** | 전체 노드 LLM 전달 | ✅ Fuzzy Top-5 사전 필터링 후 소량만 전달 |
| **에러 처리** | 전체 코드 + 전체 Traceback | ✅ Error Compressor: ±3줄 + 요약 1줄만 |
| **DB 등록** | 수동 JSON 편집 | ✅ No-Code Builder UI + LLM context_prefix 자동 생성 |

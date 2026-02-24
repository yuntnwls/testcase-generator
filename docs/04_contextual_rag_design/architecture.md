# 차세대 Contextual RAG 아키텍처 상세 설계서 (방안 C 구현 가이드)

본 문서는 `rag_cost_optimization_strategy.md`에서 도출된 최적의 전략인 **방안 C (Contextual RAG 기반 Direct Synthesis)**를 시스템 수준에서 어떻게 구현할 것인지 상세히 정의한 아키텍처 설계서입니다.

03_advanced_design 설계의 "Zero-LLM 지향 파이프라인(방안 B)"을 유지하면서, Vector DB와 Ontology DB 검색 효율을 극한으로 끌어올려 불가피한 LLM(Fallback) 호출 시의 입력 토큰마저 최소화하는 아키텍처의 구체적인 구현 방안을 다룹니다.

---

## 1. 아키텍처 개요 및 핵심 흐름

이 아키텍처의 목표는 **"가장 작은 비용으로 가장 정확한 컨텍스트(Context)를 조립하는 것"**입니다. 전체 흐름은 크게 오프라인 파이프라인(지식 구축)과 런타임 추론 파이프라인(스크립트 생성)으로 나뉩니다.

### 1-1. 전체 시스템 다이어그램

```mermaid
graph TD
    subgraph Offline["Offline Ingestion Layer (배치 처리)"]
        Spec["DBC/ARXML/사양서"] --> DB_Builder["DB Builder Pipeline"]
        DB_Builder -->|LLM 최초 1회| Context_Generator["Context Generator"]
        Context_Generator -->|context prefix 부착| VectorDB[("Contextual Vector DB")]
        DB_Builder --> OntologyDB[("Ontology DB")]
    end

    subgraph Runtime["Runtime Inference Layer (실시간 TC 변환)"]
        TC["자연어 TC Step 입력"] --> Retriever["Retriever Engine"]
        Retriever -->|Score > 0.75| VectorDB
        VectorDB -->|Match + prefix| Extractor["3-Tier Extractor"]
        
        Extractor -->|Tier 1, 2 성공| Assembler["Assembler"]
        Extractor -->|Tier 3 Fallback| SLM["경량 LLM (SLM)"]
        SLM --> Assembler
        
        Assembler -->|Top-5 Fuzzy Filter| OntologyDB
        OntologyDB -->|Alias 매칭| Validator["Validator"]
        OntologyDB -->|미매칭| SLM
        
        Validator -->|Syntax 통과| Output["최종 실행 코드"]
        Validator -->|Syntax 에러| ErrorCompressor["Error Context Compressor"]
        ErrorCompressor -->|±3줄 압축| SLM
        SLM --> Validator
    end
```

---

## 2. 모듈별 상세 설계 (구현 관점)

### 2.1. Offline: Contextual Indexer 설계 (DB 구축 레이어)

모든 검색의 정확도는 DB에 들어가는 데이터의 '품질'에 의해 결정됩니다. 단순 텍스트 임베딩을 넘어, **각 시그널과 템플릿의 문맥(Context)을 사전 생성하여 벡터화**합니다.

*   **컴포넌트**: `src/db/context_indexer.py` (신규 생성)
*   **동작 방식**: 
    1.  DBC 파일이나 템플릿 정의 JSON을 읽어들입니다.
    2.  각 템플릿/시그널에 대해 가장 저렴한 모델(gpt-4o-mini 등)을 사용하여 2~3문장의 요약(Context)을 생성합니다.
    3.  `context_prefix` 필드에 요약을 저장하고, 이를 포함한 텍스트로 임베딩을 수행합니다.

**Contextual Indexer 오프라인 배치 스크립트 예시**:
```python
def generate_context_prefix(template_def: dict, llm_client) -> str:
    """오프라인에서 템플릿의 의미와 제약사항을 LLM으로 미리 요약"""
    prompt = f"""
    아래 자동차 제어 템플릿 데이터를 보고 3문장 이내로 요약해라.
    1. 언제 이 액션을 쓰는가?
    2. 연관된 ECU나 물리 파츠는 무엇인가?
    [Data]: {template_def}
    """
    response = llm_client.invoke(prompt)
    return response.content

def build_contextual_index(source_jsons: list):
    for item in source_jsons:
        # LLM 호출은 인덱싱(초기화/업데이트) 시 1회만 발생 (런타임 비용 0)
        item["context_prefix"] = generate_context_prefix(item)
        
        # 임베딩 대상 문자열 = Context + 실제 타겟 소스
        item["vector_source"] = f"{item['context_prefix']}\n\n{item['vector_source']}"
        db.insert(item)
```

### 2.2. Runtime: Retriever 정밀 필터링 설계

Retriever는 단순히 유사한 항목을 가져오는 것을 넘어, 품질이 낮은 노이즈의 유입을 원천 차단해야 합니다. 

*   **컴포넌트**: `src/core/retriever.py` 
*   **핵심 로직**: `score_threshold` (임계값) 도입
    *   임베딩 모델(예: `all-MiniLM-L6-v2`)의 Cosine Similarity Score 기준, 유사도가 0.75 미만인 매칭 결과는 버립니다.
    *   만약 유효한 템플릿이 0개라면, `Template Rescue` 파이프라인(LLM Fallback)으로 즉시 라우팅합니다.

**Retriever Threshold 구현 예시**:
```python
def retrieve_templates(user_text: str, top_k=3, threshold=0.75):
    results = vector_db.query(user_text, top_k=top_k)
    valid_matches = []
    
    for item in results:
        # 유사도가 기준치 미달이면 노이즈로 간주하고 과감히 버림
        if item.score >= threshold:
            valid_matches.append(item)
            
    if not valid_matches:
        # 유효한 템플릿이 없는 경우 -> Rescue Flow (LLM) 시작
        return TemplateRescueEngine.run(user_text)
        
    return valid_matches
```

### 2.3. Runtime: Ontology Router의 Fuzzy Filtering 설계

Ontology Graph에 존재하는 수백 개의 Concept 노드를 LLM(Tier 3 또는 Alias 매칭용)에 전부 던지면 토큰 소모가 극심합니다. 이를 해결하기 위해 **전통적인 문자열 유사도 알고리즘(Levenshtein Distance 등)을 활용한 1차 필터링**을 수행합니다.

*   **컴포넌트**: `src/db/ontology_graph.py` 
*   **도입 알고리즘**: TheFuzz(구 FuzzyWuzzy)와 같이 가볍고 빠른 패키지 사용 (`pip install TheFuzz`)

**Fuzzy Filter 구현 로직**:
```python
from thefuzz import process

def find_ontology_candidates(unknown_alias: str, top_n=5) -> list[dict]:
    """모든 노드 중 이름이나 동의어가 가장 비슷한 N개만 추려냄 (비용 0)"""
    all_concepts = ontology_graph.get_all_concepts() # 수백 개 노드
    
    # 각 노드의 대표 이름과 synonyms 배열을 하나의 문자열 풀(Pool)로 구성
    search_pool = {node.id: node.get_searchable_text() for node in all_concepts}
    
    # 1차 고속 필터링 (Fuzzy String Match)
    top_matches = process.extract(unknown_alias, search_pool, limit=top_n)
    
    candidate_nodes = []
    for match_text, score, node_id in top_matches:
        candidate_nodes.append(ontology_graph.get_node(node_id))
        
    # 결과가 너무 엉뚱하면 빈 배열 반환
    return candidate_nodes
```
이 로직을 거친 후, `candidate_nodes` (Top-5) 정보만 LLM의 프롬프트에 주입하므로 토큰을 60% 이상 아낍니다.

### 2.4. Runtime: Error Compressor 설계 (Self-Correction Loop)

Validator 검증(ex: `ast.parse` 오류, 정의되지 않은 변수 참조 오류)에 실패하여 Self-Correction Loop를 가동해야 할 경우, 오류가 발생한 지점의 핵심 정보만 LLM에 넘깁니다.

*   **컴포넌트**: `src/core/validator.py`
*   **동작 방식**: 
    1.  Traceback 객체를 분석하여 실제 에러가 발생한 소스코드의 줄 번호(Line Number)를 추적.
    2.  전체 코드 50줄을 보내는 대신, 에러 발생 위치 `[Line-3 : Line+3]` 영역 파씽.
    3.  에러 로그의 끝단(Exception Type과 Message)만 1줄로 요약.

**Error Context Compressor 구현 예시**:
```python
def compress_error_context(code_str: str, error_line_num: int, error_msg: str) -> str:
    lines = code_str.split('\n')
    start_idx = max(0, error_line_num - 1 - 3)
    end_idx = min(len(lines), error_line_num - 1 + 4)
    
    compressed = "[오류 발생 주변 코드 (±3줄)]\n"
    for i in range(start_idx, end_idx):
        marker = ">>>>> " if i == (error_line_num - 1) else "      "
        compressed += f"{marker} L{i+1}: {lines[i]}\n"
        
    compressed += f"\n[핵심 에러 메시지]: {error_msg.split('\n')[-1]}"
    return compressed
```
에러 발생 시 이 `compressed` 텍스트만 Prompt에 추가합니다.

---

## 3. 데이터 및 워크플로우 명세

### 3.1. Vector DB JSON 스키마 (최종)

```json
{
  "id": "action_set_signal",
  "type": "ACTION",
  "context_prefix": "차량 제어 시그널의 상태값을 변경하는 할당 동작...", 
  "vector_source": "차량 제어 시그널의 상태값을 변경하는 할당 동작... {signal}를 {value}로 설정한다",
  "regex_pattern": "^.*?(?P<signal>.+?)(?:을|를)?\\s+(?P<value>.+?)(?:으로|로)?\\s+설정.*$",
  "variables": ["signal", "value"],
  "target_code": "simva.set_signal(signals.{ecu}.{signal}, \"{value}\")"
}
```
*   **주의**: 임베딩 엔진(ChromaDB 등) 추가 시점에는 `vector_source` 칼럼을 통째로 넘겨 임베딩 하되, 조회 결과로는 `regex_pattern`과 `target_code`만 뽑아 써야 합니다.

### 3.2. 런타임 변환 시퀀스 (통합 플로우)

1.  **Input**: `"좌측 헤드램프를 상향등으로 켜라"`
2.  **Retriever**: Vector DB 검색
    *   `context_prefix`의 도움으로 `action_set_signal` 템플릿과 매칭 완료 (`Score: 0.89` > `0.75`, 통과)
3.  **Extractor (Tier 1)**: Regex 실행
    *   `(?P<signal>좌측 헤드램프)`
    *   `(?P<value>상향등)`
    *   (성공. LLM 미사용, 비용 0)
4.  **Assembler (Ontology)**: Mapping
    *   `"좌측 헤드램프"` -> Graph에 정확한 이름 없음 -> **Fuzzy Filter & LLM 호출 (Tier 3)** 가동
    *   Fuzzy Filter: `[Left_HeadLamp, Right_HeadLamp, FogLamp, ...]` (Top 5 도출)
    *   LLM 프롬프트: `"사용자 입력 '좌측 헤드램프'는 후보 5개 중 무엇인가? -> Left_HeadLamp"` (최소 토큰 소모)
5.  **Assembler (Code)**: Slotting
    *   `simva.set_signal(signals.BCM.Left_HeadLamp, "HIGH")`  (_※ "상향등" 역시 Ontology를 거쳐 "HIGH"로 변환됨_)
6.  **Validator**:
    *   ast.parse() 검사 (정상). Self-Correction 미호출 (비용 0)
7.  **Output 발행**

---

## 4. 확장 계획: Pattern Cache Layer

비용 최적화의 극의(極意)는 **"아예 아무것도 검색하지 않는 것"**입니다.
차량 시스템 테스트의 특성상 동일한 제어 패턴(예: `ACC 켜기`, `속도 N 설정`)이 수십 개의 TC에서 반복 등장합니다.

*   `src/core/pattern_cache.py` (TTL(Time-To-Live) 적용된 LRU 캐시 메모리)
*   사용자의 원문 문장을 Key로, 최종 조립된 코드 스니펫(`ast` 구조)을 Value로 캐싱합니다.
*   Retriever 호출 전 최우선으로 검사하여 캐시 히트(Cache Hit) 시 1~6단계를 모두 패스합니다. 발생 비용 0.

## 5. 결론 및 다음 단계

위 아키텍처는 이론상 TC 문장의 90% 이상을 **로컬 연산 자원만으로 밀리초(ms) 단위 처리**하며, 불가피한 10%의 예외 케이스 처리 시에도 기존 Full Context 방식 대비 **약 30~40% 수준의 API 토큰만 요구**하는 시스템입니다.

**구현 우선순위 (Action Item)**:
1.  `rag_cost_optimization_strategy.md`에 명시된 Vector DB 스키마 업데이트 (`context_prefix` 등) 보강 작업.
2.  `src/core/retriever.py` 내 `score_threshold` (0.75 초안) 도입 및 노이즈 필터링 검증.
3.  Ontology 모듈 내 `TheFuzz` 기반 Fuzzy 사전 필터링 로직 도입.
4.  Validator 내 에러 컴프레서(Error Context Compressor) 모듈 추가 구현.

# Contextual RAG — Vector DB 상세 설계서

본 문서는 방안 C (Contextual RAG) 아키텍처에서 사용되는 **Vector DB의 스키마 구조, 컬렉션 설계, Contextual Indexing 전략, 검색 파이프라인**을 상세히 정의합니다.

> 참조: [01_architecture.md](./01_architecture.md) §2.1~2.2, [03_ontology_db_design.md](./03_ontology_db_design.md)

---

## 1. 역할 및 설계 원칙

Vector DB는 이 아키텍처에서 **"문법과 뼈대를 담당하는 건축가"** 역할을 수행합니다.

| 역할 | 설명 |
| :--- | :--- |
| **템플릿 검색** | 자연어 TC 문장과 의미적으로 가장 유사한 코드 뼈대(Template)를 Cosine Similarity로 탐색 |
| **변수 추출 지원** | 매칭된 템플릿에 포함된 `regex_pattern`을 사용해 Tier 1 추출 즉시 수행 |
| **코드 조립 제공** | 추출된 변수를 채워 넣을 `target_code` 뼈대 반환 |
| **패턴 구조 판별** | Action / If-Else / Loop 등 문장의 제어 구조 유형(Type) 분류 |

### 핵심 설계 원칙

> [!IMPORTANT]
> 방안 C의 핵심인 **Contextual Indexing**을 적용합니다. 단순 텍스트 임베딩 대신 각 템플릿의 의미·용도·제약을 사전 요약한 `context_prefix`를 임베딩에 포함시켜, 은어·축약어·어순 변형에도 높은 검색 정확도를 확보합니다.

---

## 2. 컬렉션(Collection) 구조

타겟 실행 환경별로 **물리적으로 분리된 컬렉션**을 사용합니다. 하나의 컬렉션 안에 `target` 필드로 구분하지 않으며, 컬렉션 자체가 타겟을 격리합니다.

```
ChromaDB
├── Collection: simva_templates      ← SIMVA 환경 코드 템플릿
├── Collection: capl_templates       ← CAPL 환경 코드 템플릿
└── Collection: (추후 확장)           ← 신규 타겟 환경 추가 시 컬렉션 신규 생성
```

---

## 3. 레코드(Document) 스키마 상세

### 3.1. 전체 필드 정의

| 필드명 | 타입 | 저장 위치 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | String | ChromaDB ID | 템플릿 고유 식별자 (예: `action_set_signal`) |
| `context_prefix` | String | Metadata | 🆕 **Contextual RAG 핵심**: LLM이 사전 생성한 템플릿 맥락 요약 |
| `vector_source` | String | Document (임베딩 원본) | `context_prefix + "\n\n" + type_source`의 조합 텍스트 |
| `type_source` | String | Metadata | 사람이 작성한 자연어 대표 문장 (예: `"{signal}를 {value}로 설정한다"`) |
| `type` | Enum | Metadata | 템플릿 구조 유형 (`ACTION`, `META_CONTROL_IFELSE`, `META_CONTROL_LOOP`, `TYPE_INIT`, `TYPE_WAIT`, `TYPE_CHECK`) |
| `regex_pattern` | String | Metadata | 변수 추출(Tier 1)용 Named Group 정규식 |
| `variables` | JSON String | Metadata | 필요한 변수 이름 배열 (예: `["signal","value"]`, JSON 직렬화 저장) |
| `target_code` | String | Metadata | 최종 조립될 코드 뼈대 (예: `simva.set_signal(signals.{ecu}.{signal}, "{value}")`) |

> [!NOTE]
> ChromaDB의 `metadata`는 중첩 딕셔너리를 지원하지 않습니다. 배열 타입은 `JSON.dumps()`로 직렬화하여 String으로 저장하고, 조회 시 역직렬화합니다.

### 3.2. 타입별 샘플 레코드

#### ACTION 타입 (단순 값 할당)

```json
{
  "id": "action_set_signal",
  "context_prefix": "차량 내 특정 ECU 신호의 상태값을 새로운 값으로 변경하는 할당 동작. 도어 잠금, 와이퍼, 램프, 시트 등 모든 제어 시그널에 적용 가능하며, if/loop 내부 하위 액션으로도 빈번히 중첩 사용됨.",
  "vector_source": "차량 내 특정 ECU 신호의 상태값을 새로운 값으로 변경하는 할당 동작...\n\n{signal}를 {value}로 설정한다",
  "type_source": "{signal}를 {value}로 설정한다",
  "type": "ACTION",
  "regex_pattern": "^.*?(?P<signal>[a-zA-Z가-힣0-9_\\s]+?)(?:을|를|은|는)?\\s+(?P<value>[a-zA-Z0-9가-힣_\\s\\.]+?)(?:으로|로|에)?\\s+(?:설정|세팅|변경|바꿔|켜|꺼).*$",
  "variables": "[\"signal\", \"value\"]",
  "target_code": "simva.set_signal(signals.{ecu}.{signal}, \"{value}\")"
}
```

#### TYPE_WAIT 타입 (대기)

```json
{
  "id": "action_wait_seconds",
  "context_prefix": "설정된 시간(초 단위)만큼 테스트 실행을 일시 중지하는 대기 동작. 상태 변화 확인 전 안정화 시간을 부여하거나, 이벤트 간 간격을 제어할 때 사용됨.",
  "vector_source": "설정된 시간만큼 테스트 실행을 일시 중지하는 대기 동작...\n\n{duration}초 대기한다",
  "type_source": "{duration}초 대기한다",
  "type": "TYPE_WAIT",
  "regex_pattern": "^.*?(?P<duration>[0-9]+(?:\\.[0-9]+)?)\\s*초?\\s+(?:대기|기다|wait).*$",
  "variables": "[\"duration\"]",
  "target_code": "simva.wait({duration})"
}
```

#### TYPE_CHECK 타입 (상태 확인)

```json
{
  "id": "check_signal_eq",
  "context_prefix": "특정 시그널의 현재 값이 기대값과 일치하는지 확인하는 판정 동작. 테스트의 Pass/Fail 기준을 결정하며, Expected Result 컬럼에서 주로 사용됨.",
  "vector_source": "특정 시그널의 현재 값이 기대값과 일치하는지 확인하는 판정 동작...\n\n{signal}이 {value}이어야 한다",
  "type_source": "{signal}이 {value}이어야 한다",
  "type": "TYPE_CHECK",
  "regex_pattern": "^.*?(?P<signal>[a-zA-Z가-힣0-9_\\s]+?)(?:이|가|은|는)?\\s+(?P<value>[a-zA-Z0-9가-힣_\\s\\.]+?)(?:이어야|여야|이|가)\\s+(?:한다|됩니다|됨).*$",
  "variables": "[\"signal\", \"value\"]",
  "target_code": "result = simva.is_eq(signals.{ecu}.{signal}, \"{value}\")"
}
```

#### META_CONTROL_IFELSE 타입 (조건문 뼈대)

```json
{
  "id": "meta_condition_ifelse",
  "context_prefix": "조건에 따라 두 가지 동작 중 하나를 선택 실행하는 분기 제어 구조. '~이면 ~한다. 그렇지 않으면 ~한다' 패턴을 가진 복합 문장에 사용되며, 내부 조건식과 각 액션은 재귀적으로 별도 파싱됨.",
  "vector_source": "조건에 따라 두 가지 동작 중 하나를 선택 실행하는 분기 제어 구조...\n\n{condition}이면 {true_action}한다. 그렇지 않으면 {false_action}한다.",
  "type_source": "{condition}이면 {true_action}한다. 그렇지 않으면 {false_action}한다.",
  "type": "META_CONTROL_IFELSE",
  "regex_pattern": "^(?P<condition>.+?)(?:이?면|인\\s*경우)\\s+(?P<true_action>.+?)(?:한다)[\\.\\s]*(?:그렇지\\s*않으면)\\s+(?P<false_action>.+?)(?:한다)$",
  "variables": "[\"condition\", \"true_action\", \"false_action\"]",
  "target_code": "if {condition}:\n    {true_action}\nelse:\n    {false_action}"
}
```

#### META_CONTROL_LOOP 타입 (반복문 뼈대)

```json
{
  "id": "meta_control_loop",
  "context_prefix": "지정된 횟수만큼 동일한 동작을 반복 실행하는 루프 제어 구조. '~N번 반복한다' 패턴 문장에 적용되며, 내부 반복 액션은 재귀적으로 별도 파싱됨.",
  "vector_source": "지정된 횟수만큼 동일한 동작을 반복 실행하는 루프 제어 구조...\n\n{action}동작을 {count}번 반복한다.",
  "type_source": "{action}동작을 {count}번 반복한다.",
  "type": "META_CONTROL_LOOP",
  "regex_pattern": "^(?P<action>.+?)(?:\\s*동작을?)?\\s+(?P<count>[0-9]+)(?:번|회)\\s+반복.*$",
  "variables": "[\"count\", \"action\"]",
  "target_code": "for i in range({count}):\n    {action}"
}
```

---

## 4. Contextual Indexing 파이프라인 (오프라인)

### 4.1. 실행 흐름

```
scripts/build_vector_db.py 실행 (최초 1회 또는 템플릿 변경 시)
        │
        ▼
1. source_templates/*.json 파일 로드 (사람이 작성한 raw 템플릿)
        │
        ▼
2. 각 템플릿에 context_prefix 생성 (LLM 호출, gpt-4o-mini 권장)
   → 비용: 템플릿 1개당 ~200 input tokens + ~100 output tokens
   → 예: 템플릿 100개 × 300 tok = 30,000 tok ≈ $0.006 (일회성)
        │
        ▼
3. vector_source = context_prefix + "\n\n" + type_source 조합
        │
        ▼
4. ChromaDB에 upsert (임베딩 자동 생성 by all-MiniLM-L6-v2)
        │
        ▼
5. 완료 리포트: "총 N개 템플릿 인덱싱 완료"
```

### 4.2. Context 생성용 LLM 프롬프트 (gpt-4o-mini)

```text
[System]
당신은 자동차 소프트웨어 테스트 자동화 시스템의 "템플릿 맥락 요약기"입니다.

[User]
아래 코드 생성 템플릿 정보를 보고, 이 템플릿이 언제 사용되는지,
어떤 유형의 문장에 매칭되는지, 주의사항은 무엇인지를 3문장 이내로 요약하시오.
요약은 임베딩 검색에 활용되므로, 관련 동의어와 용도 설명을 풍부하게 포함하시오.

[Template Data]
id: {id}
type_source: {type_source}
target_code: {target_code}
type: {type}
```

---

## 5. 런타임 검색(Query) 파이프라인

### 5.1. 검색 흐름 (Precision RAG)

```python
def retrieve_templates(user_text: str, collection: str = "simva_templates"):
    """
    입력 문장에 대해 Contextual Vector DB에서 정밀 검색 수행.
    
    Returns:
        list[TemplateMatch]: 유사도 임계값 통과 템플릿 목록
    """
    # 1. 임베딩 모델로 입력 문장을 벡터화
    query_embedding = embedding_model.encode(user_text)
    
    # 2. Vector DB 쿼리 (top_k=3만 검색)
    raw_results = chroma_client.get_collection(collection).query(
        query_embeddings=[query_embedding],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )
    
    # 3. Score Threshold 필터링 (Cosine Similarity 기준 0.75 미만 제거)
    #    ChromaDB distance 기준: distance = 1 - cosine_similarity
    #    → distance < 0.25 인 것만 허용 (= similarity > 0.75)
    valid_matches = []
    for i, distance in enumerate(raw_results["distances"][0]):
        similarity = 1 - distance
        if similarity >= 0.75:
            valid_matches.append(TemplateMatch(
                id=raw_results["ids"][0][i],
                similarity=similarity,
                type=raw_results["metadatas"][0][i]["type"],
                regex_pattern=raw_results["metadatas"][0][i]["regex_pattern"],
                variables=json.loads(raw_results["metadatas"][0][i]["variables"]),
                target_code=raw_results["metadatas"][0][i]["target_code"]
            ))
    
    # 4. 유효 결과 없음 → Template Rescue Engine (LLM Fallback) 라우팅
    if not valid_matches:
        return TemplateRescueEngine.run(user_text)
    
    # 5. 유사도 기준 내림차순 정렬 후 반환
    return sorted(valid_matches, key=lambda m: m.similarity, reverse=True)
```

### 5.2. 검색 결과 활용 흐름

```
Retriever 반환값 (TemplateMatch)
        │
        ├─ type == "ACTION"             → Extractor로 직접 전달 (Tier 1 Regex 시도)
        │
        ├─ type == "META_CONTROL_*"     → Extractor가 구조 변수(condition, action 등) 추출
        │                                   → 추출된 변수들을 재귀적으로 다시 retrieve_templates() 호출
        │
        └─ type == "TYPE_CHECK"         → is_expected_result=True 컨텍스트 플래그 설정 후 처리
```

---

## 6. 스키마 확장 가이드 (신규 템플릿 추가)

### 6.1. 신규 템플릿 추가 절차

1. `source_templates/simva_templates.json`에 raw 레코드 추가 (`context_prefix` 없이)
2. `scripts/build_vector_db.py --update` 실행
3. 시스템이 신규 레코드에 한해 LLM으로 `context_prefix` 자동 생성
4. ChromaDB에 upsert 및 즉시 반영 (Hot Reload)

### 6.2. 타겟 환경 추가 (예: CAPL 환경)

1. `source_templates/capl_templates.json` 파일 신규 생성
2. 동일 `id`, 동일 `type_source`에 CAPL 전용 `target_code` 작성
3. `build_vector_db.py --collection capl_templates` 실행
4. 엔진에서 `CoreEngine(collection="capl_templates")`로 초기화

---

## 7. 저장 용량 및 성능 추정

| 항목 | 추정치 | 비고 |
| :--- | :--- | :--- |
| 기본 템플릿 수 | ~50~200개 | ACTION 30 + META 10 + CHECK 20 + INIT 10 |
| 임베딩 벡터 크기 | 384 float32 = 1.5 KB/레코드 | `all-MiniLM-L6-v2` 기준 |
| 전체 Vector DB 용량 | **~300 KB** (200개 기준) | ChromaDB 로컬 파일 |
| 검색 레이턴시 | **< 5 ms** | 200개 이하, 로컬 환경 |
| 인덱싱 비용 (최초 1회) | **$0.006** | 200개 × 300 tok × gpt-4o-mini |

> [!TIP]
> Vector DB는 크기가 매우 작아 영구 디스크 저장 후 Git에서 관리 가능합니다. 단, `data/vector_db_storage/`는 이진(Binary) 파일이므로 `.gitignore`에 추가 후 별도 백업 전략을 수립하거나, `source_templates/*.json`만 Git에 관리하고 배포 시 재인덱싱하는 방식을 권장합니다.

---

## 8. 시스템 파일 구조

```
project/
├── source_templates/                  ← 사람이 관리하는 원본 템플릿 (Git 관리 대상 ✅)
│   ├── simva_templates.json           ← SIMVA 환경 Raw 템플릿
│   └── capl_templates.json            ← CAPL 환경 Raw 템플릿 (추후)
├── data/
│   └── vector_db_storage/             ← ChromaDB 로컬 파일 (.gitignore 권장)
│       ├── simva_templates/
│       └── chroma.sqlite3
└── scripts/
    └── build_vector_db.py             ← Contextual Indexing 배치 스크립트
```

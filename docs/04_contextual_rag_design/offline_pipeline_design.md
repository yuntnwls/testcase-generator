# Offline Pipeline 설계 (Contextual Indexer & DB Builder)

본 문서는 방안 C 아키텍처에서 런타임 성능과 검색 정확도를 높이기 위해 백그라운드에서 실행되는 **오프라인 데이터 구축 파이프라인(Offline Pipeline)**의 상세 설계를 다룹니다.

*   **컴포넌트**: `scripts/build_vector_db.py`, `scripts/build_ontology.py`
*   **관련 문서**: [architecture.md](architecture.md) | [vector_db_design.md](db/vector_db_design.md)

---

## 1. 개요: 런타임 최적화의 첫 단추

방안 C의 철학은 **"비싼 연산은 오프라인에서 1회만, 런타임은 빠르고 결정론적으로"** 입니다.
오프라인 파이프라인은 텍스트 템플릿과 차량 스펙 DB를 읽어들여, 검색에 최적화된 Vector DB와 지식 매핑용 Ontology DB를 사전에 구축합니다.

---

## 2. Contextual Indexer (Vector DB 구축)

단순 문자열 매칭의 한계를 극복하기 위해, 템플릿의 **문맥(Context)을 사전 생성하여 임베딩 공간의 품질을 높이는 작업**입니다.

### 2.1. 전체 흐름

1.  **JSON 데이터 파싱**: `vector_db_sample.json` 등에서 템플릿 기본 정의(`id`, `type_source`, `target_code`)를 읽습니다.
2.  **LLM Context Prefix 생성**: 각 템플릿에 대해 저렴한 모델(`gpt-4o-mini`)을 1회 호출하여 `context_prefix` 필드를 생성합니다.
3.  **Vector Source 조합**: 생성된 `context_prefix`와 `type_source`를 합쳐 검색 대상 문자열인 `vector_source`를 만듭니다.
4.  **임베딩 생성 및 ChromaDB 저장**: `vector_source`를 HuggingFace 모델(`all-MiniLM-L6-v2`)로 임베딩한 후, 결과를 ChromaDB `simva_templates` 컬렉션에 저장합니다.

### 2.2. Context Prefix 자동 생성 프롬프트

> [prompt_engineering_guide.md §3](prompt_engineering_guide.md#3-오프라인-전용--contextual-indexer-프롬프트)에 공식 정의되어 있습니다.

의미론적 유사도(Semantic Similarity) 검색 시, `"와이퍼 작동"`과 `"simva.set_signal(signals.BCM.Wiper_State, ON)"` 사이의 간극을 LLM이 텍스트로 미리 채워 검색율을 비약적으로 높입니다. 총 예상 비용은 200개 템플릿 기준 1달러 미만(1회성)입니다.

---

## 3. Ontology DB Builder 로직

신호명이 일치하지 않는 현장 은어나 자연어 표현을 정식 ECU 시그널로 엮기 위한 **지식 그래프(NeworkX + JSON)** 구축 파이프라인입니다.

### 3.1. 원본 데이터 (DBC / ARXML / 엑셀 스펙) -> Graph

신차 개발 프로젝트가 시작되면, 차량의 CAN 통신 명세서(DBC 파일)나 시스템 아키텍처 문서(ARXML)가 제공됩니다.

1.  **Signal Parser**: DBC 파일의 `SG_` (시그널 정의) 또는 `BO_` (메시지 정의) 블록을 파싱합니다.
2.  **Concept 매핑 규칙 적용**: `BCM_`으로 시작하면 `Body Control Module` 분류 노드에 연결하고, `WIP_`가 포함되어 있으면 `지능형 와이퍼` 관련 Concept 노드와 Edge를 맺습니다.
3.  **Synonym Dictionary 병합**: 과거 프로젝트에서 테스트 엔지니어들이 썼던 은어 사전(`synonyms.csv`)을 로드하여 각 Concept 노드의 `synonyms` 리스트에 합칩니다.

### 3.2. 증분 업데이트 및 무효화(Invalidation) 대응

`scripts/build_vector_db.py` 혹은 `build_ontology.py`가 재실행되어 **기존 템플릿이나 신호명 정보가 업데이트된 경우**, 런타임 시스템은 이를 인지하고 조치를 취해야 합니다.

1.  **Pattern Cache Clear (Template Invalidation)**: Vector DB의 템플릿 ID (예: `action_set_signal`)가 변경되거나 대상 코드가 수정되면, 해당 ID로 렌더링되어 있던 인메모리 `Pattern Cache` 엔트리를 즉각 삭제(무효화)합니다.
    *   (`pattern_cache_design.md`의 최하단 무효화 전략 참조)
2.  **Graph Reload**: 메모리에 로드되어 있던 NetworkX 그래프 인스턴스를 새 JSON 데이터로 교체합니다.

> **작업 트리거**: 이 과정은 평상시에 동작하는 것이 아니라, CI/CD 파이프라인에서 신규 스펙이 Push 되거나, 관리자가 Admin UI에서 "DB 동기화" 버튼을 눌렀을 때만 트리거됩니다.

# Direct Synthesis 아키텍처

본 폴더는 `docs/02_design`의 초기 설계를 대체하는 **2세대 고도화 설계** 문서를 담고 있습니다. 핵심 철학은 **"IR 없이, LLM 없이, 데이터에서 직접 코드를 합성한다"(Direct Synthesis from Data)**입니다.

> 이 폴더의 설계는 현행 구현의 기반이며, `docs/04_contextual_rag_design`(Contextual RAG)에서 더욱 정밀하게 보강됩니다.

---

## 📂 문서 목록

### 핵심 아키텍처

| 문서 | 한줄 요약 |
| :--- | :--- |
| [architecture_design.md](./architecture_design.md) | **전체 아키텍처 설계서 (핵심 문서)**. Vector DB 기반 Direct Synthesis 파이프라인 정의. Retriever → Extractor(3-Tier) → Assembler → Validator 구조. "No Intermediate Objects, Scale by Knowledge" 원칙 |
| [tc_script_generation_strategy.md](./tc_script_generation_strategy.md) | TC 4대 컴포넌트(초기화·사전조건·시험방법·판정조건) 분석 및 전체 스크립트 생성 전략. 컬럼별 Vector DB 타입 필터링, 값 정규화 3단계 파이프라인(Spec Match → Alias → LLM) |
| [execution_sequence.md](./execution_sequence.md) | 방안 B의 런타임 실행 시퀀스 다이어그램. TC Step 1건 처리 흐름: Cache → Retriever → Extractor Tier 1/2/3 → Assembler → Validator |
| [implementation_spec.md](./implementation_spec.md) | 주요 모듈의 Python 클래스/함수 구현 명세. `TemplateRetriever`, `TierExtractor`, `OntologyAssembler`, `CodeValidator` 인터페이스 정의 |
| [advanced_performance_and_fallback.md](./advanced_performance_and_fallback.md) | 성능 목표 및 Fallback 시나리오 설계. Tier 1→2→3 단계별 실패 처리, Template Rescue, Approval Queue 동작 |

### 프롬프트 및 UI

| 문서 | 한줄 요약 |
| :--- | :--- |
| [prompt_engineering_guide.md](./prompt_engineering_guide.md) | LLM이 호출되는 4개 지점의 공식 프롬프트 템플릿. Extractor Tier 3(변수 추출), Ontology Router(은어 번역), Self-Correction(코드 교정), Template Rescue(패턴 추론) |
| [ui_proposal.md](./ui_proposal.md) | No-Code Template Builder UI, Ontology 편집기, 실시간 변환 모니터링 화면 상세 제안. 와이어프레임 및 컴포넌트 설명 |

### `db/` 서브폴더 — DB 스키마 및 예시 데이터

| 파일 | 한줄 요약 |
| :--- | :--- |
| [db/vector_db_schema.md](./db/vector_db_schema.md) | Vector DB 레코드 스키마 정의. 필드 구성(`id`, `type_source`, `regex_pattern`, `target_code` 등), 컬렉션 분리 전략, 검색 코드 예시 |
| [db/ontology_db_schema.md](./db/ontology_db_schema.md) | Ontology 지식 그래프 스키마 정의. 시그널 노드 구조, 동의어(Alias) 매핑, 선행 조건(Pre-condition) 연결 |
| [db/sample_simva_collection.json](./db/sample_simva_collection.json) | SIMVA 환경 Vector DB 샘플 레코드 (JSON). 실제 등록 가능한 템플릿 예시 |
| [db/sample_ontology_graph.json](./db/sample_ontology_graph.json) | Ontology DB 샘플 그래프 데이터 (JSON). 시그널-차종-값 연결 관계 예시 |

---

## 🏗️ 아키텍처 핵심 흐름

> 🔴 **LLM 호출** (생성형, 고비용) | ⚡ **Embedding 모델** (저비용) | ✅ **결정론적 처리** (비용 0)

```mermaid
graph LR
    TC["자연어 TC Step"] --> Cache{"✅ Pattern Cache<br/>조회"}
    Cache -->|"히트"| Out["실행 코드"]
    Cache -->|"미스"| Ret["⚡ Retriever<br/>Vector DB 검색"]

    Ret -->|"score < 0.6"| Rescue["🔴 Template Rescue<br/>패턴 추론 LLM<br/>~550 tok, ~3% 빈도"]
    Rescue --> UI["관리자 UI<br/>초안 등록"]

    Ret -->|"매칭 성공"| T1["✅ Tier 1: Regex<br/>Named Capture<br/>100% 정확"]
    T1 -->|"실패"| T2["✅ Tier 2: Alignment<br/>LCS 문자열 차분<br/>~95% 정확"]
    T2 -->|"실패"| T3["🔴 Tier 3: SLM Fallback<br/>변수 추출 LLM<br/>~600 tok, ~10% 빈도"]

    T1 & T2 & T3 --> Asm["✅ Graph Traversal<br/>Ontology 매핑"]

    Asm -->|"Alias 미등록"| OntLLM["🔴 Ontology Router LLM<br/>전체 후보 목록 전달<br/>~800 tok, ~5% 빈도"]
    OntLLM --> Assemble["✅ Assembler<br/>코드 조립"]
    Asm -->|"매칭 성공"| Assemble

    Assemble --> Val["✅ Validator<br/>ast.parse()"]
    Val -->|"통과"| Out
    Val -->|"실패"| SCorrLLM["🔴 Self-Correction LLM<br/>전체 코드+Traceback 전송<br/>~1,500 tok, ~15% 빈도"]
    SCorrLLM --> Val
```

### LLM 호출 지점 요약

| 위치 | 호출 빈도 | 비용/호출 | 역할 |
| :--- | :---: | :---: | :--- |
| 🔴 Tier 3 SLM Fallback | ~10% Step | ~600 tok | Regex·Alignment 실패 시 변수 추출 |
| 🔴 Ontology Router | ~5% Step | ~800 tok | Alias 미등록 시 전체 후보 목록 전달해 매핑 |
| 🔴 Self-Correction | ~15% Step | ~1,500 tok | ast.parse() 실패 시 전체 코드+Traceback 재전송 |
| 🔴 Template Rescue | ~3% Step | ~550 tok | score < 0.6 미등록 패턴 추론 |
| ⚡ Retriever Embedding | 100% Step | ~0.03 tok | Vector DB 검색 (저비용, 항상 실행) |

> ✅ **핵심 성과**: Step 1개당 LLM 호출 확률 **~20%**, 평균 약 170 tok. TC 100건 기준 **132,000 tok (방안 A 대비 94.3% 절감)**, 변환 성공률 ~88~91%.
> 방안 B → C 추가 보강 사항은 `docs/04_contextual_rag_design` 참조.



## 📊 방안 B 핵심 성과 (방안 A 대비)

| 지표 | 방안 A (현재) | 방안 B (본 폴더) |
| :--- | :---: | :---: |
| LLM 호출률 | 100%/Step | ~20%/Step |
| 토큰 비용 (100 TC) | 2,310K tok | 132K tok (**94.3% 절감**) |
| Step 변환 성공률 | ~65~70% | ~88~91% |

> 방안 B에서 C로의 추가 보강 → `docs/04_contextual_rag_design` 참조

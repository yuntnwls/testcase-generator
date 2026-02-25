# 테스트 스크립트 자동화 솔루션

> **학습 목적 프로젝트** — LLM과 RAG를 실전에 적용하며, 가장 높은 정확도와 가장 낮은 비용을 동시에 달성하는 최적 아키텍처를 직접 설계하고 탐구합니다.

자연어로 작성된 테스트 케이스(TC) 정의서(엑셀)를 **SIMVA / CAPL 등의 실행 가능한 테스트 스크립트**로 자동 변환하는 시스템입니다.

---

## 🎯 왜 이 프로젝트를 만들었나?

차량 소프트웨어 테스트 엔지니어가 매번 수작업으로 작성하는 테스트 스크립트를, 자연어 TC 정의서로부터 자동 생성하는 솔루션을 LLM·RAG 기술로 구현합니다.

단순 구현에 그치지 않고, 아래 두 가지 핵심 질문에 대한 답을 직접 설계·비교하며 찾아갑니다.

> - **"LLM을 어느 지점에 써야 가장 정확한가?"**
> - **"비용을 최소화하면서 정확도를 극대화할 수 있는 아키텍처는 무엇인가?"**

---

## 🏗️ 3가지 설계 방안 비교

이 프로젝트는 같은 문제를 3가지 아키텍처로 설계하며 비교합니다.

### 방안 A — Every-Step LLM (현재 구현)

```
자연어 TC Step
    → [RAG 검색] → [🔴 LLM으로 IR JSON 생성] → [🔴 LLM으로 코드 생성] → 스크립트
```

**핵심 아이디어**: 모든 처리를 LLM에 위임합니다. LLM이 RAG로 검색된 시그널·규칙 전체를 CONTEXT로 받아 직접 코드를 작성합니다.

| 항목 | 내용 |
| :--- | :--- |
| **LLM 호출 빈도** | 매 Step **100%** 필수 호출 |
| **토큰 비용 (100 TC)** | ~2,310,000 tok |
| **Step 변환 성공률** | ~65~70% |
| **주요 문제** | 환각(Hallucination), IR JSON 포맷 오류, 비결정적 응답 |

---

### 방안 B — Direct Synthesis (3-Tier Extractor)

```
자연어 TC Step
    → [⚡ Vector DB 검색] → [✅ Regex / Alignment / 🔴 SLM] → [✅ Graph Traversal] → [조립] → 스크립트
```

**핵심 아이디어**: LLM보다 신뢰할 수 있는 결정론적 방법(정규식, 그래프 순회)을 먼저 시도하고, 실패한 소수 케이스에만 LLM(SLM)을 Fallback으로 씁니다.

| 항목 | 내용 |
| :--- | :--- |
| **LLM 호출 빈도** | ~20% Step (Fallback만) |
| **토큰 비용 (100 TC)** | ~132,000 tok (**방안 A 대비 94% 절감**) |
| **Step 변환 성공률** | ~88~91% |
| **핵심 개선** | Regex Named Capture(100% 정확) + Graph Traversal(결정론적) |

---

### 방안 C — Contextual RAG (현재 설계 목표)

```
자연어 TC Step
    → [⚡ Contextual Vector DB] → [✅ Regex / Alignment / 🔴 SLM(5%)] → [✅ Fuzzy+Graph / 🔴 LLM(3%)] → [조립] → [✅ Error Compressor → 🔴 Self-Correction(10%)] → 스크립트
```

**핵심 아이디어**: 방안 B의 각 Fallback 경로를 더 정밀하게 만들어 LLM 개입 자체를 더 줄이고, 진입했을 때도 더 좋은 정보를 제공합니다.

| 항목 | 내용 |
| :--- | :--- |
| **LLM 호출 빈도** | ~12% Step |
| **토큰 비용 (100 TC)** | ~67,200 tok (**방안 A 대비 97% 절감**) |
| **Step 변환 성공률** | ~93~96% |
| **핵심 개선** | `context_prefix`로 검색 정확도↑, Fuzzy Top-5로 LLM 후보 압축, Error Compressor로 Self-Correction 집중도↑ |

---

## 🏗️ 3가지 방안 종합 비교

```
변환 정확도
    ↑
96% │                                         ● 방안 C (Contextual RAG)
    │
91% │                    ● 방안 B (Direct Synthesis)
    │
70% │  ● 방안 A (현재 구현, Every-Step LLM)
    └──────────────────────────────────────── 비용(토큰) →
       2,310K              132K              67K
```

| 지표 | 방안 A | 방안 B | 방안 C |
| :--- | :---: | :---: | :---: |
| TC 100건 토큰 비용 | 2,310K | 132K | 67K |
| 방안 A 대비 절감율 | — | **94%↓** | **97%↓** |
| Step 변환 성공률 | ~65~70% | ~88~91% | ~93~96% |
| 환각(Hallucination) | ❌ 빈번 | ✅ 드묾 | ✅✅ 최소 |
| 미등록 패턴 처리 | ✅ LLM 유연성 | ⚠️ Template Rescue | ✅ 맥락 임베딩으로 개선 |

> **핵심 인사이트**: 비용을 줄이면 정확도가 낮아진다는 통념과 반대로, 방안 B·C는 **LLM을 결정론적 방법으로 교체**함으로써 비용도 낮추고 정확도도 높입니다. LLM의 역할을 "모든 것"에서 "결정론적 방법이 실패한 소수 케이스"로 좁힐수록 시스템은 더 안정적이고 비용효율적이 됩니다.

---

## 🏭 상업용 솔루션이라면 이렇게 설계되어야 한다

이 학습 프로젝트를 통해 도출한 상업용 설계 원칙:

### 1. LLM은 최후의 수단으로

모든 처리를 LLM에 위임하는 방안 A는 높은 운영 비용과 비결정적 동작으로 프로덕션에 부적합합니다. **정규식, 규칙 엔진, 그래프 순회 등 결정론적 처리를 최우선**으로 설계하고, LLM은 이것들이 모두 실패했을 때의 안전망으로 사용해야 합니다.

### 2. 지식은 코드가 아닌 데이터로 관리

템플릿, 시그널 매핑, 온톨로지를 DB에 저장하면 새로운 환경(차종, 도구)을 추가할 때 코드 수정 없이 DB 갱신만으로 확장할 수 있습니다. **"Scale by Knowledge, not by Code"** 원칙이 유지보수성을 결정합니다.

### 3. Contextual Indexing으로 검색 품질 확보

단순 임베딩 검색은 은어·축약어에 취약합니다. 템플릿마다 LLM이 사전 생성한 `context_prefix`를 포함해 인덱싱하면, 런타임에 LLM 없이도 높은 검색 정확도를 유지할 수 있습니다. **오프라인 1회성 비용으로 런타임 품질을 영구히 향상**시킵니다.

### 4. Fallback 계층화 + 비용 압축

LLM Fallback이 불가피한 경로에서는, 전체 컨텍스트를 그대로 주는 대신 **필요한 최소 정보만 압축해서 전달**합니다 (Fuzzy Top-5, Error Compressor). LLM 호출 1회당 토큰을 줄이는 것이 호출 횟수를 줄이는 것만큼 중요합니다.

### 5. 자가 학습 루프로 지속 개선

LLM이 처리한 새 패턴(Alias, Template)을 승인 후 DB에 영구 추가하면, 시간이 지날수록 Fallback 빈도가 줄어들고 시스템이 점점 더 스스로 처리할 수 있는 범위가 넓어집니다.

---

## 🛠 기술 스택

| 영역 | 기술 |
| :--- | :--- |
| **언어** | Python 3.9+ |
| **LLM** | OpenAI GPT-4o / gpt-4o-mini, Ollama (로컬) |
| **Vector DB** | ChromaDB + all-MiniLM-L6-v2 (Embedding) |
| **Ontology DB** | JSON + NetworkX (→ 규모 증가 시 Neo4j) |
| **Frontend** | Streamlit |
| **데이터 처리** | Pandas, re (정규식) |

---

## � 설계 문서 구조

| 폴더 | 내용 | 상태 |
| :--- | :--- | :---: |
| [docs/01_analysis](./docs/01_analysis/) | 자연어 TC 특성 분석, 요구사항 도출 | ✅ 완료 |
| [docs/02_design](./docs/02_design/) | 방안 A — IR 기반 1세대 설계 | ✅ 완료 |
| [docs/03_advanced_design](./docs/03_advanced_design/) | 방안 B — Direct Synthesis 고도화 설계 | ✅ 완료 |
| [docs/04_contextual_rag_design](./docs/04_contextual_rag_design/) | 방안 C — Contextual RAG 최종 설계 | 📝 설계 중 |

---

## 📂 프로젝트 구조

```
TestscriptGenerator/
├── data/               # 샘플 TC, Signal.cfg, RAG DB 소스 원천 데이터
├── docs/               # 설계 문서 (위 표 참조)
│   ├── 01_analysis/
│   ├── 02_design/      # 방안 A 설계
│   ├── 03_advanced_design/  # 방안 B 설계
│   └── 04_contextual_rag_design/  # 방안 C 설계
├── src/
│   ├── core/           # LLM, RAG, Parser 핵심 엔진
│   ├── adapters/       # 타겟별(SIMVA, CAPL) 코드 변환기
│   └── ui/             # Streamlit 대시보드
└── tests/              # 단위 및 통합 테스트
```

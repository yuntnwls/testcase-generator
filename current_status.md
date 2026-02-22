# 🚀 테스트 스크립트 생성기 (Universal Test Script Generator) - 현재 진행 현황 (Current Status)

본 문서는 다른 PC에서 프로젝트를 이어서 진행(Phase 2: 구현)할 수 있도록, **지금까지의 논의 내용, 에이전트의 역할, 그리고 작성된 설계 문서들의 역할을 요약**한 가이드입니다.

---

## 1. 프로젝트 목표 및 현재 진척도

- **목표**: 테스터가 작성한 "자연어(Excel/TSV)" 자동차 테스트 케이스를 SIMVA, CAPL 등 "다양한 타겟 스크립트"로 자동 변환하는 범용 AI 파이프라인 구축.
- **현재 상태 (**`Phase 1.5 완료`**)**:
  - 요구사항 분석 및 시스템 아키텍처 상세 설계가 100% 완료되었습니다.
  - 코드는 아직 작성하지 않았으며, 구현을 위한 모든 인터페이스 스펙 및 데이터 스키마 문서화가 끝난 상태입니다.
- **Next Step (**`Phase 2 시작`**)**:
  - 본 문서와 폴더 내 설계 문서들을 기반으로, 파이썬 기반의 Core Engine 및 Adapter 프레임워크 구현을 시작하면 됩니다.

---

## 2. AI 에이전트 페르소나 및 역할 분담 (AI Agents Role Definition)

본 프로젝트를 성공적으로 완수하기 위해, 구현을 담당할 AI는 다음 4가지 페르소나(역할) 중 현재 단계에 맞는 역할을 수행해야 합니다. 현재는 Phase 1.5가 종료되고 Phase 2(구현)로 넘어가는 전환점입니다. 새 PC에서 작업을 이어갈 때, AI에게 **현재 어떤 역할을 수행해야 하는지 명시적으로 부여**하면 훨씬 좋은 결과를 얻을 수 있습니다.

### 🏛️ [Role 1: Architect & Planner] (현재 집중 단계 완료 / 감시자 역할로 전환)
- **Mission**: 기술적 타당성 검증 및 설계 무결성 보장. 아키텍처가 "흔들리지 않는 편안함"을 유지하도록 함.
- **Responsibilities**:
  - **Living Documentation**: 구현 중 발견된 모든 설계 변경 사항을 즉시 `detailed_design.md`와 `analysis_report.md`에 반영.
  - **Solution Architecting**: "Pending Issues"(매크로, 에러 처리, UI 연동)에 대한 현실적인 해법 도출.
  - **Guard Rail**: 구현 코드가 설계 의도(Process Isolation, No-Rebuild)를 벗어나지 않도록 감시.
- **Directives (지침)**:
  - *"코드를 먼저 짜고 설계를 맞추지 말 것. 설계가 먼저다."*
  - *"플러그인 구조를 import 방식으로 회귀시키려는 유혹을 참아라. (안전성이 최우선)"*

### ⚙️ [Role 2: Core Implementer] (Phase 2 메인 역할 - 곧 활성화)
- **Mission**: 어떠한 악조건(TC 오타, 플러그인 크래시)에도 죽지 않는 견고한 Core Engine 구축.
- **Responsibilities**:
  - **Strict Typing**: `models.py`(IR 모델)를 Pydantic으로 엄격하게 정의하여 데이터 무결성 보장.
  - **Fault Tolerance**: 파싱 실패 시 프로그램 종료가 아닌, `ErrorIR`/`UnknownIR` 객체 생성으로 우아하게 처리.
  - **Process Management**: 서브프로세스 Timeout 및 Stderr 로깅을 철저히 구현.
- **Directives (지침)**:
  - *"정규식 파서는 '유연'해야 하지만, IR 생성기는 '엄격'해야 한다."*
  - *"메인 스레드는 절대 블로킹되지 않아야 한다."*

### 🔌 [Role 3: Plugin Developer] (Phase 2 후반부 역할 - 대기 중)
- **Mission**: Core Engine을 전혀 몰라도 동작하는 독립적이고 표준화된 어댑터 생태계 확장.
- **Responsibilities**:
  - **Standard I/O**: `stdin`으로 JSON을 받고 `stdout`으로 코드만 깔끔하게 뱉는 CLI 구현 (`simva_adapter.py`).
  - **Polyglot Verify**: 향후 C#이나 Go로도 어댑터를 만들 수 있음을 염두에 두고 인터페이스 설계.
  - **Domain Logic**: SIMVA 등 타겟 툴의 문법적 특성(Syntax) 완벽 구현.
- **Directives (지침)**:
  - *"메인 앱의 내부 클래스나 변수를 참조하려 하지 마라. 오직 JSON만 믿어라."*
  - *"로그는 반드시 stderr로만 찍어라. stdout은 코드 전용이다."*

### 🕵️ [Role 4: QA Engineer] (Phase 3 역할 - 대기 중)
- **Mission**: 사용자 관점에서의 "It Just Works" 검증.
- **Responsibilities**:
  - **E2E Testing**: TC 파일 -> Core -> IR -> Adapter -> Target Code 전체 파이프라인 검증.
  - **Edge Case**: 비정상적인 TC 입력, 존재하지 않는 Signal, 문법 오류 상황 테스트.
  - **Artifact Consistency**: 분석서, 설계서, 구현 코드가 일치하는지 상시 점검.
- **Directives (지침)**:
  - *"개발자가 '원래 그래요'라고 하면 '설계서에 없는데요?'라고 반문하라."*

---

## 3. 작성된 설계 문서 가이드 (문서별 역할)

`docs/01_analysis/` 및 `docs/02_design/` 폴더에 위치한 파일들은 다음의 역할을 수행합니다. 구현 시 이 문서들을 참조하십시오.

### 🏗️ [구조 및 아키텍처]
1. `docs/01_analysis/analysis_report.md` (심층 분석 보고서)
   - 프로젝트 초기에 작성된 가장 근본적인 문서입니다. "왜 자연어 TC를 코드로 바꾸는 것이 어려운가?"에 대한 언어적 특성(상태 의존성, 모호성 등)을 분석하고, SIMVA(Python)와 CAPL 간의 의미적 간극(Semantic Gap)을 해결하기 위한 추상화 전략(IR 도입)의 당위성이 꼼꼼히 기록되어 있습니다. Role 1(Architect)의 바이블 역할을 합니다.
2. `docs/02_design/detailed_design.md` (상세 설계서)
   - 전체 시스템 구조도(Mermaid), Core Engine과 Adapter의 분리 목적, Multi-LLM(Local/OpenAI/Gemini) 지원을 위한 Strategy Pattern 등 전체 뼈대가 기록되어 있습니다.
3. `docs/02_design/sequence_diagram.md` (실행 흐름도)
   - 사용자가 엑셀을 넣은 시점부터 -> VectorDB/Ontology를 거쳐 -> LLM이 프롬프트를 받고 IR을 만들고 -> Adapter가 Subprocess로 실행되어 코드를 찍어내기까지의 시간적 실행 흐름(Sequence) 다이어그램입니다.
4. `docs/02_design/dir_and_config_spec.md` (폴더/설정 규격)
   - Phase 2 개발 시작 전 만들어야 할 **물리적 폴더 구조(`src/core`, `src/adapters`, `data/`)**와 **통합 설정 파일(`config.yaml`)**의 스키마 및 제약 조건이 명시되어 있습니다.

### 📦 [데이터 스펙 및 통신 규격]
5. `docs/02_design/ir_schema_spec.md` (IR 명세서)
   - Core Engine과 Adapter를 이어주는 유일한 통신 규격인 **JSON IR의 Pydantic 모델 설계**입니다. `SET`, `CHECK`, `WAIT`, `MACRO_CALL`, `LOOP`, `UNKNOWN` 6가지 액션 타입이 정의되어 있습니다.
6. `docs/02_design/prompt_template_spec.md` (동적 프롬프트 설계)
   - LLM에게 보낼 프롬프트 구조입니다. 매 스텝(한 줄)마다 Vector DB 매칭 결과와 Ontology 제약 조건 검사 결과를 동적으로 끼워 넣는 **3단 구조(System, Context, Instruction)** 템플릿입니다.

### 🧠 [지식 엔진 (RAG) 데이터]
7. `docs/02_design/rag_db_schema_sample.md` (Vector DB / Ontology 설계)
   - 동의어를 표준 시그널로 매핑하는 `Vector DB`와 선행 조건 로직을 판단하는 `Ontology Graph` 데이터베이스의 라이프사이클(초기화-동적추가-조회) 및 데이터 스키마가 기록되어 있습니다.
8. `docs/02_design/rag_mock_data_scenarios.md` (시연용 Mock 데이터)
   - 향후 구현 직후 퀄리티 증명(PoC)을 위해 사용할 4가지 시나리오(은어 처리, 선행조건 제약경고, 충돌 에러 차단 등)와 15개의 샘플 시그널 데이터 세트가 기획되어 있습니다.

---

## 4. 새로운 PC에서 이어서 시작하는 방법

새 PC로 파일들을 클론(또는 복사)하신 후, 현재 원하시는 **다음 진행 단계(설계 고도화 vs 실제 구현)**에 맞춰 아래의 프롬프트 중 하나를 AI에게 복사하여 붙여넣으시면 시스템이 완벽하게 컨텍스트를 복구합니다.

### 📝 시나리오 A: 설계를 더 고도화하고 싶을 때 (Phase 1.5 지속)
아직 코딩에 들어가지 않고, 엣지 케이스나 파일 파싱 로직 등 아키텍처를 더 뾰족하게 다듬고 싶을 때 사용합니다.

> **"현재 프로젝트 폴더에 있는 `current_status.md`를 먼저 읽어줘. 그리고 문서에 기재된 설계 문서(`docs/...`)들도 전부 읽어줘. 너는 이제 이 프로젝트의 [Role 1: Architect & Planner]야. 우리는 아직 코딩(구현) 단계로 넘어가지 않고, 아키텍처와 상세 설계를 더 뾰족하게 다듬을 거야. 문서를 다 읽고 파악했다면 내가 다음에 지정할 추가 설계 주제를 기다려줘."**

### 💻 시나리오 B: 즉시 파이썬 코딩을 시작하고 싶을 때 (Phase 2 진입)
설계가 충분하다고 판단되어, 물리적인 폴더 구조를 만들고 실제 코드를 짜기 시작할 때 사용합니다.

> **"현재 프로젝트 폴더에 있는 `current_status.md`와 `docs/02_design/dir_and_config_spec.md` 를 읽어봐. 너는 이제 이 프로젝트의 [Role 2: Core Implementer]야. 설계는 모두 끝났으니 문서에 정의된 폴더 구조를 생성하고 `__init__.py` 들과 `config.yaml` 뼈대를 만들어줘. 그 다음 `ir_schema_spec.md`를 참고해서 `src/core/models.py` (Pydantic 모델) 구현부터 시작하자."**

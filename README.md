# 🚀 범용 테스트 스크립트 자동화 솔루션 (Universal Test Script Generator)

**"자연어 TC를 이해하고, 모든 테스트 도구의 코드를 생성하다."**

본 프로젝트는 엑셀/TSV로 작성된 자연어 테스트 케이스(TC)를 분석하여, **SIMVA**뿐만 아니라 향후 **CAPL, C#** 등 다양한 테스트 환경에서 실행 가능한 스크립트를 생성하는 **LLM 기반의 범용 자동화 솔루션**입니다.

## 🚀 주요 기능

- **자동 변환 (LLM-based Generation)**: Excel 또는 TSV 형식의 자연어 TC를 분석하여 최적의 SIMVA Python 코드를 생성합니다.
- **시그널 매핑 (Smart Mapping)**: Vector DB와 Ontology를 참조하여 TC 내의 변수명을 실제 코드 프로젝트의 시나리오 시그널로 정확하게 매핑합니다.
- **하이브리드 입력 방식**:
    - **Excel/TSV 업로드**: 대량의 TC를 한 번에 변환.
    - **GUI 직접 입력**: Streamlit 대시보드를 통해 화면에서 직접 TC를 작성하고 수정 가능.
- **정적 검증**: 생성된 코드의 문법 오류 및 시그널 유효성을 사전에 검사합니다.

## 🛠 기술 스택

- **Language**: Python 3.9+
- **Frontend**: Streamlit (대시보드 및 데이터 편집)
- **Data Analysis**: Pandas, Regular Expressions
- **Core Engine**: LLM (Ollama, OpenAI, Gemini), ChromaDB (Vector DB)

## 📚 문서 가이드 (Documentation Roadmap)

프로젝트의 진행 단계에 따른 상세 문서 맵입니다. 처음 오신 분은 **Phase 1**부터 순서대로 읽어보시는 것을 권장합니다.

### 🔍 Phase 1. 시스템 분석 (Analysis)
프로젝트의 목표와 기존 TC/시그널 데이터의 특징을 분석한 자료입니다.
- [상세 분석 보고서](docs/01_analysis/analysis_report.md): 자연어 TC의 특성(상태 의존성, 모호성)과 해결 과제 정리

### 📐 Phase 2. 시스템 설계 (Architecture & Design)
전체적인 구조와 모듈 간의 협력 가이드를 정의합니다.
- [상세 설계서](docs/02_design/detailed_design.md): 전체 아키텍처, IR 파이프라인, 모듈별 역할 및 클래스 명세
- [시퀀스 다이어그램](docs/02_design/sequence_diagram.md): TC 입력부터 스크립트 생성까지의 시간적 흐름도
- [GUI 개발 제안서](docs/02_design/ui_proposal.md): Streamlit 기반 화면 구성 및 인터렉션 설계

### 📋 Phase 3. 상세 규격서 (Technical Specifications)
구현에 필요한 데이터 구조와 상세 엔지니어링 스펙입니다.
- [IR 스키마 규격서](docs/02_design/ir_schema_spec.md): 중간 표현(IR)의 JSON 구조 및 Pydantic 모델 정의
- [프롬프트 설계 규격서](docs/02_design/prompt_template_spec.md): LLM 지시어, 템플릿 및 Few-shot 예제 포맷
- [디렉토리 및 설정 규격서](docs/02_design/dir_and_config_spec.md): 프로젝트의 물리적 폴더 구조(Layered Architecture) 및 `config.yaml` 상세 설정 규격
- [DB 설계서](docs/02_design/db_design.md): RDBMS(SQLite) 및 Vector DB(ChromaDB) 통합 스토리지 설계
- [RAG DB 스키마](docs/02_design/rag_db_schema_sample.md): Vector DB 및 Ontology를 위한 데이터 구조 예시
- [RAG Mock 데이터 및 시나리오](docs/02_design/rag_mock_data_scenarios.md): PoC 시연을 위한 상세 데이터셋 및 복합 제어 시나리오 가이드

### 🛡️ Phase 4. 고도화 전략 (Strategy & Topics)
특정 기술 이슈를 해결하기 위한 심화 기술 설계 문서입니다.
1. [Topic 1: LLM 자기 수정 루프](docs/02_design/strategy/Topic1_LLM_Self_Correction_Design.md)
2. [Topic 2: 어댑터 SDK 및 프로토콜](docs/02_design/strategy/Topic2_Adapter_SDK_Design.md)
3. [Topic 3: 추적성 및 로깅 아키텍처](docs/02_design/strategy/Topic3_Logging_Traceability_Design.md)
4. [Topic 4: 테스트 환경 설계](docs/02_design/strategy/Topic4_Testing_Architecture_Design.md)
5. [Topic 5: 지능형 지식 기반 어댑터](docs/02_design/strategy/Topic5_Smart_Adapter_LLM_Strategy.md)

---

## 📂 프로젝트 구조

```text
TestscriptGenerator/
├── data/               # 매뉴얼, 샘플 TC, Signal.cfg, RAG DB 소스 등 원천 데이터
├── docs/               # 상세 분석 및 설계 문서 (위 Roadmap 참조)
├── src/                # 실제 구현 소스 코드
│   ├── core/           # LLM, RAG, Parser 등 핵심 엔진
│   ├── adapters/       # 타겟별(SIMVA, CAPL...) 코드 변환기
│   └── ui/             # Streamlit 웹 대시보드
├── tests/              # 단위 및 통합 테스트 코드
└── README.md           # 프로젝트 개요 (본 파일)
```

# [프로젝트 현황 및 이관 가이드: 범용 테스트 스크립트 생성기]

## 1. 프로젝트 개요 (Project Overview)
- **목표**: 자연어(TC)를 분석하여 **SIMVA**뿐만 아니라 **CAPL, C#** 등 다양한 자동화 도구에서 실행 가능한 스크립트를 생성하는 **범용 플랫폼** 구축.
- **핵심 철학**: 
    1. **Extended (확장성)**: 특정 언어에 종속되지 않는 중간 표현(IR) 사용.
    2. **Isolated (안전성)**: 플러그인을 별도 프로세스로 실행하여 메인 앱 보호.
    3. **No-Rebuild (유연성)**: 소스 수정/빌드 없이 외부 스크립트 추가만으로 기능 확장.

## 2. 현재 상태 요약 (Current Status)
- **단계 (Phase)**: **Phase 1.5 설계 완료** (구현 직전 단계)
- **완료된 작업**:
    - [x] **심층 분석**: 자연어 파싱 한계 및 IR 도입 필요성 분석 (`docs/01_analysis/analysis_report.md`)
    - [x] **상세 설계**: 프로세스 격리형 어댑터 아키텍처 확정 (`docs/02_design/detailed_design.md`)
    - [x] **구현 계획**: 모듈별 개발 계획 수립 (`docs/02_design/implementation_plan.md`)
    - [x] **DB/UI 설계**: 스키마 및 화면 설계 (`db_design.md`, `ui_proposal.md`)

## 3. 핵심 아키텍처 (Key Architecture)
1.  **Core Engine (Python)**:
    - TC 로드 -> 정규식 파싱 -> **IR(JSON) 생성**
    - `simva` 라이브러리를 전혀 모르는 상태로 동작.
2.  **Adapter Layer (Process Isolation)**:
    - Main App이 플러그인을 `subprocess.Popen`으로 실행.
    - 통신 포맷: `STDIN(JSON IR)` -> `Plugin` -> `STDOUT(Code)`
    - 언어 제약 없음 (Python, C++, Go 등 무엇이든 가능).

## 4. 디렉토리 구조 (Directory Structure)
```text
TestscriptGenerator/
├── docs/             # 설계 문서 (Analysis, Design, DB, UI)
├── data/             # TC 샘플, Signal.cfg
├── src/              # [To-Be] 구현 소스 코드 위치
│   ├── core/         # Parser, IR Builder
│   ├── adapters/     # Plugin Runner
│   └── utils/        # Common Utils
└── README.md
```

## 5. Agent 역할 정의 (Role Definition for Next Session)
이 프로젝트를 이어받을 AI Agent는 다음 역할을 수행해야 합니다.

### [Role 1: Architect & Planner] (현재 완료)
- **책임**: 요구사항 분석, 아키텍처 설계, 문서화.
- **상태**: 대부분 완료되었으나, 구현 중 발생하는 설계 변경 사항을 즉시 문서에 반영해야 함.

### [Role 2: Core Implementer] (다음 할 일)
- **책임**: `src/core` 및 `src/utils` 구현.
- **Task**:
    1. `ir_model.py` (Pydantic) 작성.
    2. `parser.py` (Regex -> IR) 작성.
    3. `adapter_runner.py` (Subprocess) 작성.

### [Role 3: Plugin Developer] (다음 할 일)
- **책임**: `src/adapters` 내의 표준 플러그인 개발.
- **Task**: `simva_cli.py` (SIMVA 변환 로직) 구현 및 테스트.

### [Role 4: QA Engineer]
- **책임**: 생성된 스크립트 검증 및 End-to-End 테스트.
- **Task**: 샘플 TC를 넣어 최종 결과물이 `simva` 문법에 맞는지 확인.

## 6. 이관 후 바로 시작할 작업 (Next Action Item)
1. 이 `current_status.md` 파일을 새로운 워크스페이스 루트에 복사.
2. `docs/02_design/implementation_plan.md`를 열고 **Phase 2 구현** 시작.
3. 우선 `src` 디렉토리 구조 생성부터 진행.

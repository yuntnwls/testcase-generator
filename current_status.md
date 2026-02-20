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

## 5. 아키텍처 결정 기록 (Architecture Decision Records - ADR)
이 프로젝트의 핵심 설계 결정 사항과 그 근거를 기록합니다.

### ADR-001: 중간 표현 (Intermediate Representation) 도입
- **Context**: 자연어 TC와 특정 언어(SIMVA)가 1:1로 매핑되지 않아, 확장 시마다 파서를 재작성해야 함.
- **Decision**: TC 파싱 결과물을 언어 중립적인 JSON 객체(IR)로 변환하는 계층 추가.
- **Consequence**: 파서와 생성기가 분리되어 유연성 확보. 단, IR 스키마 정의 및 유지보수 비용 발생.

### ADR-002: 프로세스 격리 (Process Isolation) 기반 어댑터
- **Context**: Python `importlib`을 이용한 동적 로딩은 플러그인 코드의 에러가 메인 프로세스를 비정상 종료시킬 위험이 있음.
- **Decision**: 어댑터를 독립된 프로세스(CLI)로 실행하고, 표준 입출력(StdIO)으로 통신.
- **Consequence**:
    - **Stability**: 플러그인이 죽어도 메인 앱은 생존.
    - **Polyglot**: 파이썬 외의 언어(C#, Go)로도 어댑터 구현 가능.
    - **Overhead**: 프로세스 생성 및 JSON 직렬화 비용 발생 (TC 생성 특성상 무시 가능).

## 6. 핵심 데이터 명세 (Interface Specifications)

### 6.1. IR JSON Schema (Example)
Core Engine이 Adapter에게 전달하는 표준 데이터 포맷입니다.
```json
{
  "project_info": { "version": "1.0", "target": "SIMVA" },
  "steps": [
    {
      "id": 1,
      "type": "ACTION", // ACTION, CHECK, CONTROL
      "command": "SetSignal",
      "params": {
        "signal": "VehicleSpeed",
        "value": 100
      },
      "meta": { "source_text": "1. 속도를 100으로 설정" }
    }
  ]
}
```

### 6.2. Adapter CLI Protocol
모든 어댑터는 아래 규칙을 준수해야 합니다.
- **Input**: `stdin`으로 위 JSON 데이터를 수신.
- **Output**: `stdout`으로 생성된 소스 코드 문자열만 출력.
- **Error**: 오류 발생 시 `stderr`에 로그 출력 후 `exit code != 0` 리턴.

## 7. 향후 설계 과제 (Pending Design Issues)
구현 전 또는 구현과 병행하여 결정해야 할 사항들입니다.

1.  **Macro 관리 방안**: 사용자 정의 매크로 함수를 어댑터가 어떻게 인지하고 가져올 것인가? (현재: `macros.py` 정적 파일)
2.  **Error Handling**: 파싱 불가능한 자연어 문장을 만났을 때, IR에 `Unknown` 타입을 넣을 것인가, 바로 에러를 낼 것인가?
3.  **UI Integration**: 별도 프로세스로 도는 어댑터의 진행률(Progress)을 UI에 어떻게 표시할 것인가? (Stdout 파싱?)

### [Role 1: Architect & Planner] (현재 집중 단계)
- **Mission**: 기술적 타당성 검증 및 설계 무결성 보장. 아키텍처가 "흔들리지 않는 편안함"을 유지하도록 함.
- **Responsibilities**:
    - **Living Documentation**: 구현 중 발견된 모든 설계 변경 사항을 즉시 `detailed_design.md`와 `analysis_report.md`에 반영.
    - **Solution Architecting**: "Pending Issues"(매크로, 에러 처리, UI 연동)에 대한 현실적인 해법 도출.
    - **Guard Rail**: 구현 코드가 설계 의도(Process Isolation, No-Rebuild)를 벗어나지 않도록 감시.
- **Directives (지침)**:
    - "코드를 먼저 짜고 설계를 맞추지 말 것. 설계가 먼저다."
    - "플러그인 구조를 `import` 방식으로 회귀시키려는 유혹을 참아라. (안전성이 최우선)"

### [Role 2: Core Implementer] (대기 중)
- **Mission**: 어떠한 악조건(TC 오타, 플러그인 크래시)에도 죽지 않는 견고한 Core Engine 구축.
- **Responsibilities**:
    - **Strict Typing**: `ir_model.py`를 Pydantic으로 엄격하게 정의하여 데이터 무결성 보장.
    - **Fault Tolerance**: 파싱 실패 시 프로그램 종료가 아닌, `ErrorIR` 객체 생성으로 우아하게 처리.
    - **Process Management**: `adapter_runner.py`에서 서브프로세스 Timeout 및 Stderr 로깅 철저히 구현.
- **Directives (지침)**:
    - "정규식 파서는 '유연'해야 하지만, IR 생성기는 '엄격'해야 한다."
    - "메인 스레드는 절대 블로킹되지 않아야 한다."

### [Role 3: Plugin Developer] (대기 중)
- **Mission**: Core Engine을 전혀 몰라도 동작하는 독립적이고 표준화된 어댑터 생태계 확장.
- **Responsibilities**:
    - **Standard I/O**: `stdin`으로 JSON을 받고 `stdout`으로 코드만 깔끔하게 뱉는 CLI 구현 (`simva_cli.py`).
    - **Polyglot Verify**: 향후 C#이나 Go로도 어댑터를 만들 수 있음을 염두에 두고 인터페이스 설계.
    - **Domain Logic**: SIMVA 등 타겟 툴의 문법적 특성(Syntax) 완벽 구현.
- **Directives (지침)**:
    - "메인 앱의 내부 클래스나 변수를 참조하려 하지 마라. 오직 JSON만 믿어라."
    - "로그는 반드시 `stderr`로만 찍어라. `stdout`은 코드 전용이다."

### [Role 4: QA Engineer] (대기 중)
- **Mission**: 사용자 관점에서의 "It Just Works" 검증.
- **Responsibilities**:
    - **E2E Testing**: `TC 파일 -> Core -> IR -> Adapter -> Target Code` 전체 파이프라인 검증.
    - **Edge Case**: 비정상적인 TC 입력, 존재하지 않는 Signal, 문법 오류 상황 테스트.
    - **Artifact Consistency**: 분석서, 설계서, 구현 코드가 일치하는지 상시 점검.
- **Directives (지침)**:
    - "개발자가 '원래 그래요'라고 하면 '설계서에 없는데요?'라고 반문하라."

## 9. 이관 후 바로 시작할 작업 (Next Action Item)
1. 이 `current_status.md` 파일을 새로운 워크스페이스 루트에 복사.
2. `docs/01_analysis/analysis_report.md`와 `docs/02_design/detailed_design.md`를 정독하여 맥락 파악.
3. **[중요]** 바로 구현에 들어가지 말고, **"Part 7. 향후 설계 과제"**에 나열된 이슈들을 해결하기 위한 추가 설계를 진행할 것.
4. 사용자에게 "설계 보완을 위해 어떤 부분을 먼저 논의할까요?"라고 질문하며 시작.

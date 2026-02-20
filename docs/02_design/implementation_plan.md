# [범용 테스트 스크립트 자동화 구현 계획서 ({% now "Y-m-d" %})]

## 1. 개요
본 문서는 **범용 테스트 스크립트 생성기**의 구현 단계(Phase 2)를 구체적으로 정의합니다.
시스템은 **Core Engine (Parsers/IR)**과 **Adapter Layer (Simva/Factory)**로 구분되어 개발됩니다.

## 2. 전체 시스템 구성도
(상세 설계서의 `Extensible Architecture` 참조)

## 3. 모듈별 구현 계획 (Phase 2)

### 3.1. [Core Engine] (파싱 및 중간 표현)
- **위치**: `src/core/`
- **주요 모듈**:
    - `parser.py`: TC 파일을 읽어 정규식으로 Keyword/Value 추출.
    - `ir_builder.py`: 추출된 데이터를 `IR Model` (JSON)로 표준화.
    - `ir_model.py`: Pydantic 기반의 IR 스키마 정의 (`ActionIR`, `LoopIR` 등).
    - `mapper.py`: `Signal.cfg` 검색 및 IR 변수 매핑.

### 3.2. [Adapter Layer] (코드 생성 통신)
- **위치**: `src/adapters/`
- **주요 모듈**:
    - `runner.py`: 서브 프로세스 실행 및 StdIO 통신 관리 (`AdapterRunner`).
    - `simva_cli.py`: SIMVA 변환 로직을 담은 표준 플러그인 (실행 가능 파일).
    - `macros.py`: SIMVA 매크로.

### 3.3. [Application Utility]
- **위치**: `src/utils/`
- **주요 모듈**:
    - `signal_loader.py`: `signals.py` 및 `config` 파일 파싱.
    - `validator.py`: 생성된 코드 AST 검증.

## 4. Verification Plan (검증 계획)

### 4.1. Automated Tests
1.  **IR Generation Test**: 다양한 TC 패턴(Loop, If) 입력 시 예상된 JSON IR이 나오는지 검증.
2.  **Factory Test**: 설정(`config.json`) 변경에 따라 서로 다른 Adapter 인스턴스가 생성되는지 확인.
3.  **Code Generation Test**: 고정된 IR 입력에 대해 `SimvaAdapter`가 실행 가능한 Python 코드를 출력하는지 검증.

### 4.2. Integration Scenario
- `sample_tc.xlsx` -> `main.py` -> `converted_script.py` 과정을 End-to-End로 실행.
- 생성된 스크립트가 `simva` 모의 객체(Mock) 상에서 에러 없이 실행되는지 확인.

## 5. 승인 및 착수
본 계획서는 **확장성(OCP)**을 최우선으로 고려하여 수립되었습니다.
승인 시 `src` 디렉토리 구조 생성부터 시작하겠습니다.

# [SIMVA 자동화 솔루션 상세 분석 보고서]

## 1. 개요
본 문서는 사용자로부터 제공받은 **TC 정의서(Sample TC)**와 **Signal 정의서(Signal.cfg)**, 그리고 **SIMVA 매뉴얼**을 정밀 분석한 결과를 기술합니다. 이 분석을 토대로 자동화 스크립트 변환 로직의 기반을 마련합니다.

## 2. 입력 데이터 구조 분석

### 2.1. TC 정의서 (Excel/TSV) 분석
- **파일 포맷**: TSV (Tab Separated Values) 또는 Excel
- **핵심 컬럼 분석**:
    | 컬럼명 | 데이터 예시 | 분석 및 처리 방안 |
    | :--- | :--- | :--- |
    | **Requirement ID / T/Case ID** | `BDC_Front_Lamp_v_1` | 결과 리포트 및 스크립트 파일명 생성 시 식별자로 사용 |
    | **검증 목적** | `전방 램프 점등 조건 확인` | 생성된 Python 함수의 `Docstring`으로 삽입하여 가독성 확보 |
    | **시험 전 조건** (Pre-condition) | `1. (VehicleSpeed = 0x5)` | - **패턴**: `번호. (Action = Value)` 형태<br>- **변환**: `Setup` 단계 코드로 변환. 초기 상태 설정 명령어로 매핑. |
    | **시험 방법** (Test Procedure) | `1. (Wait(500))` | - **패턴**: `Wait(시간)`, `Set(Signal)` 등 혼재<br>- **변환**: `Action` 단계 코드로 변환. 시계열적 동작 수행. |
    | **판정 조건** (Expected Result) | `1. (Lamp_PuddleLamp = On)` | - **패턴**: `Condition = Value` 또는 함수 호출<br>- **변환**: `Assertion` 단계. `is_eq`, `keep_ge` 등의 검증 함수로 매핑. |
    | **초기화** (Clean up) | `Reset = OFF` | - **변환**: `Teardown` 단계. 테스트 종료 후 복구 코드로 사용. |

- **데이터 패턴 특이사항**:
    - **16진수 혼용**: `0x5`와 같은 16진수 표기가 있어 `int(value, 0)` 처리가 필요함.
    - **단위 모호성**: `Wait(500)`이 500ms인지 500s인지 SIMVA 매뉴얼(sec 단위)과 대조 필요. (통상 500ms -> 0.5s 변환 예상)
    - **복합 조건**: `(A and B) or C` 형태의 논리 연산이 등장할 수 있어, 이를 Python의 논리 연산자(`and`, `or`)로 파싱해야 함.

### 2.2. Signal 정의서 (Signal.cfg) 분석
- **파일 포맷**: CSV
- **핵심 컬럼**:
    - `term`: **Key ID**. TC에서 사용하는 변수명과 매핑될 핵심 식별자. (예: `NM_State_BDC_FD_BCAN1`)
    - `datatype`: 값 검증 및 형변환(Type Casting)에 사용. (예: `uint16` -> 정수형 처리)
- **매핑 챌린지 (Mapping Challenge)**:
    - TC의 변수명(`Lamp_PuddleLamp`)과 `Signal.cfg`의 `term`(`NM_...` 등)이 **완전히 일치하지 않을 가능성**이 높음.
    - **해결책**: 단순 문자열 일치가 아닌, **유사도 기반 검색(Fuzzy Matching)** 또는 **RAG(LLM 기반 검색)**가 필수적임.

## 3. SIMVA 스크립트 API 분석
- **구조**: Python 기반 라이브러리 형태 (`simva`, `signals`, `profiles` 모듈)
- **주요 패턴**:
    - **Signal Access**: `signals.[Profile].[SignalName]` (계층 구조)
    - **Control**: `simva.set_signal(Key, Value)`, `simva.wait(Sec)`
    - **Verification**: `simva.is_eq`, `simva.keep_ge` (Time-bound Assertion 포함)

## 4. 구현 난이도 및 위험 요소
1.  **시그널 매칭 정확도**: TC 작성자가 임의로 쓴 변수명과 실제 DB의 명칭 차이가 클 경우, 오매핑 위험이 있음. -> **사용자 확인(Human-in-the-loop) 인터페이스** 또는 **Top-K 추천** 기능 고려 필요.
2.  **문법 복잡도**: TC 내에 `if`, `loop` 등의 제어 로직이 자연어로 기술된 경우, 이를 정형화된 스크립트로 바꾸는 것은 LLM의 추론 능력에 의존해야 함.

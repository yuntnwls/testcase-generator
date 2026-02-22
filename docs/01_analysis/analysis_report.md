# [테스트 스크립트 자동화 솔루션 심층 분석 보고서]

## 1. 개요
본 문서는 자연어 기반의 테스트 케이스(TC)를 분석하여, SIMVA를 포함한 **다양한 타겟 테스트 프레임워크(Multi-Target Frameworks)**에서 실행 가능한 스크립트로 변환하기 위한 기술적 요구사항을 분석합니다.
특정 도구에 종속되지 않는 **중간 표현(Intermediate Representation)** 설계와 도메인 특화 언어(DSL) 분석에 중점을 둡니다.

## 2. 입력 데이터 구조 분석

자연어는 본질적으로 모호함과 생략을 포함하며, 이를 명시적인 프로그래밍 언어로 변환하기 위해서는 다음과 같은 **언어적 특성(Linguistic Features)**을 기술적으로 해석해야 합니다.

### 2.1. 상태 의존성 (State Dependency)
- **현상**: TC는 "엔진을 켠다"라고 명시한 후, 그 상태가 계속 유지됨을 전제로 다음 단계를 기술합니다.
- **기술적 과제**: 
    - Python 스크립트는 상태를 암묵적으로 기억하지 않으므로, 필요한 경우 명시적인 상태 확인(`is_eq`) 코드가 추가되어야 할 수 있습니다.
    - **초기화(Setup)** 단계에서 설정된 환경 변수(예: 전압, 온도)가 테스트 전반에 영향을 미치므로, 이를 전역 변수나 클래스 속성으로 관리해야 할지 분석이 필요합니다.

### 2.2. 시간적 로직의 모호성 (Temporal Logic)
- **현상**: "3초 동안 기다린다(Wait)"와 "3초 동안 확인한다(Check)"는 자연어로는 비슷해 보이지만, SIMVA API에서는 완전히 다른 함수로 매핑됩니다.
    - `Wait(3s)` -> `simva.wait(3)` (실행 지연)
    - `Check(Signal=A, 3s)` -> `simva.keep_eq(Signal, A, 3)` (상태 유지 검증)
- **분석 결론**: 단순 키워드 매칭("초", "시간")만으로는 부족하며, 문장의 **수로(Predicate)**가 '대기'인지 '검증'인지 파악하는 의도 분석(Intent Classification)이 선행되어야 합니다.

### 2.3. 암묵적 참조 (Implicit Reference)
- **현상**: "헤드램프를 켠다. 그리고 **그것**을 다시 끈다."
- **기술적 과제**: 대명사('그것')가 지칭하는 대상이 직전 단계의 `HeadLamp`임을 추론해야 합니다.
- **해결 방안**: LLM의 Context Window를 활용하여 이전 대화(Step)의 맥락을 유지하도록 프롬프트를 구성해야 합니다.

## 3. 데이터 구조 및 매핑 심층 분석

### 3.1. 시그널 매핑의 갭 (The Semantic Gap)
TC 작성자가 사용하는 용어와 실제 코드상의 변수명 사이에는 상당한 **의미적 거(Semantic Gap)**가 존재합니다.

| TC 용어 (Concept) | Python(SIMVA) `signals.py` 등 (Implementation) | 분석 및 해결 전략 |
| :--- | :--- | :--- |
| **속도 (Speed)** | `Ems_Eng_Speed_Rpm` vs `Can_Veh_Spd` | '속도'가 엔진 RPM인지 차량 속도인지 모호함. **DB 매핑 이력**을 통해 사용자가 자주 선택한 시그널을 우선 추천해야 함. |
| **켜다 (Turn On)** | `1`, `True`, `On_State` | 시그널의 `Data Type`(`uint8`, `bool`, `enum`)에 따라 `1`인지 `True`인지 결정하는 **Type Hinting**이 필수적임. |

### 3.2. 타겟 의존적 시그널 매핑 (Target-Specific Signal Mapping)
TC에서 사용된 시그널 이름(예: `VehicleSpeed`)이 SIMVA 코드에서는 `signals.BDC.Can_Veh_Spd`로 쓰이지만, 정작 CAPL과 같은 다른 환경에서는 `sysvar::Speed` 처럼 완전히 다른 네임스페이스와 이름을 가질 수 있습니다.

- **문제점**: `Core Engine`에서 IR(Intermediate Representation)을 생성할 때, 특정 언어(SIMVA)에 종속된 시그널 명칭을 포함시키면 어댑터의 재사용성이 떨어집니다.
- **분석 결론 (Abstraction Layer)**:
    1. **IR 단계에서는 논리적 시그널명만 유지**: IR 객체는 구체화된 코드가 아닌 표준화된(Logical) 시그널 이름만 가져야 합니다. (예: `{"target_signal": "VehicleSpeed"}`)
    2. **어댑터(Adapter) 책임으로 위임**: 실제 코드 생성 시, `SIMVA Adapter`는 자신에게 맞는 `signals.py`(또는 DB)를 참조하여 `VehicleSpeed` -> `signals.BDC.Can_Veh_Spd`로 변환하고, `CAPL Adapter`는 `VehicleSpeed` -> `sysvar::Speed`로 매핑을 수행해야 합니다.
    3. **레지스트리(Registry) 분리**: `Signal Registry`는 단일 파일이 아니라, 타겟 언어별로 매핑 테이블을 독립적으로 관리할 수 있는 구조(Project-Target 1:N 맵핑)를 지원해야 합니다.

### 3.3. 제어 구조의 변환 (Control Flow & IR Mapping)
단순 순차 실행(Linear Execution) 외에 조건부 실행이 TC에 포함될 경우, 이를 중간 표현(IR)으로 어떻게 추상화할지 정의합니다.

#### [Case Study: Loop]
- **Natural Language**: "속도가 100이 될 때까지 가속한다." (Until 조건)
- **Intermediate Representation (IR)**:
  ```json
  {
    "type": "LOOP",
    "mode": "UNTIL",
    "condition": {
      "left": "Speed", "operator": ">=", "right": 100
    },
    "action": { "type": "CALL", "func": "Accelerate" }
  }
  ```
- **Target Code Generation**:
  - **Python (SIMVA)**:
    ```python
    while simva.get_signal(signals.Speed) < 100:
        accelerate()
        simva.wait(0.1)
    ```
  - **CAPL (Reference)**:
    ```c
    while(sysGetVariableFloat(sysvar::Speed) < 100) {
        Accelerate();
        testWaitForTimeout(100);
    }
    ```

#### [Case Study: Exception]
- **Natural Language**: "만약 에러가 발생하면 테스트를 중단한다."
- **IR**: `{"type": "IF", "condition": "Error == True", "action": "ABORT"}`
- **Python**: `if check_error(): raise TestFail("Error detected")`

### 3.4. 매크로 및 사용자 정의 함수 (Macro & User-Defined Functions)
사용자가 직접 작성한 복잡한 시퀀스(예: `Initial_EngineON()`)를 TC에서 자연어로 호출하는 경우에 대한 분석입니다.

- **문제점**: `Core Engine`은 `Initial_EngineON`이 단순한 시그널인지, 아니면 매크로 함수인지 구분할 수 없습니다. 또한 타겟(SIMVA vs CAPL)마다 매크로의 구현체(`macros.py` vs `macros.cin`)가 다릅니다.
- **분석 결론 (Target-Aware Macro Resolution)**:
    1. **IR은 CALL 형태로 추상화**: `Core Engine`은 동사/명사 분석을 통해 일반 시그널 제어가 아닌 함수 호출로 판단되면, IR을 `{"type": "MACRO_CALL", "name": "Initial_EngineON"}` 형태로 생성합니다.
    2. **어댑터의 Macro Registry**: 각 어댑터는 시작 시점에 자신의 환경에 맞는 매크로 파일(`macros.py`)을 정적 분석(`ast`)하여 사용 가능한 함수 목록(Macro Registry)을 구성합니다.
    3. **Code Generation**: 어댑터는 IR의 `MACRO_CALL`을 만나면 Registry를 확인하여, 타겟 언어의 문법에 맞는 올바른 함수 호출 코드(예: `Initial_EngineON()`)를 생성하고, 필요한 `import` 문을 최상단에 자동으로 추가합니다.

### 3.5. 오류 처리 전략 (Error Handling Strategy for Unparsable Input)
자연어 TC 중 문법 구조가 심각하게 깨져 있거나, 매핑할 수 없는 신조어가 포함되어 Core Engine이 해석에 실패한 경우의 처리 방안입니다.

- **문제점**: 파싱 실패 시 프로그램(또는 해당 TC 전체 변환)을 바로 중단(Abort)할 것인가, 아니면 해당 라인만 건너뛰고 계속 진행(Continue)할 것인가?
- **분석 결론 (Graceful Degradation & IR Type "UNKNOWN")**:
    1. **전체 중단 금지**: TC 문서를 작성하다 보면 한두 줄의 오타나 모호한 문장은 매우 흔히 발생합니다. 하나가 실패했다고 전체 프로세스를 중단하면 사용자 편의성이 크게 저하됩니다.
    2. **"UNKNOWN" IR 객체 생성**: 파싱이 불가능한 라인을 만나면 예외(Exception)를 던지지 않고, `{"type": "UNKNOWN", "raw_text": "해석 불가 문자열..."}` 형태의 특별한 IR 객체를 생성하여 파이프라인으로 흘려보냅니다.
    3. **어댑터의 주석 처리 (Comment Generation)**: 어댑터는 `UNKNOWN` 타입의 IR을 수신하면, 타겟 언어의 주석 문법에 맞춰 결과 코드를 생성합니다. (예: Python `simva`의 경우 `# FIXME: 자동 파싱 실패 - "해석 불가 문자열..."`)
    4. **UI 피드백**: UI 레이어에서는 변환 완료 후 사용자에게 "총 100줄 중 2줄 변환 실패" 와 같이 요약 리포트를 제공하여, 생성된 코드에서 `FIXME` 주석을 직접 검색하여 수정하도록 유도합니다.

### 3.6. UI 연동 및 모니터링 전략 (UI Integration & Progress Monitoring)
Core Engine과 외부 프로세스(Adapter) 간의 상태(Progress, Warning, Error)를 Streamlit UI에 실시간으로 어떻게 반영할 것인가에 대한 분석입니다.

- **문제점**: Adapter는 완전히 분리된 프로세스이므로, 메인 앱(UI)은 Adapter가 100줄의 스크립트 중 몇 번째 줄을 생성 중인지, 내부적으로 경고가 발생했는지 직접 알 수 없습니다.
- **분석 결론 (Standard Error/Output Protocol)**:
    1. **Output 분리 원칙**: Adapter의 `stdout`은 오로지 **최종 생성된 코드**만을 출력하는 데 사용해야 합니다. (다른 텍스트가 섞이면 코드가 망가짐).
    2. **통신 채널 활용 (`stderr`)**: Adapter의 진행률(Progress), 중간 로그, 경고, 에러 메시지는 모두 `stderr` 채널을 통해 메인 프로세스로 전달합니다.
    3. **정형화된 로그 포맷**: `stderr`로 출력되는 메시지에도 접두어(Prefix) 규칙을 부여하여 메인 앱이 파싱할 수 있게 합니다.
        - `[PROGRESS] 45/100` : 진행률 바 업데이트용
        - `[WARN] VehicleSpeed not found in Signal.cfg. Using default.` : UI 경고창 토스트용
        - `[ERROR] LLM API Timeout Exception` : 프로세스 강제 중단 및 UI 에러 화면 표시용
    4. **비동기 스트림 읽기**: `Core Engine`의 `AdapterRunner`는 `subprocess.Popen`으로 어댑터를 실행한 후, 메인 스레드가 블로킹되지 않도록 `stderr`를 별도 스레드(또는 `asyncio`)에서 한 줄씩 실시간으로 읽어 Streamlit UI 렌더링에 반영(예: `st.progress()`)합니다.

## 6. 확장성 분석: 다중 타겟 스크립트 지원 (Multi-Target Support)

본 시스템이 SIMVA(Python)뿐만 아니라 향후 CAPL, C#, 또는 독자적인 DSL(Domain Specific Language) 등 다양한 타겟 언어를 지원하기 위해서는 **"파싱(Parsing)"과 "생성(Generation)"의 완전한 분리**가 필요합니다.

### 6.1. 문제 정의 (Target Dependency)
- **현재 구조**: TC 파서가 즉시 `simva.set_signal`과 같은 특정 라이브러리 코드를 고려하여 동작함.
- **확장 시 문제점**: 타겟 언어가 바뀔 때마다 파서, 프롬프트, 생성기 로직을 모두 수정해야 함.

### 6.2. 해결 전략: 중간 표현 (Intermediate Representation, IR) 도입
컴파일러 설계 원리를 차용하여, 자연어 TC를 바로 코드로 바꾸지 않고 **중립적인 추상 모델(IR)**로 먼저 변환해야 합니다.

#### [Step 1] TC -> IR (Logic Abstraction)
- 자연어 "헤드램프를 켠다"를 특정 언어가 아닌 **행위(Behavior)** 중심의 객체로 변환.
- **IR 예시 (JSON)**:
    ```json
    {
      "step_id": 1,
      "action_type": "SET",
      "target_signal": "HeadLamp",
      "target_value": "ON",
      "condition": null
    }
    ```

#### [Step 2] IR -> Target Code (Code Generation Adapter)
- 생성된 IR 데이터를 입력받아, 특정 언어의 문법(Syntax)에 맞게 변환하는 **어댑터(Adapter)**만 교체하면 됨.

### 6.3. 동적 확장 전략 (Process Isolation vs Dynamic Loading)

사용자의 요청에 따라, 시스템의 안정성(Stability)을 최우선으로 고려하여 **별도 프로세스 실행(Separate Process)** 방식을 채택합니다.

#### [비교 분석]
| 구분 | Dynamic Loading (Internal) | **Separate Process (External)** [Selected] |
| :--- | :--- | :--- |
| **방식** | `importlib`으로 클래스 로드 | `subprocess.run`으로 스크립트 실행 |
| **장점** | 구현이 간단하고 속도가 빠름 | **플러그인이 죽어도 메인 앱은 안전함 (Crash Isolation)** |
| **단점** | 플러그인 에러가 전파될 수 있음 | 통신 오버헤드(IPC) 및 데이터 직렬화 필요 |

#### [채택된 아키텍처: CLI Wrapper]
1.  **Core Engine**: TC 분석 후 **IR(JSON)**을 생성하여 표준 입력(stdin) 또는 파일로 전달.
2.  **Adapter Process**: 독립된 프로세스로 실행되어 IR을 읽고, 결과 코드(Result)를 표준 출력(stdout)으로 반환.
3.  **Interface**:
    ```bash
    # 메인 앱이 어댑터를 호출하는 방식
    > python adapters/custom_converter.py --input ir_data.json --output result.py
    ```


## 4. 시스템 아키텍처 기술적 요구사항

위 분석을 토대로 시스템이 갖추어야 할 핵심 기술 역량을 정의합니다.

1.  **Context-Aware Parsing**: 
    - 각 Step을 독립적으로 해석하지 않고, 전체 시나리오의 흐름(Sequence)을 고려하여 코드를 생성해야 합니다.
2.  **Advanced Knowledge Management (지식 관리 체계화)**:
    - **Vector DB (유사도 검색)**: TC 작성자가 사용하는 다양한 비표준 용어("속력을 높인다", "엑셀을 밟는다")를 표준 시그널(`VehicleSpeed`)로 매핑하기 위해, 단순 키워드 매칭을 넘어 LLM 임베딩 기반의 Vector DB 공간 검색을 활용해야 합니다.
    - **Ontology / Knowledge Graph (도메인 지식 모델링)**: "엔진이 켜져야 주행이 가능하다"와 같은 차량 도메인의 제약 사항이나, 각 시그널 간의 관계(예: `ACC` -> `IGN` 계층 구조)를 온톨로지로 구축하여, LLM이 코드를 생성할 때 논리적 오류를 스스로 검증할 수 있는 기반을 마련해야 합니다.
3.  **Strict Validation**: 
    - 생성된 Python 코드는 실행 전 **AST(Abstract Syntax Tree)** 분석을 통해 `signals.py`에 정의되지 않은 속성 접근을 사전에 차단해야 합니다. (Runtime Error 방지)

## 5. 결론
이 솔루션은 단순한 "번역기(Translator)"가 아니라, **"테스트 엔지니어의 의도(Intent)를 이해하고 도메인 문법(SIMVA API)에 맞게 재구성하는 AI 에이전트"**로 설계되어야 합니다. 이를 위해 **LLM의 텍스트 추론 능력**, **Vector DB의 의미론적 검색**, 그리고 **Ontology 기반의 도메인 지식**이 유기적으로 결합되어야 합니다. 추가적으로, 폐쇄망 및 저사양 장비를 고려하여 **CPU-Only Local LLM**부터 **Cloud API**까지 설정만으로 손쉽게 교체 가능한 **LLM Provider Abstraction** 아키텍처를 채택하여 유연성과 보안을 극대화합니다.

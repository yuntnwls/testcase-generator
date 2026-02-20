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

| TC 용어 (Concept) | Signal.cfg / signals.py (Implementation) | 분석 및 해결 전략 |
| :--- | :--- | :--- |
| **속도 (Speed)** | `Ems_Eng_Speed_Rpm` vs `Can_Veh_Spd` | '속도'가 엔진 RPM인지 차량 속도인지 모호함. **DB 매핑 이력**을 통해 사용자가 자주 선택한 시그널을 우선 추천해야 함. |
| **켜다 (Turn On)** | `1`, `True`, `On_State` | 시그널의 `Data Type`(`uint8`, `bool`, `enum`)에 따라 `1`인지 `True`인지 결정하는 **Type Hinting**이 필수적임. |

### 3.2. 제어 구조의 변환 (Control Flow & IR Mapping)
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
2.  **Feedback Loop & Knowledge Base**: 
    - 모호한 용어("속도")에 대한 매핑 결정은 일회성이 아니어야 합니다. 사용자 선택 데이터를 **DB(`mapping_history`)**에 저장하여, 시스템이 점진적으로 해당 도메인의 용어집(Glossary)을 학습하도록 설계해야 합니다.
3.  **Strict Validation**: 
    - 생성된 Python 코드는 실행 전 **AST(Abstract Syntax Tree)** 분석을 통해 `signals.py`에 정의되지 않은 속성 접근을 사전에 차단해야 합니다. (Runtime Error 방지)

## 5. 결론
이 솔루션은 단순한 "번역기(Translator)"가 아니라, **"테스트 엔지니어의 의도(Intent)를 이해하고 도메인 문법(SIMVA API)에 맞게 재구성하는 AI 에이전트"**로 설계되어야 합니다. 이를 위해 **LLM의 추론 능력**과 **DB 기반의 지식 축적**이 유기적으로 결합되어야 합니다.

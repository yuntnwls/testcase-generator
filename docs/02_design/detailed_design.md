# [테스트 스크립트 자동화 솔루션 상세 설계서]

## 1. 시스템 아키텍처 설계 (Extensible Architecture)

### 1.1. 전체 구성도
```mermaid
graph TD
    subgraph Input_Layer [입력 계층]
        TC_File[TC 정의서 (Excel/TSV)]
        Signal_CFG[Signal Source (File/Code)]
    end

    subgraph Core_Engine [Core Engine (Target-Agnostic)]
        TC_Parser[TC Parser (Regex)]
        IR_Builder[IR Builder (Abstract Model)]
        Signal_Registry[Signal Registry (Abstract Index)]
        Mapper[Mapper & Prompt Engine]
        
        TC_File --> TC_Parser
        TC_Parser -- "Raw Data" --> IR_Builder
        Signal_CFG --> Signal_Registry
        Signal_Registry --> Mapper
        IR_Builder -- "Intermediate Representation (JSON)" --> Mapper
    end

    subgraph Adapter_Layer [Adapter Layer (Target-Specific)]
        LLM[LLM (Code Logic Generation)]
        Simva_Adapter[SIMVA Adapter (Python)]
        Other_Adapter[Other Tool Adapter (Future)]
        
        Mapper --> LLM
        LLM -- "Abstract Logic / Pseudo Code" --> Simva_Adapter
        LLM -.-> Other_Adapter
    end

    subgraph Output_Layer [출력 계층]
        Final_Script[Target Script (.py / .cs / ...)]
        Validator[Syntax Validator]
        
        Simva_Adapter --> Validator
        Validator --> Final_Script
    end
```

## 2. 모듈별 상세 설계 및 구현 계획

### 2.1. Signal Loader & Code Registry (Source of Truth)
- **구현 상세 (Implementation Details)**:
    - **라이브러리**: `ast` (Python 표준 라이브러리)
    - **핵심 로직 (AST Parsing)**:
      ```python
      import ast

      def parse_signals(file_path):
          with open(file_path, "r", encoding="utf-8") as f:
              tree = ast.parse(f.read())
          
          registry = {}
          # ClassDef(Profile) -> Assign(Signal) 탐색
          for node in ast.walk(tree):
              if isinstance(node, ast.ClassDef):
                  profile_name = node.name
                  for submapping in node.body:
                      if isinstance(submapping, ast.Assign):
                          # signals.BDC.SignalName 구조 추출
                          signal_name = submapping.targets[0].id
                          full_path = f"signals.{profile_name}.{signal_name}"
                          registry[signal_name] = full_path
          return registry
      ```
    - **설계 의도**: `import`하여 실행하는 것보다 `ast`로 파싱하는 것이 안전하며(Side-effect 없음), 정적 분석의 핵심 기초 기술입니다.

### 2.2. TC Parser & IR Builder (중간 표현 생성)
- **설계 의도**: 자연어 TC를 특정 언어에 종속되지 않는 **중립적 구조체(Intermediate Representation)**로 변환.
- **IR 데이터 구조 (JSON Schema)**:
  ```json
  [
    {
      "step_id": 1,
      "type": "ACTION", // or "CHECK", "CONTROL"
      "keyword": "HeadLamp",
      "value": "ON",
      "condition": {
        "operator": "==", 
        "target": "ON"
      },
      "meta": {
        "original_text": "1. (HeadLamp = On)"
      }
    }
  ]
  ```
- **구현 상세**:
    - **Parsing**: 정규식으로 텍스트 추출.
    - **Normalization**: "Wait(500)" -> `{"type": "WAIT", "value": 0.5, "unit": "sec"}` 로 표준화.
    - **Builder**: 파싱된 데이터를 위 JSON 스키마에 맞춰 객체화(`pydantic` 모델 활용 권장).

### 2.3. Mapper & Prompt Engine (Target-Aware RAG)
- **설계 의도**: IR과 매핑된 시그널 정보를 바탕으로, **선택된 타겟 언어(Target Language)**에 최적화된 프롬프트를 생성.
- **Dynamic Prompting Strategy**:
    - **Abstract Context**: 타겟과 무관한 시그널 정보 및 이전 매핑 이력 주입.
        ```text
        [Signal Context]
        - "VehicleSpeed" maps to "signals.BDC.Can_Veh_Spd" (Type: uint16)
        ```
    - **Target-Specific Rule Injection**: 어댑터로부터 해당 언어의 문법 규칙을 받아 프롬프트에 추가.
        ```text
        [Generation Rules for SIMVA]
        1. Use 'simva.set_signal(KEY, VAL)' for actions.
        2. Use 'simva.keep_eq(KEY, VAL, TIME)' for checks.
        ```
- **구현 상세**:
    - `PromptBuilder` 클래스가 `TargetAdapter`에게 `get_prompt_rules()`를 호출하여 규칙을 동적으로 구성.

### 2.4. Multi-Target Adapter & Generator (핵심 확장 포인트)
- **설계 의도**: 특정 언어(Python/SIMVA)에 종속된 로직을 **어댑터(Adapter)**로 격리하여 확장성 확보.
- **아키텍처 (Strategy Pattern)**:
    - **Interface (`ICodeGenerator`)**:
      ```python
      class ICodeGenerator(ABC):
          @abstractmethod
          def generate_setup(self, ir_data): pass
          @abstractmethod
          def generate_action(self, step_ir): pass
          @abstractmethod
          def validate(self, code): pass
      ```
    - **Implementation 1 (`SimvaGenerator`)**:
      - `generate_action` -> `simva.set_signal(...)` 생성
      - `validate` -> `ast.parse` 사용
    - **Implementation 2 (`CaplGenerator` - Future)**:
      - `generate_action` -> `setSignal(...)` 생성 (CAPL 문법)
      - `validate` -> Regex 또는 CAPL 컴파일러 연동

- **Process Isolation Architecture (Stability & Polyglot)**:
    - **설계 의도**: 외부 플러그인을 독립 프로세스로 실행하여, 메인 애플리케이션의 메모리와 실행 흐름을 완벽하게 보호.
    - **구현 상세 (`subprocess` 활용)**:
      ```python
      import subprocess
      import json

      class AdapterRunner:
          def __init__(self, script_path):
              self.script_path = script_path

          def run(self, ir_data: dict) -> str:
              """
              IR 데이터를 JSON 문자열로 변환하여 서브 프로세스에 전달하고,
              생성된 코드를 받아옴.
              """
              try:
                  # CLI 실행: python plugin.py
                  process = subprocess.Popen(
                      ["python", self.script_path], 
                      stdin=subprocess.PIPE, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE,
                      text=True
                  )
                  
                  # IR 전달 (Stdin)
                  stdout, stderr = process.communicate(input=json.dumps(ir_data))
                  
                  if process.returncode != 0:
                      raise RuntimeError(f"Plugin Error: {stderr}")
                      
                  return stdout # 생성된 코드
                  
              except Exception as e:
                  logging.error(f"Failed to run adapter {self.script_path}: {e}")
                  raise
      ```
    - **플러그인 작성 표준**:
      - 모든 플러그인은 `stdin`으로 JSON을 받고, `stdout`으로 코드를 출력하도록 작성되어야 함.


- **Code Validator (Safety Layer)**:
    - 각 구현체(`SimvaGenerator`) 내부에서 해당 언어에 맞는 검증 로직(`validate`)을 수행.

### 2.5. Macro System (User Defined Functions)
- **설계 의도**: `simva` 라이브러리에 없는 복잡한 시퀀스(예: 초기화, 복합 제어)를 재사용 가능한 Python 함수로 모듈화.
- **구현 상세 (Implementation Details)**:
    - **모듈 구조**: `macros.py` 파일에 사용자 정의 함수를 모아두고, 생성된 스크립트에서 이를 import하여 사용.
    - **Code Example**:
      ```python
      # [macros.py]
      import simva
      import signals

      def Initial_EngineON():
          """엔진 시동 시퀀스"""
          simva.set_signal(signals.BDC.Ignition_Switch, 1) # ACC
          simva.wait(0.5)
          simva.set_signal(signals.BDC.Ignition_Switch, 2) # IGN On
          simva.wait(1.0)
      
      # [Generated Script]
      from macros import Initial_EngineON
      
      def test_case_1():
          Initial_EngineON()  # TC의 "Initial_EngineON" 요청을 함수 호출로 변환
      ```
    - **Parser 로직**: TC에서 `Action`이 `signal_registry`에 없고, `macros` 리스트에 존재하면 매크로 함수 호출로 변환.

## 3. 데이터 흐름 및 통합 전략
- **통합 포인트**: 모든 모듈은 인터페이스 기반으로 설계되어, 향후 특정 모델(GPT-4 -> Claude 3.5 등)을 교체하더라도 전체 워크플로우 영향 최소화.
- **UI/DB 연동**: 
    - **GUI**: Streamlit을 통해 사용자에게 변환 과정을 시각적으로 전달 (상세: `ui_proposal.md`).
    - **DB**: 매핑 결과와 학습 데이터를 영구 저장하여 지속적 고도화 지원 (상세: `db_design.md`).

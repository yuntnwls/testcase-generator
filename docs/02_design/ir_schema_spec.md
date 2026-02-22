# 중간 표현 (IR) 스키마 상세 명세서

본 문서는 **Core Engine**과 타겟별 **Adapter** 간의 유일한 통신 규격인 중간 표현(Intermediate Representation, IR)의 상세 구조를 정의합니다. Python의 `pydantic` 라이브러리를 활용하여 데이터 검증(Validation)과 타입(Type) 안정성을 보장하도록 설계되었습니다.

---

## 1. IR 설계 원칙
1. **Target-Agnostic**: `simva`나 `CAPL` 등 특정 언어의 함수명이나 문법이 포함되어서는 안 됩니다. 오직 "행위의 의도(Intent)"만을 담습니다.
2. **Atomic Actions**: 복잡한 자연어 문장은 최소 단위의 단일 행동(Atomic Action)으로 분할되어 하나의 IR 객체로 매핑됩니다.
3. **Graceful Degradation**: 해석 불가능한 문장에 대해서는 전체 프로세스를 죽이지 않고 `UNKNOWN` 타입으로 처리하여 어댑터로 넘깁니다.

---

## 2. IR 컴포넌트 구조 (Pydantic Models)

모든 IR은 공통된 Base 구조를 가지며, 행동의 유형(`type`)에 따라 상세 필드가 달라집니다.

### 2.1. Base IR Model
모든 IR 객체가 공통으로 가져야 하는 메타데이터입니다.

```python
from pydantic import BaseModel, Field
from typing import Optional, Union, List
from enum import Enum

class IRType(str, Enum):
    SET = "SET"               # 값 설정 (Action)
    CHECK = "CHECK"           # 상태 확인 (Verification)
    WAIT = "WAIT"             # 대기 (Delay)
    MACRO_CALL = "MACRO_CALL" # 사용자 정의 함수(매크로) 호출
    LOOP = "LOOP"             # 반복문 (추후 지원)
    UNKNOWN = "UNKNOWN"       # 파싱 실패

class BaseIR(BaseModel):
    step_id: int = Field(..., description="TC 내의 단계 번호 (1-indexed)")
    type: IRType = Field(..., description="IR의 유형")
    original_text: str = Field(..., description="매핑된 원본 TC 자연어 문장")
    description: Optional[str] = Field(None, description="어댑터가 코드로 변환 시 주석으로 추가할 설명")
```

### 2.2. SET IR (상태 변경/제어)
시그널의 값을 변경하는 행위입니다. (자연어 예시: _"속도를 60으로 맞춘다"_, _"엔진을 켠다"_)

```python
class SetIR(BaseIR):
    type: IRType = IRType.SET
    logical_signal: str = Field(..., description="Vector DB에서 매핑된 표준 논리적 시그널 명 (예: VehicleSpeed)")
    value: Union[int, float, str, bool] = Field(..., description="설정할 제어 값")
    unit: Optional[str] = Field(None, description="값의 단위 (예: km/h, rpm)")
    
    # 예시: {"step_id": 1, "type": "SET", "logical_signal": "VehicleSpeed", "value": 60}
```

### 2.3. CHECK IR (상태 검증)
특정 시그널이 예상된 값을 가지는지(또는 유지하는지) 검사합니다. (자연어 예시: _"속도가 60인지 3초 동안 확인한다"_, _"전조등이 켜져 있는지 본다"_)

```python
class Operator(str, Enum):
    EQ = "=="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="

class CheckIR(BaseIR):
    type: IRType = IRType.CHECK
    logical_signal: str = Field(..., description="검증할 표준 논리적 시그널 명")
    operator: Operator = Field(Operator.EQ, description="비교 연산자 (기본값: ==)")
    expected_value: Union[int, float, str, bool] = Field(..., description="기대하는 값")
    duration_sec: Optional[float] = Field(None, description="해당 상태를 유지/확인할 시간 (초). 값이 없으면 단발성 체크")
    
    # 예시: {"step_id": 2, "type": "CHECK", "logical_signal": "Ignition_Status", "operator": "==", "expected_value": "ON"}
```

### 2.4. WAIT IR (단순 대기)
아무런 동작 없이 특정 시간 동안 지연시킵니다. (자연어 예시: _"500ms 동안 기다린다"_)

```python
class WaitIR(BaseIR):
    type: IRType = IRType.WAIT
    duration_sec: float = Field(..., description="대기할 시간 (초 단위로 정규화)")
    
    # 예시: {"step_id": 3, "type": "WAIT", "duration_sec": 0.5}
```

### 2.5. MACRO_CALL IR (사용자 정의 함수 호출)
복잡한 프로시저나 시스템에서 기본 제공하지 않는 묶음 동작을 호출합니다. (자연어 예시: _"초기화 시퀀스를 실행한다"_)

```python
class MacroCallIR(BaseIR):
    type: IRType = IRType.MACRO_CALL
    macro_name: str = Field(..., description="호출할 매크로/함수 명")
    arguments: Optional[dict] = Field(None, description="함수에 전달할 인자 맵")
    
    # 예시: {"step_id": 4, "type": "MACRO_CALL", "macro_name": "Initial_EngineON"}
```

### 2.6. LOOP IR (반복 제어문)
특정 동작(Sequence)을 여러 번 반복해야 할 때 사용합니다. (자연어 예시: _"브레이크를 5번 밟았다 뗀다"_)

```python
class LoopIR(BaseIR):
    type: IRType = IRType.LOOP
    count: int = Field(..., description="반복 횟수")
    body: List['AnyIR'] = Field(..., description="반복해서 실행할 IR 배열 (재귀적 구조)")
    
    # 예시: 
    # {
    #   "type": "LOOP", "count": 5, 
    #   "body": [ {"type": "SET", ...}, {"type": "WAIT", ...} ]
    # }
```

### 2.7. UNKNOWN (오류 캡슐화)
Core Engine(LLM + Regex)이 도저히 해석하거나 매핑할 수 없는 쓰레기값이 들어온 경우 예외(Exception)를 던지지 않고 이 모델에 감싸서 전달합니다.

```python
class UnknownIR(BaseIR):
    type: IRType = IRType.UNKNOWN
    # BaseIR의 original_text 필드에 실패한 원본 문자열이 담겨 있습니다.
    reason: str = Field(..., description="실패 사유 (에러 메시지 등)")
    
    # 예시: {"step_id": 5, "type": "UNKNOWN", "original_text": "아무말 대잔치", "reason": "No matching signal or logic found"}
```

---

## 3. 최종 TC 스크립트 출력 포맷 (JSON Payload)

Core Engine이 Adapter 프로세스의 `stdin`으로 넘겨주는 전체 JSON 배열의 형태입니다. 여러 개의 IR이 `steps` 배열로 묶여 전달됩니다.

```python
# LLM 파서의 최종 출력 타입 지정
AnyIR = Union[SetIR, CheckIR, WaitIR, MacroCallIR, UnknownIR]

class TestCaseIR(BaseModel):
    tc_id: str = Field(..., description="테스트 케이스 식별자 (예: TC_001)")
    tc_title: str = Field(..., description="테스트 케이스 제목")
    steps: List[AnyIR] = Field(..., description="순차적으로 실행될 단계별 IR 목록")
```

### JSON Data Payload 예시 (Adapter Stdin)

Core Engine은 Pydantic 모델의 `model_dump_json()` 메서드를 호출하여 아래와 같은 순수 JSON 문자열을 어댑터에 밀어넣습니다.

```json
{
  "tc_id": "SYS_TEST_01",
  "tc_title": "고속도로 정속 주행 시나리오",
  "steps": [
    {
      "step_id": 1,
      "type": "SET",
      "original_text": "시동을 켠다.",
      "logical_signal": "Ignition_Status",
      "value": "ON"
    },
    {
      "step_id": 2,
      "type": "WAIT",
      "original_text": "엔진 안정화를 위해 3초 대기.",
      "duration_sec": 3.0
    },
    {
      "step_id": 3,
      "type": "CHECK",
      "original_text": "엔진 켜졌는지 점검.",
      "logical_signal": "Ignition_Status",
      "operator": "==",
      "expected_value": "ON"
    },
    {
      "step_id": 4,
      "type": "UNKNOWN",
      "original_text": "초사이언 모드로 전환한다.",
      "reason": "VectorDB match failed."
    }
  ]
}
```

---

## 4. 어댑터 파싱 규칙 검증 (Validation Protocol)

Adapter 프로세스는 위 JSON을 받아 다음과 같이 Pydantic을 이용해 **역직렬화(Deserialize)** 하여 처리합니다. 이 과정에서 타입이 맞지 않거나 필수 필드가 없으면 즉시 에러(`ValidationError`)를 뱉어내어 잘못된 타겟 코드 생성을 원천 차단합니다.

```python
# Adapter 내 코드 일부 (미리보기)
import sys
import json
from pydantic import TypeAdapter

# stdin으로 JSON 문자열 확보
raw_json_str = sys.stdin.read()

# AnyIR 리스트로 역직렬화 (Pydantic 2.0 권장 방식)
adapter = TypeAdapter(TestCaseIR)
parsed_tc = adapter.validate_json(raw_json_str)

def render_step(step, indent="    "):
    if step.type == IRType.SET:
        return f"{indent}simva.set({step.logical_signal}, {step.value})"
    
    elif step.type == IRType.WAIT:
        return f"{indent}time.sleep({step.duration_sec})"
        
    elif step.type == IRType.MACRO_CALL:
        # 사용자 정의 함수를 그대로 출력 (상단에 import 필수)
        args_str = ", ".join(f"{k}={v}" for k, v in step.arguments.items()) if step.arguments else ""
        return f"{indent}{step.macro_name}({args_str})"
        
    elif step.type == IRType.LOOP:
        # 'for' 루프 텍스트 렌더링 후, body 안의 내용들을 재귀적으로 들여쓰기 추가하여 변환
        loop_code = f"{indent}for _ in range({step.count}):\n"
        for child_step in step.body:
            loop_code += render_step(child_step, indent + "    ") + "\n"
        return loop_code.rstrip()
        
    elif step.type == IRType.UNKNOWN:
        return f"{indent}# FIXME: {step.original_text} (Reason: {step.reason})"

# 실제 변환 실행
for step in parsed_tc.steps:
    print(render_step(step))
```

### 4.1. 왜 이렇게 분리했는가? (LLM Code Generation vs Direct Translation)

가장 핵심적인 아키텍처 의사결정 중 하나는 **"LLM에게 프롬프트로 타겟 코드를 직접 짜게 시키지 않는다"**는 것입니다.

만약 LLM이 `simva.set(...)` 코드를 직접 텍스트로 생성하도록 프롬프트를 작성하면 다음과 같은 치명적인 문제가 발생합니다.
1. **환각(Hallucination)**: LLM이 가끔 `simva.set_value()` 처럼 존재하지 않는 API 함수를 창조하여 문법 오류(Syntax Error)를 유발합니다. 아무리 프롬프트를 정교하게 깎아도 완벽한 통제가 불가능합니다.
2. **타겟 확장성(Scalability) 부족**: 현재는 파이썬(simva)을 쓰지만, 나중에 C# 기반의 다른 테스트 자동화 툴(CAPL 등)을 지원해야 할 경우 LLM 프롬프트와 RAG 로직 전체를 갈아엎어야 합니다.

이를 해결하기 위해 **Direct Translation (직접 변환) 패턴**을 채택했습니다:
- **Core Engine (LLM)**: 코딩은 전혀 하지 않고, 오직 "의도(Intent) 파악"과 "도메인 규칙(Ontology) 매핑"만 수행하여 중립적인 JSON (IR 객체)만 만들어냅니다.
- **Adapter (Python)**: LLM이 개입하지 않고, 위 예시처럼 철저하게 하드코딩된 `if-else` 분기문을 통해 JSON(`IRType.SET`)을 `simva.set(...)` 이라는 정해진 포맷의 문자열로 안전하고 100% 문법적으로 완벽하게 찍어냅니다. (CAPL 지원을 원하면 이 어댑터 파일만 `setSignal(...)` 문자열을 출력하는 로직으로 갈아끼우면 됩니다.)

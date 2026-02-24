from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union, List, Annotated, Literal
from enum import Enum

class IRType(str, Enum):
    SET = "SET"               # 값 설정 (Action)
    CHECK = "CHECK"           # 상태 확인 (Verification)
    WAIT = "WAIT"             # 대기 (Delay)
    MACRO_CALL = "MACRO_CALL" # 사용자 정의 함수(매크로) 호출
    MACRO_DEF = "MACRO_DEF"   # 사용자 정의 함수(매크로) 정의
    CONDITION = "CONDITION"   # 조건문 (if-elif-else)
    LOOP = "LOOP"             # 반복문
    SEQUENCE = "SEQUENCE"     # 다중 동작 래퍼 (Multi-action)
    COMPLEX_LOGIC = "COMPLEX_LOGIC" # 복잡한 제어 로직 (LLM 직접 처리용)
    UNKNOWN = "UNKNOWN"       # 파싱 실패

class BaseIR(BaseModel):
    step_id: int = Field(0, description="TC 내의 단계 번호 (1-indexed)")
    type: IRType = Field(..., description="IR의 유형")
    original_text: str = Field("", description="매핑된 원본 TC 자연어 문장")
    description: Optional[str] = Field(None, description="어댑터가 코드로 변환 시 주석으로 추가할 설명")

class SetIR(BaseIR):
    type: Literal[IRType.SET] = IRType.SET
    logical_signal: str = Field(..., description="Vector DB에서 매핑된 표준 논리적 시그널 명")
    value: Union[int, float, str, bool] = Field(..., description="설정할 제어 값")
    unit: Optional[str] = Field(None, description="값의 단위 (예: km/h, rpm)")

class Operator(str, Enum):
    EQ = "=="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="

class CheckIR(BaseIR):
    type: Literal[IRType.CHECK] = IRType.CHECK
    logical_signal: str = Field(..., description="검증할 표준 논리적 시그널 명")
    operator: Operator = Field(Operator.EQ, description="비교 연산자 (기본값: ==)")
    expected_value: Union[int, float, str, bool] = Field(..., description="기대하는 값")
    duration_sec: Optional[float] = Field(None, description="해당 상태를 유지/확인할 시간 (초)")
    check_type: Literal["is", "keep", "turn"] = Field("is", description="검증 유형 (is: 즉시, keep: 유지, turn: 변화)")

    @field_validator('operator', mode='before')
    @classmethod
    def validate_operator(cls, v):
        if v == "=":
            return "=="
        return v

class WaitIR(BaseIR):
    type: Literal[IRType.WAIT] = IRType.WAIT
    duration_sec: float = Field(..., description="대기할 시간 (초 단위로 정규화)")

class MacroCallIR(BaseIR):
    type: Literal[IRType.MACRO_CALL] = IRType.MACRO_CALL
    macro_name: str = Field(..., description="호출할 매크로/함수 명")
    arguments: Optional[dict] = Field(None, description="함수에 전달할 인자 맵")

class LoopIR(BaseIR):
    type: Literal[IRType.LOOP] = IRType.LOOP
    count: int = Field(..., description="반복 횟수")
    body: List['AnyIR'] = Field(..., description="반복해서 실행할 IR 배열 (재귀적 구조)")

class SequenceIR(BaseIR):
    type: Literal[IRType.SEQUENCE] = IRType.SEQUENCE
    actions: List['AnyIR'] = Field(..., description="순차적으로 실행할 다중 동작 IR 배열")

class ConditionIR(BaseIR):
    type: Literal[IRType.CONDITION] = IRType.CONDITION
    condition_text: str = Field(..., description="조건식 설명 (예: '시속이 0인 경우')")
    condition_signal: Optional[str] = Field(None, description="조건을 검사할 논리 시그널 명")
    condition_operator: Optional[Operator] = Field(None, description="비교 연산자")
    condition_value: Optional[Union[int, float, str, bool]] = Field(None, description="비교 대상 값")
    if_body: List['AnyIR'] = Field(..., description="조건 만족 시 실행할 단계")
    else_body: Optional[List['AnyIR']] = Field(None, description="조건 미만족 시 실행할 단계")

class MacroDefinitionIR(BaseIR):
    type: Literal[IRType.MACRO_DEF] = IRType.MACRO_DEF
    macro_name: str = Field(..., description="정의할 매크로/함수 명")
    category: Literal["precondition", "method", "check", "cleanup"] = Field(..., description="함수가 속할 모듈 카테고리")
    parameters: Optional[List[str]] = Field(None, description="함수의 파라미터 목록")
    body: List['AnyIR'] = Field(..., description="함수 내부 로직")

class ComplexLogicIR(BaseIR):
    """
    정형화된 IR로 표현하기 어려운 복잡한 로직을 담기 위한 모델.
    어댑터 수준의 LLM(Smart Adapter)이 이 텍스트를 보고 타겟 코드를 직접 생성함.
    """
    type: Literal[IRType.COMPLEX_LOGIC] = IRType.COMPLEX_LOGIC
    instruction: str = Field(..., description="구현해야 할 로직에 대한 자연어 지시어")
    context_signals: Optional[List[str]] = Field(None, description="로직과 관련된 시그널 목록")

class UnknownIR(BaseIR):
    type: Literal[IRType.UNKNOWN] = IRType.UNKNOWN
    reason: str = Field(..., description="실패 사유 (에러 메시지 등)")

# Pydantic Discriminator Union
AnyIR = Union[
    SetIR, CheckIR, WaitIR, MacroCallIR, MacroDefinitionIR, 
    ConditionIR, LoopIR, SequenceIR, ComplexLogicIR, UnknownIR
]
AnyIR = Annotated[AnyIR, Field(discriminator='type')]

# Rebuild models for recursive structures
LoopIR.model_rebuild()
ConditionIR.model_rebuild()
MacroDefinitionIR.model_rebuild()
SequenceIR.model_rebuild()

class TestCaseIR(BaseModel):
    tc_id: str = Field(..., description="테스트 케이스 식별자 (예: TC_001)")
    tc_title: str = Field(..., description="테스트 케이스 제목")
    steps: List[AnyIR] = Field(..., description="순차적으로 실행될 단계별 IR 목록")

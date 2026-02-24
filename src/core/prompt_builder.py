import json

class PromptBuilder:
    """
    RAG에서 얻은 Context 정보와 사용자 입력 TC 텍스트를 결합하여
    LLM에 던질 최종 프롬프트를 동적으로 조립하는 클래스입니다.
    """
    
    @staticmethod
    def get_system_prompt() -> str:
        return """당신은 자동차 도메인 테스트 스크립트의 "중간 표현(Intermediate Representation, IR)"을 생성하는 전문 AI 오라클입니다. 
당신의 유일한 임무는 사용자의 자연어 테스트 스텝을 분석하여 지정된 JSON 스키마에 맞는 JSON 배열(List)을 반환하는 것입니다. 
하나의 스텝에 여러 동작이 포함되어 있다면 순서대로 배열에 담고, 단일 동작이라도 반드시 JSON 배열([ {...} ]) 형태로 반환하십시오.
마크다운 포맷(```json ...)이나 코드, 설명, 인사말을 절대 포함하지 마십시오. 오직 대괄호로 시작하는 파싱 가능한 JSON 리스트만 반환하십시오.

# IR JSON Schema Types:
- SET: 시그널 값을 변경할 때 (필드: type="SET", logical_signal, value)
  * 필수 주의: value 필드에는 절대 딕셔너리(`{"type": "int", "value": 10}`) 구조를 쓰지 말고, 원시 값(10, 50.5, "ON", true 등)을 직접 입력하세요.
- CHECK: 상태를 확인할 때 (필드: type="CHECK", logical_signal, operator, expected_value, duration_sec)
  * 필수 주의: expected_value 필드에도 절대 딕셔너리 구조를 쓰지 말고 원시 값을 직접 넣으세요.
  * 중요: 비교 연산자(operator)는 '=' 대신 반드시 '=='를 사용하십시오.
- WAIT: 대기할 때 (필드: type="WAIT", duration_sec)
- CONDITION: 조건부 실행 (필드: type="CONDITION", condition_text-자연어설명, condition_signal-검사할시그널명, condition_operator-연산자(==,!= 등), condition_value-비교값, if_body-IR배열, else_body-IR배열(옵션))
- LOOP: 반복 실행 (필드: type="LOOP", count-횟수, body-IR배열)
- MACRO_CALL: 복합 함수를 호출할 때 (필드: type="MACRO_CALL", macro_name)
- UNKNOWN: 해석 불가 또는 논리적 오류 발생 시 (필드: type="UNKNOWN", reason)

# Rules:
1. 제공되는 [CONTEXT] 영역의 RAG 데이터를 최우선으로 신뢰하여 logical_signal을 선택하십시오.
2. CONDITION이나 LOOP 내의 'body' 및 'if_body' 필드는 다른 IR 객체들을 포함하는 리스트(Array)입니다. 재귀적 중첩이 가능합니다.
3. 도메인 제약조건(Ontology Validation)에서 위반 사항이 있다면, 절대로 SET 명령을 만들지 말고 UNKNOWN 타입으로 분류한 후 reason에 위반 사유를 명시하십시오.
4. 중첩된 단계(CONDITION/LOOP 내부)에서도 핵심 필드인 `logical_signal`, `value`, `operator`, `expected_value`는 반드시 정확한 값으로 채워야 합니다. 식별이 불가능하다면 해당 단계를 UNKNOWN으로 분류하십시오. 빈 문자열("")로 남겨두지 마십시오.
5. 프롬프트 내의 안내용 헤더(예: ### Vector DB Match Results, [CONTEXT] 등) 명칭을 절대 실제 데이터(시그널 명 등)로 사용하지 마십시오. 적절한 시그널을 찾을 수 없다면 임의로 지어내지 말고 해당 단계를 UNKNOWN 유형으로 분류하십시오.
6. 시그널 값(value)은 [CONTEXT]에 제공된 Data Type에 맞게 변환하십시오 (예: enum 일 경우 해당 문자열로).
7. '발생시킨다', '출력한다', '경고를 준다', '알람을 발생시킨다' 등의 표현은 CONDITION이나 LOOP 내에서도 반드시 SET 또는 MACRO_CALL로 분류하십시오. 절대로 simva.warn(), simva.alert() 등 존재하지 않는 함수를 생성하지 마십시오. 시그널을 특정할 수 없다면 UNKNOWN으로 처리하십시오.
8. (필수) "~인 경우", "~(하)면", "If"와 같이 조건절이 있거나 "~면 ~하고, 그렇지 않으면 ~한다" 구조일 경우, 최상위 항목을 `CONDITION` 타입으로 분류하십시오. 조건 만족 시 동작은 `if_body`에, 불만족 시 동작(그렇지 않으면)은 `else_body`에 넣으십시오. 특히 "**~인 경우**"는 명확한 조건문으로 간주해야 합니다. 단순한 조건없는 SET(할당)으로 최상위에 나열하는 실수를 하지 마십시오.
    - 예시 1: `차속이 10 이상이면 잠그고, 그렇지 않으면 해제한다` -> `[{{"type": "CONDITION", "condition_text": "차속이 10 이상이면", "condition_signal": "VehicleSpeed", "condition_operator": ">=", "condition_value": 10, "if_body": [{{"type": "SET", "logical_signal": "Door_Status", "value": "CLOSED"}}], "else_body": [{{"type": "SET", "logical_signal": "Door_Status", "value": "OPEN"}}]}}]`
    - 예시 2: `시동이 ON인 경우 헤드램프를 켠다` -> `[{{"type": "CONDITION", "condition_text": "시동이 ON인 경우", "condition_signal": "Ignition_Status", "condition_operator": "==", "condition_value": "ON", "if_body": [{{"type": "SET", "logical_signal": "HeadLamp_Status", "value": "LOW"}}]}}]`
9. (매우 중요) 입력 텍스트가 `(Key = Value)` 형식이거나 명시적인 상태 확인(Check/Verify) 지시가 없을 때 (단, Rule 8의 조건문은 예외), `=` 연산자는 항상 해당 키에 값을 할당하는 `SET` 동작으로 해석하십시오. 절대 상태를 확인하는 `CHECK` 로 오해하지 마십시오.
    - 예시 1: `(VehicleSpeed = 50)` -> `[{{"type": "SET", "logical_signal": "VehicleSpeed", "value": 50}}]`
    - 예시 2: `(Lamp_LightSwSta = On)` -> `[{{"type": "SET", "logical_signal": "Lamp_LightSwSta", "value": "On"}}]`
    - 단, "현재 차량 속도가 10 km/h인지 확인한다." 처럼 명시적으로 "확인한다"라고 검증을 지시하는 문장은 절대 `CONDITION`이나 `SET`이 아닌 `CHECK` 타입으로 반환하십시오.
      -> `[{{"type": "CHECK", "logical_signal": "VehicleSpeed", "operator": "==", "expected_value": 10}}]`
10. (다중 동작 시퀀스 래퍼) "A하고 B한다" (예: "속도를 10으로 설정하고 1초 대기한다")처럼 한 문장에 두 개 이상의 독립적인 동작(설정, 대기 등)이 있다면, 반드시 `type: "SEQUENCE"` 단일 객체로 반환하고 내부 `actions` 배열 필드에 개별 동작들을 담으십시오. 
    - **[절대 금지]**: 하나의 `SET` 객체 안의 `duration_sec` 속성에 대기 시간을 넣고 병합하는(Merge) 행위는 엄격히 금지됩니다. (예: `type: SET`과 `duration_sec`는 절대 한 객체에 공존할 수 없습니다.)
    - 예시 1: `(5초 후 KEY_IN)` -> `[{{"type": "SEQUENCE", "actions": [{{"type": "WAIT", "duration_sec": 5.0}}, {{"type": "SET", "logical_signal": "KEY_IN", "value": "ON"}}]}}]`
    - 예시 2: `차량 속도를 10으로 설정하고 1초 대기한다.` -> `[{{"type": "SEQUENCE", "actions": [{{"type": "SET", "logical_signal": "VehicleSpeed", "value": 10}}, {{"type": "WAIT", "duration_sec": 1.0}}]}}]`
11. (반복 동작 처리) 텍스트에 "반복한다(repeat)", "~회 수행" 등의 명시적인 반복 지시가 있는 경우, 반드시 최상위를 `LOOP` 타입으로 분류하십시오. 반복 횟수가 명시되어 있으면 `count` 필드에, 조건 기반이면 `condition` 필드에 기록하십시오. 반복할 동작이 여러 개라면 `body` 내부에 `SEQUENCE`를 넣거나 동작들을 배열로 나열하십시오.
    - 예시: `와이퍼를 LOW로 설정하고 2초 대기하는 동작을 3회 반복한다.` -> `[{{"type": "LOOP", "count": 3, "body": [{{"type": "SEQUENCE", "actions": [{{"type": "SET", "logical_signal": "Wiper_Status", "value": "LOW"}}, {{"type": "WAIT", "duration_sec": 2.0}}]}}]}}]`
    - 단, 명시적 반복 지시가 없다면 절대 임의로 상위 `LOOP` 블록을 만들지 마십시오.
12. (임의 대기 생성 금지) 입력 텍스트에 "대기", "초 후", "Wait" 등 명시적인 지시가 없는 한, 절대로 임의의 `WAIT` 동작이나 1초 대기를 추가하지 마십시오. 텍스트에 명시된 동작만 충실히 JSON으로 변환하십시오.
"""
    
    @classmethod
    def build_prompt(cls, user_text: str, rag_signals: list, rag_rules: list) -> str:
        """
        :param user_text: 원본 TC 텍스트 스텝 (예: "엑셀 10% 밟아라")
        :param rag_signals: Vector DB에서 찾은 시그널 매핑 리스트
        :param rag_rules: Ontology 기반으로 검증한 현재 상황/제약 조건 메시지 등
        """
        
        # 1. Context 영역 조립
        context_str = "[CONTEXT]\n"
        
        # Vector DB 매칭 결과 삽입
        if rag_signals:
            context_str += "### Vector DB Match Results (권장 시그널 후보):\n"
            for sig in rag_signals:
                context_str += (
                    f"- Logical Signal: {sig['logical_name']} "
                    f"(Type: {sig['data_type']}, Allowed: {sig['allowed_values']})\n"
                    f"  Description: {sig['description']}\n"
                )
        else:
            context_str += "### Vector DB Match Results:\n- 검색된 맵핑 시그널이 없습니다. 시스템이 해석할 수 없다면 UNKNOWN을 반환하세요.\n"
            
        # Ontology 룰 결과 삽입
        if rag_rules:
            context_str += "\n### Ontology Pre-condition Rules:\n"
            for rule in rag_rules:
                desc = rule.get('description', '')
                context_str += (
                    f"- 주의사항 (관련 시그널: {rule.get('source')}): {desc}\n"
                )
                
        # 2. Few-shot & Instruction 영역 조립
        instruction_str = f"""
[INSTRUCTION]
위 규칙 및 문맥 데이터를 바탕으로 아래 [Target Step]에 대한 IR JSON 배열(List)을 반환하세요.
현재 처리 중인 텍스트는 테스트 시나리오의 "시험 방법(Action Phase)"에 해당하는 데이터입니다. 명시적인 확인/검증 지시가 없는 한 값을 설정(SET)하는 동작으로 해석하십시오.

# Target Step
Text: "{user_text}"

생성 결과(JSON):
"""
        # 최종 프롬프트 결합
        return context_str + instruction_str

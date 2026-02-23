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

# Target Step
Text: "{user_text}"

생성 결과(JSON):
"""
        # 최종 프롬프트 결합
        return context_str + instruction_str

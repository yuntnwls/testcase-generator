# 주제 1: LLM 자기 수정(Self-Correction) 설계

이 문서는 LLM 응답의 신뢰성을 높이기 위한 자동 검증 및 재시도 메커니즘을 정의합니다.

## 핵심 메커니즘: Pydantic 기반 검증 루프

LLM이 생성한 JSON이 정의된 IR(중간 표현) 스키마를 따르지 않을 경우, 시스템은 에러 메시지를 포함하여 LLM에게 재수정을 요청합니다.

### 프로세스 흐름
1. **Initial Prompt**: 사용자 텍스트 + RAG 컨텍스트를 LLM에 전달.
2. **LLM Output**: LLM이 JSON 문자열을 반환.
3. **Pydantic Validation**: `IRAdapter.validate_python()`을 통해 스키마 검사.
4. **Error Handling**:
    - **통과 시**: 최종 IR 객체 반환.
    - **실패 시**: 발생한 `ValidationError` 상세 내용을 포함하여 Prompt 재구성 후 최대 3회 재시도.
5. **Fallback**: 모든 재시도 실패 시 `UnknownIR` 객체를 생성하여 시스템 중단을 방지.

## 구현 상세 (`engine.py`)

```python
for attempt in range(self.max_retries):
    try:
        raw_json = self.llm.generate(current_prompt)
        parsed_dict = json.loads(raw_json)
        # Pydantic을 이용한 강제 스키마 검증
        return self.ir_adapter.validate_python(parsed_dict)
    except ValidationError as ve:
        # 에러 내용을 피드백으로 사용하여 Prompt 업데이트
        current_prompt += f"\n\nERROR: {str(ve)}\nPlease fix the JSON format."
```

## 기대 효과
- **데이터 무결성**: 어댑터 단계로 넘어가기 전 완벽한 형태의 데이터 보장.
- **유연성**: 단순한 정규표현식 검사보다 복잡한 제약 조건(온톨로지 등) 검증 가능.

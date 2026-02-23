# 주제 3: 로깅 및 추적성(Traceability) 설계

이 문서는 복잡한 변환 과정에서 발생하는 문제를 진단하기 위한 구조화된 로깅 아키텍처를 정의합니다.

## 핵심 도구: `structlog`

단순 텍스트 로그 대신, 검색과 분석이 용이한 JSON 형태의 구조화된 로깅을 사용합니다.

### Trace ID 시스템
- 모든 TC 변환 요청마다 고유한 `trace_id` (UUID)를 생성합니다.
- 이 ID는 파싱, RAG 검색, LLM 호출, 어댑터 실행에 이르는 모든 단계의 로그에 포함됩니다.

## 로그 구조 예시
```json
{
  "event": "Starting TC conversion",
  "level": "info",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "tc_id": "TC_001",
  "step_count": 5,
  "timestamp": "2026-02-23T10:00:00Z"
}
```

## 구현 전략
- **Contextual Logging**: `logger.bind(trace_id=...)`를 사용하여 특정 컨텍스트 내의 모든 로그에 ID를 자동 삽입.
- **UI 연동**: 엔진이 로그 데이터를 Generator를 통해 Yield 하면, Streamlit UI가 이를 실시간으로 사용자에게 시각화.
- **에러 추적**: 예외 발생 시 스택 트레이스 대신 `trace_id`를 사용자에게 제공하여, 개발자가 로그 파일에서 상세 원인을 즉시 검색할 수 있도록 함.

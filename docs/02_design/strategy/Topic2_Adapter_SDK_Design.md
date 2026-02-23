# 주제 2: 어댑터 SDK 및 통신 프로토콜 설계

이 문서는 메인 엔진과 타겟 언어별 어댑터(Subprocess) 간의 데이터 교환 방식을 정의합니다.

## 아키텍처: 서브프로세스 파이프라인

메인 엔진은 특정 언어에 종속되지 않기 위해, 각 어댑터를 별도의 프로세스로 실행하고 표준 입출력(STDIN/STDOUT)을 통해 통신합니다.

### 통신 프로토콜
- **Input (STDIN)**: `TestCaseIR`의 전체 JSON 데이터.
- **Output (STDOUT)**: 최종 생성된 타겟 스크립트 코드.
- **Feedback (STDERR)**: 진행 상황(`[PROGRESS] 1/10`) 및 에러 정보(`[ERROR] ...`).

## 어댑터 베이스 클래스 (`BaseAdapter`)

모든 어댑터는 다음 추상 인터페이스를 구현해야 합니다:
- `generate_header()`: 함수 정의 및 초기화 코드 생성.
- `translate_step(ir_step)`: 개별 IR 단계를 타겟 코드로 변환.
- `generate_footer()`: 마무리 코드 생성.

## 실행 제어 흐름
1. `CoreEngine`이 `TestCaseIR` 객체를 JSON으로 직렬화.
2. `subprocess.Popen`을 통해 전용 어댑터(예: `simva_adapter.py`) 실행.
3. JSON 데이터를 어댑터의 STDIN으로 전달.
4. 어댑터가 코드를 생성하여 STDOUT으로 반환하면, 엔진이 이를 수집하여 사용자에게 전달.

## 장점
- **격리성**: 특정 어댑터의 런타임 에러가 메인 엔진 전반에 영향을 주지 않음.
- **확장성**: 새로운 언어(CAPL, C# 등) 추가 시 엔진 수정 없이 어댑터 파일만 추가하면 됨.

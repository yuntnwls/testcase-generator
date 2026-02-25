# 📊 세미나 발표 화면 흐름 가이드 (Presentation Flow)

> 본 문서는 별도의 PPT 슬라이드 없이 마크다운 문서 내용과 터미널 화면만으로 세미나를 진행하기 위한 화면 전환(비주얼) 흐름도입니다. 발표 시 이 순서대로 뷰어 화면을 띄워놓고 대본([seminar_speaker_script.md](seminar_speaker_script.md))과 매칭하여 진행합니다.

---

## [도입] Title & 배경 (Screen 1~3)

### Screen 1: 타이틀 및 개요
*   **표시 화면**: [README.md](../../README.md) (프로젝트 메인 화면) 최상단 타이틀 영역
*   **강조 포인트**: "LLM과 RAG 실전 도입기", "97% 비용 절감과 환각 제로" 등 프로젝트 핵심 성과 키워드

### Screen 2: 문제 정의 (왜 이 프로젝트를 시작했는가?)
*   **표시 화면**: 요구사항 문서 또는 기존 엑셀(VS Code CSV 뷰어 등) 형태의 수동 작성 케이스 화면
*   **강조 포인트**: 기존 수동 C# 코드 변환 작업의 지루한 병목 현상 및 휴먼 에러 발생 가능성

### Screen 3: 달콤했던 첫 번째 착각 "LLM이 다 해주겠지"
*   **표시 화면**: 화면을 빈 캔버스로 두거나 [docs/02_design/README.md](../02_design/README.md)의 도입 부분
*   **강조 포인트**: "단순 프롬프트 + LLM = 완벽한 코드가 나올 것"이라는 초기 구상의 순진함과 패착

---

## [Phase 1] 좌절: 방안 A (Naive RAG)의 한계 (Screen 4~5)

### Screen 4: 방안 A - Naive RAG 아키텍처 (초기 설계)
*   **표시 화면**: [docs/02_design/README.md](../02_design/README.md) (초기 아키텍처 다이어그램/개요 부분)
*   **강조 포인트**: 입력 -> JSON(IR) 변환 -> RAG 검색 -> 코드 생성으로 이어지는 논문형 기본 구조

### Screen 5: 프로덕션(Production)의 벽 & 핵심 교훈
*   **표시 화면**: 관련 성과표 마크다운 위치 또는 발표자 시선 고정 처리
*   **강조 포인트**: TC 100개 무지성 변환 시 **230만 토큰** 소모, 환각(Hallucination) 빈발에 따른 검증 실패 문제 극심화
*   **Lesson 1**: 확률적 모델(LLM)에게 확정적 로직(코드 문법 생성)을 단독으로 맡길 수 없다.

---

## [Phase 2] 각성: 방안 B (Direct Synthesis) (Screen 6~8)

### Screen 6: 아키텍처 대수술 "LLM 호출을 빼라!"
*   **표시 화면**: [docs/02_design/architecture_design.md](../02_design/architecture_design.md) (방안 B 파이프라인 구조도)
*   **강조 포인트**: 거대한 1개의 LLM 프롬프트 병목을 지우고 컴포넌트를 분할 합성(Direct Synthesis)하는 흐름 전환

### Screen 7: 3-Tier Extractor의 탄생
*   **표시 화면**: [docs/02_design/3_tier_extractor_design.md](../02_design/3_tier_extractor_design.md) 문서 상세화면 영역
*   **강조 포인트**: 단계별 방어막(1차 Regex, 2차 LCS)을 통한 100% 결정론적 변수 추출 연산 기법 (토큰 비용이 발생하지 않는 0원 구간)

### Screen 8: 방안 B의 성능 향상 및 남은 숙제
*   **표시 화면**: 터미널 연출, 또는 오류 예시가 적힌 가이드 화면
*   **강조 포인트**: 토큰 94% 절약. 단, "앞창문 닦개 불 올려"와 같은 현장의 다양한 은어 대응에서는 단순 RAG 텍스트 매칭이 박살 나면서 에러 터짐.

---

## [Phase 3] 완성: 방안 C (Contextual RAG) (Screen 9~12)

### Screen 9: RAG의 근본적 한계와 해결 (Contextual RAG)
*   **표시 화면**: [docs/04_contextual_rag_design/README.md](../04_contextual_rag_design/README.md) (방안 C 아키텍처 개요)
*   **강조 포인트**: 비싼 연산을 실시간(Runtime) 응답에서 오프라인(Offline 배치) 단계로 강제 이동시켜 버리는 설계 역전 철학

### Screen 10: 런타임 속도를 방어하는 3대 컴포넌트 집중 조명
*   **표시 화면**: [docs/04_contextual_rag_design/](../04_contextual_rag_design/) 하위 개념 설명 파트
*   **강조 포인트**: 
    1. 이중 비용 방어를 위한 **LRU Pattern Cache**
    2. 동사의 의도(Action)와 목적어 대상(Signal)을 분리하여 정확도를 올리는 **2-Step RAG 모델**
    3. Graph Hop을 통한 휴먼 룰(제약사항) 주입 메커니즘

### Screen 11: 토큰 다이어트의 정수, Error Compressor
*   **표시 화면**: [docs/04_contextual_rag_design/rescue_flow_design.md](../04_contextual_rag_design/rescue_flow_design.md) (Error Context Compressor 부분)
*   **강조 포인트**: 파이썬 `ast` 모듈을 이용한 에러 지점 위아래 3줄짜리 압축 압착 처리로 자가 수정(Self-Correction) 연체 비용을 극한치인 90% 추가 절감

### Screen 12: 최종 아키텍처 성과 스탯
*   **표시 화면**: 결과 종합 테이블 / 비용 비교표 마크다운 위치 노출
*   **강조 포인트**: 97.1% 연산 파괴, 환각 오류 제로 0%에 근접하는 전례 없는 엔터프라이즈 레벨 성공률 달성

---

## [Live Demo] 방안 C 투스텝 RAG 액션 시연 (Screen 13)

### Screen 13: 라이브 데모 실행 화면 분할 영역
*   **화면 분할 뷰어링**: 좌측 프레임 - 하단 **터미널 실행창** / 우측 프레임 - **[docs/05_seminar_materials/demo_scenario_guide.md](demo_scenario_guide.md)** 가이드 화면
*   **실행 명령어 (좌측)**: `python docs/05_seminar_materials/demo/demo_cli_app.py`
*   **진행 포인트**: 우측의 [demo_scenario_guide.md](demo_scenario_guide.md)를 띄워 청중들이 데모 스텝(1단계 Vector 의도 추출 -> 2단계 Ontology 조건 매핑 -> 조립 및 완성) 진행 파트를 육안 활자로 직접 쫓아가도록 자연스럽게 시야 유도.

---

## [마무리] Lesson Learned & QnA (Screen 14)

### Screen 14: 배운 점 핵심 요약 및 질의응답 (Takeaways)
*   **표시 화면**: 메인 화면 혹은 QnA 관련 마크다운 최하단
*   **강조 포인트**:
    1. LLM은 메인 파이낸스 로직이 아닌 안전 장치(Fallback)용 유격수로 써라.
    2. 정규식(Regex)/Rule-based/Cache 파이프라인 같은 고전 알고리즘들의 파괴력.
    3. 복잡한 추론/맥락화 작업은 반드시 실시간(Online)이 아닌 오프라인(Offline) 아키텍처로 분리할 것.

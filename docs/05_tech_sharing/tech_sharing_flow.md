# 📊 기술 공유 흐름 (Presentation Flow)

## [도입] Title & 배경 (Screen 1~3)

### Screen 1: 타이틀 및 개요
*   [README.md](../../README.md) 최상단 타이틀 영역 분할 화면
*   **인사 및 주제 소개**: "LLM과 RAG 기술 실전 도입 경험 공유"
*   **핵심 키워드**: "처절한 실패", "아키텍처 3단계 진화", "97% 비용 절감", "환각 제로"

### Screen 2: 문제 정의 (왜 이 프로젝트를 시작했는가?)
*   요구사항 문서 또는 기존 엑셀(VS Code CSV 뷰어 등) 형태의 수동 작성 케이스 화면
*   **기존 문제점**: 자연어 엑셀 TC 수동 변환 과정의 지루함 및 휴먼 에러 지속 발생
*   **프로젝트 목표**: LLM을 활용한 코딩(파이썬 테스트 스크립트 작성) 완전 무인 자동화 달성

### Screen 3: 달콤했던 첫 번째 착각 "LLM이 다 해주겠지"
*   [docs/02_design/README.md](../02_design/README.md)의 기획(도입) 부분
*   **초기 오판**: "프롬프트만 잘 짜면 최신 LLM이 완벽한 코드를 알아서 짜줄 것이다"

---

## [Phase 1] 좌절: 방안 A (Naive RAG)의 한계 (Screen 4~5)

### Screen 4: 방안 A - Naive RAG 아키텍처 (초기 설계)
*   [docs/02_design/README.md](../02_design/README.md)의 초기 아키텍처 다이어그램 및 개요
*   **방안 A 구조**: 논문 기반의 전형적인 RAG (TC 입력 -> JSON 형태 IR 변환 -> 검색 -> 코드 생성)

### Screen 5: 프로덕션(Production)의 벽 & 핵심 교훈
*   관련 성과표 마크다운 위치 화면 고정
*   소규모 데모는 성공적이었으나, 대규모 운영 환경에서는 실패
*   **TC 100개당 230만 토큰**이라는 천문학적 비용 발생
*   LLM의 확률적 특성으로 인한 잦은 **할루시네이션**(어제 맞던 코드가 오늘 틀림)
*   **Lesson 1**: "코드 생성(확정적 로직)을 LLM(확률적 모델)에게 온전히 맡기면 안 된다."

---

## [Phase 2] 각성: 방안 B (Direct Synthesis) (Screen 6~8)

### Screen 6: 아키텍처 대수술 "LLM 호출을 빼라!"
*   [docs/02_design/architecture_design.md](../02_design/architecture_design.md) 방안 B 파이프라인 구조도
*   **핵심 철학**: "최대한 LLM 호출을 빼자"
*   **Direct Synthesis**: 중간의 무거운 JSON 과정을 생략하고, 템플릿/정규식에 빈칸(매개변수) 직접 삽입

### Screen 7: 3-Tier Extractor의 탄생
*   [docs/02_design/3_tier_extractor_design.md](../02_design/3_tier_extractor_design.md) 시스템 상세 화면 영역
*   **3-Tier Extractor (비용 0원 구간)**:
    1.  100% 정확한 **정규식 매핑**
    2.  단어 및 글자 수를 맞추는 **LCS 정렬 알고리즘**
    3.  위 두 단계 실패 시에만 최후로 가장 저렴한 **SLM 호출** (전체 케이스의 10% 미만)

### Screen 8: 방안 B의 성능 향상 및 남은 숙제
*   비교표, 또는 오류 예시가 적힌 가이드 화면
*   **성과**: 토큰 연산 비용 **94% 절감** (230만 -> 13만 토큰)
*   **부작용(한계)**: 현장 생산 라인들의 다채롭고 극단적인 은어 사용 시 검색 붕괴 및 파이프라인 에러 터짐 현상 지속

---

## [Phase 3] 완성: 방안 C (Contextual RAG) (Screen 9~12)

### Screen 9: RAG의 근본적 한계와 해결 (Contextual RAG)
*   [docs/04_contextual_rag_design/README.md](../04_contextual_rag_design/README.md) 방안 C 아키텍처 개요
*   **기존 RAG 한계**: 표면적인 문장 단위 임베딩만으로는 맥락(Context)을 이해하지 못하는 맹점
*   **해결책 철학**: "비싸고 강력한 LLM 사고(Context) 과정을 런타임(실시간)에서 **오프라인(배치)**으로 옮기자"

### Screen 10: 런타임 속도를 방어하는 3대 컴포넌트 집중 조명
*   [docs/04_contextual_rag_design/](../04_contextual_rag_design/) 하위의 컴포넌트 설명 파트
*   **Contextual Indexer**: 야간 배치 전처리 작업을 통해 DB 스펙에 부연 설명(Context) 생성 후 임베딩 (검색 품질 극대화)
*   **런타임 비용 제로화 3대 방어막**:
    1.  **Pattern Cache (LRU)**: 캐시 히트로 LLM 스킵
    2.  **2-Step RAG**: 의도(Action)와 대상(Signal)의 검색층 완전 분리
    3.  **Error Context Compressor**: 토큰 다이어트 통제

### Screen 11: 토큰 다이어트의 정수, Error Compressor
*   [docs/04_contextual_rag_design/rescue_flow_design.md](../04_contextual_rag_design/rescue_flow_design.md) Error Context Compressor 파트
*   **Error Compressor 효과**: 수십~수백 줄의 Python 에러 Traceback 코드를 ast 모듈로 에러 지점 위아래 3줄로 핵심만 압축 (재진행 복구 비용 **90% 추가 절약**)

### Screen 12: 최종 아키텍처 성과 스탯
*   결과 종합 테이블 / 비용 비교표 마크다운 위치 노출
*   **최종 성과 (방안 C)**: 
    *   LLM 호출률: 100% -> **12% 감소**
    *   토큰 사용량: **97.1% 감소** (할루시네이션 사실상 제로 도달)
*   **결론**: "LLM의 가장 위대하고 훌륭한 사용법은 겹겹이 쳐진 확정적 알고리즘 방어막 가장 조용한 속 깊은 곳에 숨겨두는 것"

---

## [Live Demo] 방안 C 투스텝 RAG 액션 시연 (Screen 13)

### Screen 13: 라이브 데모 (Live)
*   **좌측 프레임 창**: 하단 터미널(`python docs/05_tech_sharing/demo/demo_cli_app.py` 실행 대기)
*   **우측 프레임 창**: **[demo_scenario_guide.md](demo_scenario_guide.md)** 시연 가이드
*   **데모 안내**: 2-Step RAG 모델의 자연어 추상화 및 제약 조건 병합, 최종 코드 생성 시연
*   **1단계 역할분담** (입력: `좌측 전조등을 켜라`): 자연어 문장을 외우지 않음. 입력된 사용자의 의도(Action API 템플릿)만 신속하게 추출
*   **2단계 역할분담 (Graph Hop)**: 단순 시그널 매칭을 넘어, 온톨로지 지식 그래프를 건너뛰며 사전 '제약 조건(휴먼 룰)' 자동 색인. 배터리 조건 등 제약 사항이 프롬프트에 자동 병합됨 (환각 방지 가드레일 작동 증명)
*   **비용 제로 매핑**: LLM 유입 전 티어1 정규식 파서가 파라미터를 결정론적으로 확정 짓는 고속 처리 구간 확인
*   **최종 코드 조립**: 부품(Action 템플릿 + 시그널 + Value + 제약조건)이 모두 모여 환각 없이 한 번에 정확한 코드를 합성
*   **로딩 속도 체감** (똑같은 문장 재입력 후 Pattern Cache HIT! 시각화): 3~4초 걸리던 인공지능 합성 작업이 LRU Cache Hit를 통해 밀리세컨드 단위 처리로 단축. **현장의 스펙 이력이 쌓일수록 스스로 더 빨라지며 사용 비용이 역으로 줄어드는 구조**

---

## [마무리] Lesson Learned & QnA (Screen 14)

### Screen 14: 배운 점 핵심 요약 및 질의응답
*   메인 화면 혹은 QnA 관련 마크다운 최하단
*   **최종 정리 (3 Takeaways)**:
    1.  **AI 포지셔닝**: LLM은 메인 로직이 아닌 최후의 수단(Fallback) 방어선으로 분리 배치하라.
    2.  **클래식의 힘**: 정규식, 룰 베이스, 캐시 시스템은 LLM과 결합할 때 비로소 최고의 파급력을 가지게 됨.
    3.  **비용 역전 설계**: 비싸고 무거운 문맥(Context) 임베딩 연산은 철저히 메인 앱 바깥의 독립된 오프라인 배치 시스템으로 격리하라.
*   **Q & A**

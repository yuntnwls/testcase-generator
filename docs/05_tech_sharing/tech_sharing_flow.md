# 📊 기술 공유 (Presentation Flow)

## 배경

### 1. 개요
*   [README.md](../../README.md) 최상단 타이틀 영역
*   **인사 및 주제 소개**: "LLM과 RAG 기술 실전 도입 경험 공유"
*   **핵심 키워드**: "처절한 실패", "아키텍처 3단계 진화", "97% 비용 절감", "환각 제로"

### 2. 문제 정의 (왜 이 프로젝트를 시작했는가?)
*   요구사항 문서 또는 기존 엑셀 형태의 수동 작성 케이스
*   **기존 문제점**: 자연어 엑셀 TC 수동 변환 과정의 지루함 및 휴먼 에러 지속 발생
*   **프로젝트 목표**: LLM을 활용한 코딩(파이썬 테스트 스크립트 작성) 자동화 달성

### 3. 첫 번째 착각 "LLM이 다 해주겠지"
*   [docs/02_design/README.md](../02_design/README.md)의 기능 정의 및 배경
*   **초기 오판**: "프롬프트만 잘 짜면 최신 LLM이 완벽한 코드를 알아서 짜줄 것이다"

---

## 방안 A (Naive RAG)의 한계

### 4. 방안 A - Naive RAG 아키텍처 (초기 설계)
*   [docs/02_design/README.md](../02_design/README.md)의 초기 아키텍처 다이어그램 및 개요
*   **방안 A 구조**: 논문 기반의 전형적인 RAG (TC 입력 -> JSON 형태 IR 변환 -> 검색 -> 코드 생성)

### 5. 프로덕션(Production)의 벽 & 핵심 교훈
*   관련 성과표 마크다운 위치 고정
*   소규모 데모는 성공적이었으나, 대규모 운영 환경에서는 실패
*   **TC 100개당 230만 토큰**이라는 천문학적 비용 발생
*   LLM의 확률적 특성으로 인한 잦은 **할루시네이션**(어제 맞던 코드가 오늘 틀림)
*   **Lesson 1**: "코드 생성(확정적 로직)을 LLM(확률적 모델)에게 온전히 맡기면 안 된다."

---

## 방안 B (Direct Synthesis)

### 6. 아키텍처 대수술 "LLM 호출을 줄여라!"
*   [docs/03_advanced_design/architecture_design.md](../03_advanced_design/architecture_design.md) 방안 B 파이프라인 구조도
*   **핵심 철학**: "최대한 LLM 호출을 줄이자"
*   **Direct Synthesis**: 중간의 무거운 JSON 과정을 생략하고, 템플릿/정규식에 빈칸(매개변수) 직접 삽입

### 7. 3-Tier Extractor의 탄생
*   [docs/04_contextual_rag_design/extractor_design.md](../04_contextual_rag_design/extractor_design.md) 시스템 상세 영역
*   **3-Tier Extractor (비용 0원 구간)**:
    1.  100% 정확한 **정규식 매핑**
    2.  단어 및 글자 수를 맞추는 **LCS 정렬 알고리즘**
    3.  위 두 단계 실패 시에만 최후로 가장 저렴한 **SLM 호출** (전체 케이스의 10% 미만)

### 8. 방안 B의 성능 향상 및 남은 숙제
*   **성과**: 토큰 연산 비용 **94% 절감** (230만 -> 13만 토큰)
*   **한계 (문맥의 부재)**: 단순 '문장 유사도' 검색은 도메인 은어나 상황별 중의적 표현에 취약함
    *   *예시*: `"좌전등 켜"` (입력) ↔ `"좌측 헤드램프 시그널 값을 설정한다"` (DB) 사이의 낮은 유사도 점수로 검색 실패
*   **결과**: 검색 실패 및 의도 오판으로 인한 잘못된 코드 생성 잔존

---

## 방안 C (Contextual RAG)

### 9. RAG의 근본적 한계와 해결 (Contextual RAG)
*   [docs/04_contextual_rag_design/README.md](../04_contextual_rag_design/README.md) 방안 C 아키텍처 개요
*   **해결책 (Contextual Indexing)**: DB 구축 시 LLM이 각 템플릿의 '사용 맥락'을 요약(`context_prefix`)하여 임베딩에 병합
    *   *효과*: `"좌전등"` 같은 은어도 `"차량 조명 제어 맥락"`이라는 배경지식을 통해 정석 템플릿과 높은 확률로 매칭 성공
*   **철학**: "비싸고 강력한 LLM 사고 과정을 런타임(실시간)이 아닌 **오프라인(배치)** 으로 미리 옮겨두자"

### 10. 런타임 속도를 방어하는 3대 컴포넌트 집중 조명
*   핵심 설계: Pattern Cache, Ontology Router, Rescue Flow
*   **Contextual Indexer**: 야간 배치 전처리 작업을 통해 DB 스펙에 부연 설명(Context) 생성 후 임베딩 (검색 품질 극대화)
*   **런타임 비용 제로화 3대 방어막**:
    1.  **Pattern Cache (LRU)**: [pattern_cache_design.md](../04_contextual_rag_design/pattern_cache_design.md) - 캐시 히트로 LLM 스킵
    2.  **2-Step RAG**: [ontology_router_design.md](../04_contextual_rag_design/ontology_router_design.md) - 의도(Action)와 대상(Signal)의 검색층 완전 분리
    3.  **Error Context Compressor**: [rescue_flow_design.md](../04_contextual_rag_design/rescue_flow_design.md) - 토큰 다이어트 통제

### 11. 토큰 다이어트의 정수, Error Compressor
*   [docs/04_contextual_rag_design/rescue_flow_design.md](../04_contextual_rag_design/rescue_flow_design.md) Error Context Compressor 파트
*   **Error Compressor 효과**: 수십~수백 줄의 Python 에러 Traceback 코드를 ast 모듈로 에러 지점 위아래 3줄로 핵심만 압축 (재진행 복구 비용 **90% 추가 절약**)

### 12. 최종 아키텍처 성과 스탯
*   결과 종합 테이블 / 비용 비교표 마크다운 위치 노출
*   **최종 성과 (방안 C)**: 
    *   LLM 호출률: 100% -> **12% 감소**
    *   토큰 사용량: **97.1% 감소** (할루시네이션 사실상 제로 도달)
*   **결론**: "LLM의 가장 위대하고 훌륭한 사용법은 겹겹이 쳐진 확정적 알고리즘 방어막 가장 조용한 속 깊은 곳에 숨겨두는 것"

---

## [마무리] Lesson Learned

### 14. 배운 점 핵심 요약
*   **최종 정리 (3 Takeaways)**:
    1.  **AI 포지셔닝**: LLM은 메인 로직이 아닌 최후의 수단(Fallback) 방어선으로 분리 배치하라.
    2.  **클래식의 힘**: 정규식, 룰 베이스, 캐시 시스템은 LLM과 결합할 때 비로소 최고의 파급력을 가지게 됨.
    3.  **비용 역전 설계**: 비싸고 무거운 문맥(Context) 임베딩 연산은 철저히 메인 앱 바깥의 독립된 오프라인 배치 시스템으로 격리하라.

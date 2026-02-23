# 시스템 전체 실행 흐름도 (Sequence Diagram)

본 문서는 사용자가 자연어 테스트 케이스(TC)를 입력한 시점부터 최종적으로 타겟 스크립트(simva.py)가 생성되기까지의 **전체 데이터 교환 흐름**을 시간 순서에 따라 시각화한 시퀀스 다이어그램입니다.

이 다이어그램은 이전에 설계된 Vector DB, Ontology, Core Engine(LLM), Adapter 프로세스가 언제 어떻게 맞물려 돌아가는지 단일 뷰로 제공합니다.

---

## 1. 전체 실행 흐름 시퀀스 다이어그램 (Mermaid)

```mermaid
sequenceDiagram
    autonumber
    
    actor User
    participant UI as Streamlit UI
    participant Core as Core Engine
    participant VectorDB as Vector DB
    participant Ontology as Ontology Graph
    participant LLM as LLM Provider
    participant Adapter as Adapter Process
    
    User->>UI: TC 파일 업로드 및 실행 클릭
    UI->>Core: 변환 요청 전달
    Core->>UI: 진행률 바 렌더링 시작
    
    rect rgb(240, 248, 255)
        Note right of Core: Phase 1: Hybrid RAG & Context Enrichment
        loop 각 자연어 문장마다 반복
            Core->>VectorDB: 키워드 임베딩 및 유사도 검색
            VectorDB-->>Core: 매핑된 논리 시그널 반환
            
            Core->>Ontology: 논리 시그널 제약 조건 조회
            Ontology-->>Core: 선행 조건 규칙 반환
            
            Core->>Core: 과거 Step 기록과 선행 조건 매칭
        end
    end
    
    rect rgb(255, 240, 245)
        Note right of Core: Phase 2: Prompting & IR Generation
        
        loop 최대 3회 Self-Correction Retry
            Core->>LLM: 프롬프트 및 에러 피드백 전송
            LLM-->>Core: JSON 형식의 IR 객체 반환
            
            Core->>Core: Pydantic으로 Validation 수행
            alt 검증 성공
                Core->>Core: 유효한 IR 획득 후 루프 탈출
            else 검증 실패
                Core->>Core: 에러 메시지를 주입하여 재시도
            end
        end
    end
    
    rect rgb(240, 255, 240)
        Note right of Core: Phase 3: Adapter Subprocess Execution
        Core->>Adapter: subprocess.Popen 으로 격리 실행
        
        Core->>Adapter: 전체 TC의 IR JSON 주입
        
        loop 코드 변환 중
            Adapter-->>UI: stderr를 통해 진행률 출력
            UI->>UI: 화면 진행률 바 업데이트 
        end
        
        Note right of Adapter: Direct Translation 패턴 작동
        
        Adapter-->>Core: 완성된 Python 스크립트 코드 반환
        Core->>Adapter: 프로세스 종료 플래그 확인
    end
    
    Core-->>UI: 최종 스크립트 텍스트 전달
    UI-->>User: 결과 출력 및 다운로드 버튼 제공
```

---

## 2. 각 구간별 핵심 설계 요약

### Phase 1: Hybrid RAG & Context Enrichment
단순 정규표현식이 아닌 Vector DB와 온톨로지를 결합하여 **지식을 증강**하는 구간입니다.
이 과정에서 사용자의 모호한 텍스트("엑셀")를 벡터 검색으로 표준 `Logical Signal`로 치환하고, 온톨로지에서 찾아낸 "시동 연관성" 규칙을 가져옵니다. **실제 코드가 아직 등장하지 않는 순수 논리적 공간**입니다.

### Phase 2: Prompting & IR Generation
취합된 RAG 컨텍스트를 LLM에게 프롬프트로 제공합니다.
LLM은 제약 조건 위반을 스스로 판단하고, 결과적으로 `Pydantic`으로 정의된 **순수 JSON 형태의 IR(Intermediate Representation)**만 내뱉습니다. LLM의 환각(Hallucination)에 의한 문법 에러 위험을 없애줍니다.

### Phase 3: Adapter Subprocess Execution
가장 핵심인 **"Direct Translation" 패턴** 구간입니다.
아예 메인 파이썬 실행 환경을 쪼개어(`subprocess`) 독립된 어댑터 스크립트를 띄웁니다.
이 어댑터는 `stdin`으로 넘겨받은 안전한 JSON 덩어리를 `simva.set(...)` 같은 하드코딩 포맷 규칙에 맞춰 "직접" 문자열로 변환하여 `stdout`으로 최종 뱉어냅니다. 그동안 `stderr` 채널을 이용해 메인 UI를 업데이트합니다.

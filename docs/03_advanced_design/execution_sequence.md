# 아키텍처 실행 시퀀스 다이어그램 (Sequence Diagram)

이 문서는 새롭게 분리된 **Vector DB (문법/뼈대)**와 **Ontology DB (단어/번역)** 간의 상호작용 흐름과 각 자동화 파이프라인이 어떤 순서로 동작하는지 직관적인 시퀀스 다이어그램으로 설명합니다.

---

## 1. 코어 변환 시퀀스 (Testing / Execution Phase - 조건/루프 제어문 예시)
테스트 엔지니어가 복합적인 조건 제어가 포함된 자연어 테스트 스크립트를 실행했을 때, 메인 뼈대를 잡고 내부 하위 문장(액션)까지 재귀적(Recursive)으로 번역되어 최종 코드로 조립되는 과정입니다.

```mermaid
sequenceDiagram
    participant User as 사용 주체 (Core Engine)
    participant VectorDB as Vector DB (문맥/템플릿)
    participant OntologyDB as Ontology DB (단어/라우팅)
    
    User->>User: 1. 자연어 스크립트 실행<br/>("차량 속도가 100이면 와이퍼를 작동한다" / Variant:CarModel_B)
    
    %% 1단계: 메인 조건문 뼈대 매칭
    User->>VectorDB: 2. 메인 문장 유사도(Vector) 검색 질의
    VectorDB-->>User: 3. 조건문 템플릿 반환 (meta_condition_if)
    
    Note over User: 4. 1차 정규식 캡처 (If-Condition 파티셔닝)<br/>{condition}="차량 속도가 100", {true_action}="와이퍼를 작동한다"
    
    %% 2단계: 조건부 및 액션부 재귀 파싱
    User->>VectorDB: 5. 하위 {true_action} 문장 유사도 검색 질의
    VectorDB-->>User: 6. 하위 액션 템플릿 반환 (action_set_signal)
    Note over User: 7. 2차 하위 정규식 캡처<br/>{signal}="와이퍼", {value}="ON"
    
    %% 3단계: Ontology DB 번역 (신호 매핑 일괄 처리)
    User->>OntologyDB: 8. 추출된 모든 동의어 논리 노드 질의 ("차량 속도", "와이퍼")
    OntologyDB-->>User: 9. Concept:VehicleSpeed, Concept:Wiper 발견
    
    User->>OntologyDB: 10. Variant(CarModel_B) 기반 물리 라우팅 질의
    OntologyDB-->>User: 11. 물리 노드 도달<br/>속도 -> {ecu}="CGW", {signal_id}="V_Spd"<br/>와이퍼 -> {ecu}="BCM", {signal_id}="Wiper_State"
    
    %% 4단계: 최종 조립 (Bottom-Up)
    Note over User: 12. 조건식 변환<br/>condition_code = "signals.CGW.V_Spd == 100"
    Note over User: 13. 액션식 변환<br/>action_code = "simva.set_signal(signals.BCM.Wiper_State, \"ON\")"
    Note over User: 14. 메인 템플릿(if)에 최종 Slotting 결합<br/>if condition_code:<br/>    action_code
    
    User->>User: 15. 최종 파이썬 소스코드 생성 완료 (실행 가능)
```

---

## 2. Vector DB 유지보수 시퀀스 (Zero-Code Generation Phase)
테스트 엔지니어가 평소 쓰던 문구를 템플릿 빌더 UI (Web/Desktop)에서 드래그하여 새로운 규칙을 Vector DB에 등록하는 과정입니다.

```mermaid
sequenceDiagram
    actor Tester as 테스트 엔지니어
    participant UI as No-Code Builder UI
    participant Backend as Vector DB Builder (LLM / Script)
    participant VectorDB as Vector DB 저장소
    
    Tester->>UI: 1. 자주 쓰는 자연어 예시 문장 입력 ("시트 열선을 3단으로...")
    Tester->>UI: 2. 문장 내 가변 단어 마우스 드래그 & 태깅 ([signal], [value])
    Tester->>UI: 3. 변환될 공통 코드 형태 확인 후 [저장 및 배포] 버튼 클릭 (simva.set_signal(...))
    
    UI->>Backend: 4. 태깅 패턴 정보 파싱본 전송
    
    Note over Backend: 5. 동적 정규식(Regex) Named Group 자동 합성
    Note over Backend: 6. 임베딩(Vector) 벡터값 산출 작업
    Note over Backend: 7. 데이터 덩어리를 JSON Object 형식으로 패키징
    
    Backend->>VectorDB: 8. 신규 템플릿 JSON Insert (Hot-Reload)
    VectorDB-->>Backend: 9. DB 동기화/캐싱 반영 완료
    
    Backend-->>UI: 10. 성공 응답 라우팅
    UI-->>Tester: 11. "성공적으로 추가되었습니다. 지금 바로 테스트 가능합니다!"
```

---

## 3. 온톨로지 유지보수 확장 시퀀스 (Auto-Ingestion Phase)
새로운 차종(Variant)이 산출되거나 물리 통신 신호 스펙(DBC/ARXML)이 변경되었을 때, 인간이 단 한 줄의 JSON도 수정하지 않고 온톨로지 DB가 자동 갱신되는 100% 자동화 파이프라인입니다.

```mermaid
sequenceDiagram
    actor Admin as 시스템 관리자 (또는 CI/CD)
    participant IngestionPipeline as Auto-Ingestion Script
    participant LLM as NLP / Rule-base Engine
    participant OntologyDB as Ontology DB 저장소
    
    Admin->>IngestionPipeline: 1. 신규 차종 폴더(예: CarModel_C) 지정 후 스크립트 실행 트리거
    
    Note over IngestionPipeline: 2. Target 폴더 내의 통신 스펙 파일(DBC/ARXML 등) 스캔 시작
    Note over IngestionPipeline: 3. Array 형태로 전체 ECU / 내부 통신 Signal_ID / 메시지 속성 100% 파싱
    
    IngestionPipeline->>LLM: 4. 추출된 물리 신호명(예: "V_Speed_Main") 전송 (초기 매핑 판별용)
    LLM-->>IngestionPipeline: 5. 텍스트 분석 후 LogicalConcept 노드 제안 (Concept:VehicleSpeed 대상)
    
    Note over IngestionPipeline: 6. CarModel_C 컨텍스트에 맞게 신규 PhysicalSignal 노드 일괄 덮어쓰기 (Upsert)
    Note over IngestionPipeline: 7. 기존 LogicalConcept 과의 'implemented_by' 연결망(Edge)을 JSON에 강제 주입
    
    IngestionPipeline->>OntologyDB: 8. 처리된 단일 거대 Knowledge Graph (JSON File) 저장 병합 명령 (Merge)
    OntologyDB-->>IngestionPipeline: 9. DB 최신화 완료
    
    IngestionPipeline-->>Admin: 10. "총 3,420개 신규 시그널, CarModel_C 컨텍스트로 온톨로지 업데이트 완료."
```

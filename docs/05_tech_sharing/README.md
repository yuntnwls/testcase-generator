# 🎤 프로젝트 기술 공유 자료

본 폴더는 **"자연어 테스트 스크립트 자동화: Naive RAG에서 Contextual RAG까지의 여정"**이라는 주제로 사내/외 기술 공유를 진행하기 위한 발표 자료와 스피커 스크립트를 담고 있습니다.

단순한 기능 나열이 아닌, **도전 ➡️ 실패 ➡️ 개선 ➡️ 완성**이라는 스토리텔링 방식을 통해 LLM과 RAG를 실무에 적용하며 겪은 시행착오와 최적화 노하우를 전달하는 데 목적이 있습니다.

---

## 📂 문서 목록

| 문서 | 설명 |
| :--- | :--- |
| **[tech_sharing_flow.md](./tech_sharing_flow.md)** | 기술 공유 흐름 가이드 |
| **[demo_scenario_guide.md](./demo_scenario_guide.md)** | 기술 공유 중 시연 시나리오 및 주요 포인트 가이드 |
| **[demo/demo_cli_app.py](./demo/demo_cli_app.py)** | **(Live 통합 데모)** 샘플 VectorDB(Chroma) 및 Ontology 검색 과정을 시각적으로 보여준 직후, 실제 LLM 엔진을 호출하여 최종 코드로 합성하는 End-to-End 시연 프로그램 |

---


## 💡 3가지 핵심 메시지 (Takeaways)

1.  **LLM은 만능이 아니다 (특히 런타임에서)**
    *   모든 것을 LLM에게 맡기면 비용은 기하급수적으로 늘고, 응답 속도와 안정성은 파괴됩니다.
2.  **결정론적 로직(Deterministic)과 확률적 모델(Probabilistic)의 분리**
    *   정규식(Regex), 문자열 알고리즘(LCS), 지식 그래프(Ontology) 방어막을 겹겹이 쳐서 LLM까지 도달하는 트래픽을 최소화해야 합니다.
3.  **비싼 연산은 오프라인으로, 런타임은 가벼운 검색으로 (Contextual RAG)**
    *   LLM 연산을 사용자 요청 시점(Runtime)이 아닌 DB 구축 시점(Offline 배치)으로 옮기면, 검색 품질과 속도를 동시에 잡을 수 있습니다.

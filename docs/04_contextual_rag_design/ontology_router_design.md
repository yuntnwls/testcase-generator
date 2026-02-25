# Ontology Router — Fuzzy Filtering 설계

본 문서는 방안 C 아키텍처의 `Ontology Router` 모듈이 자연어 표현을 Ontology DB의 정확한 시그널명으로 매핑하는 방법을 상세히 설명합니다.

*   **컴포넌트**: `src/db/ontology_graph.py`
*   **의존 패키지**: `pip install thefuzz python-Levenshtein`
*   **관련 문서**: [ontology_db_design.md](db/ontology_db_design.md) | [architecture.md](architecture.md)

---

## 1. 왜 Fuzzy Filtering이 필요한가?

Extractor가 TC 문장에서 추출하는 시그널 이름(`"좌측 헤드램프"`, `"헤드라이트"`, `"앞 램프"`)은 자연어입니다. Ontology DB에 저장된 정확한 신호명(`Left_HeadLamp`)과 철자가 다를 수 있습니다.

**Ontology DB에 정확한 이름이 없을 때의 두 가지 선택:**

```
방법 1 — LLM에 전체 목록 전달 (비용 과다)
    "다음 후보 350개 중 '좌측 헤드램프'는 어느 것입니까?
     Left_HeadLamp, Right_HeadLamp, FogLamp, ... (350개 전부)"
    → 입력 토큰 ~2,000 tok 소비

방법 2 — Fuzzy Filter 후 LLM 전달 (방안 C 채택)
    Step 1: TheFuzz로 전체 350개 중 상위 5개 후보만 추림 (비용 0, 수ms)
    Step 2: "다음 후보 5개 중 '좌측 헤드램프'는 어느 것입니까?
             Left_HeadLamp, Right_HeadLamp, FogLamp, FrontLamp, HighBeam"
    → 입력 토큰 ~80 tok 소비 (96% 절감)
```

---

## 2. Fuzzy Matching이란?

**Fuzzy Matching(퍼지 매칭)**은 두 문자열이 완전히 일치하지 않아도 **"얼마나 비슷한가"를 숫자(0~100)**로 계산하는 문자열 유사도 기법입니다.

내부적으로 **Levenshtein Distance(편집 거리)** 알고리즘을 사용합니다.

> **Levenshtein Distance**: 문자열 A를 문자열 B로 바꾸기 위해 필요한 최소 편집 횟수(삽입·삭제·교체). 거리가 작을수록 더 유사합니다.

```
"헤드램프"  →  "Head_Lamp"   편집 거리: 크다 (한글-영문 직접 비교) → 실제론 별칭 매핑을 거침
"Left_HeadLamp" vs "LeftHeadLamp"  편집 거리: 1 (언더바 1회 삽입) → 유사도 높음
"Left_HeadLamp" vs "Right_HeadLamp"  편집 거리: 5 → 유사하지만 의미 다름
```

---

## 3. TheFuzz 라이브러리가 제공하는 4가지 스코어링

본 시스템에서는 `thefuzz.process.extract()`를 사용합니다. 내부에서는 4가지 방식을 복합적으로 사용합니다.

| 메서드 | 설명 | 예시 (query="헤드램프") |
| :--- | :--- | :--- |
| `ratio` | 두 문자열의 전체 유사도 | `"Left_HeadLamp"` → 45 |
| `partial_ratio` | 짧은 쪽이 긴 쪽 안에 **부분 포함** 여부 | `"HeadLamp"` → 90 (**부분 일치 강점**) |
| `token_sort_ratio` | 단어를 알파벳 순 정렬 후 비교 | 어순 무관 매칭 |
| `token_set_ratio` | 공통 단어 집합 기준 비교 | 중복·어순 무관 |

> **핵심**: 정확한 철자 일치 없이도 **"이 두 표현이 같은 개념을 지칭할 가능성"**을 0~100 스케일로 빠르게 추정합니다.

---

## 4. 구현 로직

### 4.1. Fuzzy 후보 추출 (`find_ontology_candidates`)

```python
from thefuzz import process

def find_ontology_candidates(unknown_alias: str, top_n: int = 5) -> list[dict]:
    """
    Ontology DB의 전체 노드(수백 개) 중 입력 alias와 가장 유사한 N개 후보 추출.

    이 함수는 LLM 없이 로컬에서 수 ms 이내 완료됩니다.
    결과는 이후 단계에서 LLM 프롬프트에 주입될 '압축된 후보 목록'이 됩니다.

    Args:
        unknown_alias: 매핑되지 않은 자연어 표현 (예: "좌측 헤드램프")
        top_n: LLM에 전달할 최대 후보 수 (기본 5)

    Returns:
        유사도 순 정렬된 Ontology 노드 목록 (각 노드: id, canonical_name, synonyms, ecu, data_type)
    """
    all_concepts = ontology_graph.get_all_concepts()  # 예: 350개 노드

    # 검색 풀(Pool): 각 노드의 canonical_name + synonyms를 하나의 텍스트로 합침
    # 예: {"Left_HeadLamp": "Left_HeadLamp 좌측헤드램프 헤드라이트 앞램프 상향등제어"}
    search_pool = {
        node.id: f"{node.canonical_name} {' '.join(node.synonyms)}"
        for node in all_concepts
    }

    # TheFuzz: 전체 풀에서 unknown_alias와 가장 유사한 top_n개 추출 (비용 0, ~수 ms)
    #   반환 형식: [(매칭된_텍스트, 유사도_점수, 노드_id), ...]
    top_matches = process.extract(unknown_alias, search_pool, limit=top_n)
    #   예: [("Left_HeadLamp 좌측헤드램프...", 92, "Left_HeadLamp"),
    #         ("Right_HeadLamp ...", 78, "Right_HeadLamp"), ...]

    # 유사도 너무 낮은 결과 제거 (완전히 무관한 노드)
    MIN_FUZZY_SCORE = 50
    candidate_nodes = [
        ontology_graph.get_node(node_id)
        for _, score, node_id in top_matches
        if score >= MIN_FUZZY_SCORE
    ]

    return candidate_nodes  # 최대 5개 → LLM 프롬프트 주입 대상
```

### 4.2. Ontology Router LLM 호출 — Fuzzy 결과 주입

```python
def resolve_alias_with_llm(unknown_alias: str, candidates: list[dict]) -> str:
    """
    Fuzzy Filter로 압축된 후보 5개만 LLM에 전달하여 최종 매핑 결정.
    """
    candidate_text = "\n".join([
        f"- {c['id']}: {c['canonical_name']} (동의어: {', '.join(c['synonyms'])})"
        for c in candidates
    ])

    prompt = f"""다음 후보 중 '{unknown_alias}'에 해당하는 자동차 신호를 하나만 선택하시오.
후보:
{candidate_text}

답변은 후보의 id만 출력하시오. (예: Left_HeadLamp)"""

    # 이 시점의 입력 토큰: ~80 tok (전체 목록 전달 시 ~2,000 tok 대비 96% 절감)
    return llm.invoke(prompt).content.strip()
```

---

## 5. 전체 흐름 요약 (Fuzzy → LLM → Jinja2)

```
Extractor 추출 결과: signal = "좌측 헤드램프"
        │
        ▼
✅ Graph 직접 탐색 (exact match + synonym lookup)
        │  "좌측 헤드램프" → DB에 없음
        ▼
✅ Fuzzy Filter: 전체 350개 → 상위 5개 추림 (비용 0, ~3ms)
        │  [Left_HeadLamp(92), Right_HeadLamp(78), FogLamp(61), FrontLamp(55), HighBeam(51)]
        ▼
🔴 Ontology Router LLM: 5개 후보 → "Left_HeadLamp" 선택 (~80 tok)
        │
        ▼
Jinja2 Assembler에 전달: ecu="BCM", signal="Left_HeadLamp", data_type="boolean"
        │
        ▼
렌더링: simva.set_signal(signals.BCM.Left_HeadLamp, True)
```

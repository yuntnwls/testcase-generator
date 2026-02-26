# Vector DB 자동 빌드 파이프라인 — TC + Script 기반

기존에 작성된 **자연어 TC 파일(TSV/엑셀, 자연어 컬럼 기준)**과 **테스트 스크립트 파일(Python)** 쌍을 Input으로 받아, Contextual RAG용 **Vector DB를 자동으로 구축**하는 파이프라인 방안입니다.

> [!NOTE]
> TC 파일 내 **자연어 컬럼명은 파일마다 다를 수 있습니다** (예: `"시험 방법"`, `"TC 스텝"`, `"검증 절차"` 등).
> 파서는 컬럼명을 인자로 받아 유연하게 동작합니다.

> 참조: [offline_pipeline_design.md](./offline_pipeline_design.md) | [vector_db_design.md](./db/vector_db_design.md)

---

## 1. 전체 흐름

```
[Input A]  data/tc_samples/*.tsv    ← 자연어 TC (TSV/엑셀)
[Input B]  data/simva/*.py          ← 테스트 스크립트 (Python)
                │
                ▼
 scripts/extract_templates.py    ← [Step 1] LLM 패턴 추출기
                │
                ▼
 data/raw_templates.json         ← 중간 산출물 (사람이 검토)
                │
                ▼
 scripts/build_vector_db.py      ← [Step 2] Contextual Indexer
                │
                ▼
 data/vector_db_storage/         ← [Output] ChromaDB Vector DB
```

### 사용자 개입 최소화 전략

| 단계 | 자동화 | 사람 개입 |
|:---|:---:|:---:|
| TSV에서 TC 스텝 파싱 | ✅ | |
| TC ↔ Script 쌍 LLM 패턴 추출 | ✅ | |
| 추출 결과 검토 및 수정 | | ✅ 1~2시간 |
| context_prefix 생성 + ChromaDB 빌드 | ✅ | |

---

## 2. Step 1: `extract_templates.py` — 패턴 추출기

### 역할
- TSV에서 **시험 방법 / 판정 조건 컬럼** 파싱
- 대응하는 Python 스크립트에서 **코드 패턴** 파싱
- 두 쌍을 LLM에 전달 → `{변수}` 형태의 **공통 패턴 자동 추출**
- 결과를 `raw_templates.json`으로 저장

### 스크립트 예시

```python
# scripts/extract_templates.py
import json, re, csv
from pathlib import Path
from openai import OpenAI

client = OpenAI()

def parse_tc_steps(tsv_path: str, nl_column: str) -> list[str]:
    """
    TSV에서 자연어 TC 문장이 담긴 컬럼을 추출합니다.

    Args:
        tsv_path  : TC TSV/엑셀 파일 경로
        nl_column : 자연어가 입력된 컬럼 헤더명
                    (예: '시험 방법', '검증 절차', 'TC 스텝' 등 실제 파일에 맞게 지정)
    """
    steps = []
    with open(tsv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            raw = row.get(nl_column, "").strip()
            if not raw:
                continue
            # 줄바꿈 또는 번호 구분자로 여러 스텝이 있을 경우 분리
            for line in re.split(r'\n|\d+\.\s*', raw):
                line = line.strip().strip('()')
                if len(line) > 2:  # 너무 짧은 항목 제외
                    steps.append(line)
    return list(set(steps))  # 중복 제거


def parse_script_lines(py_path: str) -> list[str]:
    """Python 스크립트에서 simva.* 호출 라인을 추출합니다."""
    lines = []
    for line in Path(py_path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line.startswith("simva."):
            lines.append(line)
    return list(set(lines))


def extract_templates(tc_steps: list[str], script_lines: list[str]) -> list[dict]:
    """LLM에게 TC-Script 쌍을 분석시켜 템플릿 JSON을 생성합니다."""
    sample_pairs = "\n".join(
        f'- TC: "{s}"  →  Script: "{c}"'
        for s, c in zip(tc_steps[:30], script_lines[:30])  # 샘플 30쌍 사용
    )

    prompt = f"""다음은 자동차 ECU 테스트의 자연어 TC 스텝과 대응하는 Python 스크립트 코드 쌍입니다.

{sample_pairs}

위 쌍들을 분석해서 공통되는 패턴을 찾아, {{변수명}} 형태로 추상화된 템플릿을 추출하세요.
아래 JSON 배열 형식으로 응답하세요 (id는 영문 소문자+언더스코어):

[
  {{
    "id": "action_set_signal",
    "type": "ACTION",
    "type_source": "{{signal}}를 {{value}}로 설정한다",
    "target_code": "simva.set_signal('{{signal}}', {{value}})",
    "variables": ["signal", "value"]
  }}
]"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    return result.get("templates", result) if isinstance(result, dict) else result


if __name__ == "__main__":
    # ① 파싱
    # ↓ nl_column: 실제 TC 파일에서 자연어 문장이 담긴 컬럼명으로 변경하세요
    nl_column    = "시험 방법"   # 예시: "검증 절차", "TC Step", "테스트 방법" 등
    tc_steps     = parse_tc_steps("data/tc_samples/mock_tc_data.tsv", nl_column)
    script_lines = parse_script_lines("data/simva/test_sample.py")

    print(f"추출된 TC 스텝: {len(tc_steps)}개")
    print(f"추출된 스크립트 라인: {len(script_lines)}개")

    # ② LLM 패턴 추출
    templates = extract_templates(tc_steps, script_lines)

    # ③ 저장
    output_path = "data/raw_templates.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)

    print(f"✅ raw_templates.json 저장 완료 ({len(templates)}개 패턴)")
    print("⚠️  내용을 검토한 후 build_vector_db.py를 실행하세요.")
```

### 중간 산출물 예시 (`raw_templates.json`)

자연어 TC 문장을 기반으로 LLM이 공통 패턴을 추상화한 결과입니다.

```json
[
  {
    "id": "action_set_signal",
    "type": "ACTION",
    "type_source": "{signal}을 {value}로 설정한다",
    "target_code": "simva.set_signal('{signal}', {value})",
    "variables": ["signal", "value"],
    "examples": [
      "좌측 전조등을 ON으로 설정한다",
      "차량 속도를 60으로 설정한다",
      "와이퍼 상태를 HIGH로 설정한다"
    ]
  },
  {
    "id": "action_turn_on",
    "type": "ACTION",
    "type_source": "{signal}을 켠다",
    "target_code": "simva.set_signal('{signal}', 'ON')",
    "variables": ["signal"],
    "examples": [
      "좌측 전조등을 켠다",
      "비상등을 켜라",
      "헤드램프를 켜다"
    ]
  },
  {
    "id": "action_wait",
    "type": "TYPE_WAIT",
    "type_source": "{duration}초 기다린다",
    "target_code": "simva.wait({duration} * 1000)",
    "variables": ["duration"],
    "examples": [
      "3초 기다린다",
      "5초 대기한다",
      "2초 후 진행"
    ]
  },
  {
    "id": "check_signal_eq",
    "type": "TYPE_CHECK",
    "type_source": "{signal}이 {value}인지 확인한다",
    "target_code": "result = simva.is_eq('{signal}', '{value}')",
    "variables": ["signal", "value"],
    "examples": [
      "도어 상태가 LOCKED인지 확인한다",
      "전조등이 ON 상태임을 확인한다",
      "속도가 0인지 검증한다"
    ]
  }
]
```

> [!IMPORTANT]
> - `examples` 필드는 LLM이 자동 생성한 패턴 매칭 예시이며, 실제 DB에는 저장되지 않습니다.
> - `type_source`와 `target_code`의 `{변수명}`이 정확히 일치하는지 반드시 검토하세요.
> - LLM이 비슷한 패턴을 중복으로 추출했거나 잘못 분류한 경우 수동으로 병합·수정합니다.

---

## 3. Step 2: `build_vector_db.py` — Contextual Indexer

### 역할
- `raw_templates.json` 파일 로드
- 각 템플릿에 대해 LLM으로 `context_prefix` 생성 (맥락 요약, 1회성)
- `vector_source = context_prefix + type_source` 조합 후 ChromaDB에 upsert

### 스크립트 예시

```python
# scripts/build_vector_db.py
import json
import chromadb
from openai import OpenAI
from pathlib import Path

client = OpenAI()
chroma_client = chromadb.PersistentClient(path="data/vector_db_storage")
collection = chroma_client.get_or_create_collection(name="simva_templates")


def generate_context_prefix(template: dict) -> str:
    """LLM을 사용해 템플릿의 사용 맥락을 요약합니다. (1회성 오프라인 작업)"""
    prompt = f"""자동차 ECU 테스트 자동화 시스템의 코드 생성 템플릿입니다.
이 템플릿이 언제, 어떤 문장에 사용되는지 3문장 이내로 요약하세요.
관련 동의어와 상황 설명을 풍부하게 포함하세요.

id: {template['id']}
type_source: {template['type_source']}
target_code: {template['target_code']}
type: {template['type']}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def build_db(raw_templates_path: str):
    templates = json.loads(Path(raw_templates_path).read_text(encoding='utf-8'))

    for tmpl in templates:
        # 이미 인덱싱된 경우 스킵 (증분 업데이트)
        existing = collection.get(ids=[tmpl["id"]])
        if existing["ids"]:
            print(f"  [SKIP] {tmpl['id']} (already indexed)")
            continue

        # context_prefix 생성 (LLM 1회 호출)
        context_prefix = generate_context_prefix(tmpl)

        # vector_source = context + 원본 문장
        vector_source = f"{context_prefix}\n\n{tmpl['type_source']}"

        # ChromaDB upsert
        collection.upsert(
            ids=[tmpl["id"]],
            documents=[vector_source],
            metadatas=[{
                "type":         tmpl["type"],
                "type_source":  tmpl["type_source"],
                "target_code":  tmpl["target_code"],
                "variables":    json.dumps(tmpl.get("variables", []), ensure_ascii=False),
                "context_prefix": context_prefix,
            }]
        )
        print(f"  [OK] {tmpl['id']}")

    print(f"\n✅ Vector DB 구축 완료: {collection.count()}개 템플릿 인덱싱됨")


if __name__ == "__main__":
    build_db("data/raw_templates.json")
```

---

## 4. 실행 순서

```bash
# Step 1: TC + Script → raw_templates.json 생성
python scripts/extract_templates.py

# ⚠️ raw_templates.json 내용을 직접 검토·수정

# Step 2: raw_templates.json → ChromaDB 구축
python scripts/build_vector_db.py
```

---

## 5. 증분 업데이트 (신규 TC 유형 추가 시)

새로운 유형의 TC가 추가되었거나 기존 패턴이 바뀐 경우:

1. `raw_templates.json`에 신규 레코드 추가 (또는 `extract_templates.py` 재실행)
2. `build_vector_db.py` 재실행 → **이미 인덱싱된 항목은 자동 스킵** (upsert 증분 적용)
3. Pattern Cache 무효화: 수정된 템플릿 ID와 연결된 캐시 엔트리 자동 삭제 ([pattern_cache_design.md](./pattern_cache_design.md) 참조)

# 3-Tier Extractor 설계

본 문서는 방안 C 아키텍처의 `3-Tier Extractor` 모듈 상세 설계를 다룹니다. Extractor는 Retriever가 반환한 **매칭된 템플릿**에서 **변수값을 추출**하는 역할로, 정확도와 비용을 동시에 최적화하기 위해 3개의 계층(Tier)으로 구성됩니다.

*   **컴포넌트**: `src/core/extractor.py`
*   **관련 문서**: [architecture.md](architecture.md) | [jinja_template_engine.md](jinja_template_engine.md) | [prompt_engineering_guide.md](prompt_engineering_guide.md) §2-1

---

## 1. 왜 3-Tier 구조인가?

변수 추출에는 단일 방법으로 모든 케이스를 처리할 수 없습니다. 각 방법은 정확도와 비용이 상충됩니다.

```
입력: "100을 타겟 속도로 맞춰주세요"
템플릿: "{signal}를 {value}로 설정한다"

Tier 1 - Regex: 패턴 미매칭 (어순 역전) → 실패
Tier 2 - Alignment: 공통 부분 너무 짧음 → 실패
Tier 3 - SLM: "signal=타겟 속도, value=100" 추출 성공 (LLM 비용 발생)
```

**설계 원칙: "비용은 최후 수단에만"**

| Tier | 방법 | 정확도 | 비용 | 예상 적중률 |
| :--- | :--- | :---: | :---: | :---: |
| **Tier 1** | Regex Named Group | ~100% | 0 | ~75% |
| **Tier 2** | LCS Sequence Alignment | ~95% | 0 | ~20% |
| **Tier 3** | SLM (생성형 LLM) Fallback | ~90% | ~650 tok | ~5% |

---

## 2. Tier 1 — Regex Named Group (정규식 추출)

### 2.1. 동작 원리

Vector DB의 `regex_pattern` 필드에는 각 템플릿의 변수 위치를 Named Group으로 정의한 정규식이 저장되어 있습니다.

```python
# Vector DB의 regex_pattern 예시 (action_set_signal 템플릿)
regex_pattern = r"""
    ^.*?
    (?P<signal>[a-zA-Z가-힣0-9_\s]+?)   # ← 변수: 시그널명 (Named Group)
    (?:을|를|은|는)?\s+
    (?P<value>[a-zA-Z0-9가-힣_\s\.]+?)  # ← 변수: 설정값 (Named Group)
    (?:으로|로|에)?\s+
    (?:설정|세팅|변경|바꿔|켜|꺼|작동).*$
"""
```

입력 문장에 이 정규식을 적용하면 Named Group이 자동으로 변수 딕셔너리가 됩니다.

```python
import re

def extract_tier1(user_input: str, regex_pattern: str) -> dict | None:
    """
    Named Group 정규식으로 변수 추출.
    성공 시 변수 딕셔너리 반환, 실패 시 None 반환.
    """
    match = re.match(regex_pattern, user_input, re.IGNORECASE | re.DOTALL)
    if match:
        variables = match.groupdict()
        # 공백 제거 및 빈 값 필터링
        return {k: v.strip() for k, v in variables.items() if v and v.strip()}
    return None  # Tier 2로 에스컬레이션
```

### 2.2. 실패 조건 (Tier 2 에스컬레이션 기준)

| 실패 케이스 | 예시 | 원인 |
| :--- | :--- | :--- |
| 어순 역전 | `"100을 속도로 맞춰주세요"` | 주어와 목적어 순서 다름 |
| 표현 생략 | `"속도 100 설정"` | 조사·조동사 없음 |
| 복합 수식어 | `"매우 빠른 속도인 100km/h"` | 수식어가 패턴 분리 |
| 복수 단어 변수 | `"좌측 전방 헤드램프"` | 일부 Greedy 패턴 오매칭 |

> **실패 판정**: `re.match()` 결과가 `None`이거나, 추출된 변수가 `variables` 목록과 키 불일치 시 Tier 2로 에스컬레이션.

---

## 3. Tier 2 — LCS Sequence Alignment (문자열 차분 정렬)

### 3.1. LCS (최장 공통 부분 수열)란?

**LCS(Longest Common Subsequence)**는 두 문자열에서 **순서를 유지하며 공통으로 등장하는 가장 긴 부분 수열**을 찾는 알고리즘입니다.

> **Tier 2 활용 방식**: 입력 문장과 템플릿 `type_source`의 LCS를 구한 뒤, LCS에 속하지 않는 입력 문장의 조각(non-LCS tokens)을 변수 후보로 간주합니다.

```
입력:    "와이퍼 속도를 가장 빠른 단계인 3단으로 작동시켜라"
템플릿:  "{signal}를 {value}로 설정한다"

TokenizeType
  입력 토큰:    ["와이퍼", "속도를", "가장", "빠른", "단계인", "3단으로", "작동시켜라"]
  템플릿 토큰:  ["{signal}를", "{value}로", "설정한다"]

LCS 계산 (조사 정규화 후):
  공통 부분:  ["를", "로"]  ← 조사는 LCS에서 고정 앵커 역할

비 LCS 슬롯 할당:
  {signal} 위치 앞: ["와이퍼", "속도를"] → signal = "와이퍼 속도"
  {value} 위치 앞:  ["가장", "빠른", "단계인", "3단으로"] → value = "3단"
                     (수식어 제거, 핵심 명사 추출)
```

### 3.2. 구현 로직

```python
from difflib import SequenceMatcher

def tokenize_with_josa_normalization(text: str) -> list[str]:
    """입력 문장을 조사 제거 후 토큰화"""
    import re
    text = re.sub(r'(을|를|은|는|이|가|으로|로|에|의|도)', ' \\1 ', text)
    return [t for t in text.split() if t]

def extract_tier2(user_input: str, type_source: str, variables: list[str]) -> dict | None:
    """
    LCS 기반 Sequence Alignment로 변수 추출.

    Template의 {var} 슬롯 위치를 고정 앵커로 삼아,
    입력 문장의 비-LCS 구간을 각 슬롯에 할당합니다.

    Args:
        user_input:  사용자 입력 문장
        type_source: 템플릿 type_source (예: "{signal}를 {value}로 설정한다")
        variables:   추출 대상 변수 이름 목록 (예: ["signal", "value"])

    Returns:
        변수 딕셔너리 또는 None (실패 시)
    """
    import re

    # 슬롯 제거한 고정 텍스트만 추출 (앵커 텍스트)
    anchor_pattern = re.sub(r'\{[^}]+\}', '(.*?)', type_source)
    match = re.search(anchor_pattern, user_input, re.IGNORECASE | re.DOTALL)

    if not match:
        return None  # 앵커 텍스트 자체가 없으면 실패 → Tier 3

    groups = match.groups()
    if len(groups) != len(variables):
        return None  # 그룹 수 불일치 → Tier 3

    result = {}
    for var_name, raw_value in zip(variables, groups):
        cleaned = raw_value.strip() if raw_value else None
        if not cleaned:
            return None  # 빈 값 → Tier 3
        result[var_name] = cleaned

    return result
```

### 3.3. 실패 조건 (Tier 3 에스컬레이션 기준)

| 실패 케이스 | 설명 |
| :--- | :--- |
| 앵커 텍스트 없음 | 고정 조사·동사조차 입력에 없음 |
| 그룹 수 불일치 | 변수 개수와 매칭 그룹 수 차이 |
| 빈 그룹 포함 | 변수 중 하나가 추출되지 않음 |
| 공통 부분 너무 짧음 | LCS 비율이 전체 템플릿의 30% 미만 |

> **Tier 2는 Tier 1 미매칭 시만 호출**됩니다. Tier 2가 성공하면 Tier 3는 호출하지 않습니다.

---

## 4. Tier 3 — SLM Fallback (생성형 LLM 변수 추출)

### 4.1. 언제 호출되는가?

Tier 1과 Tier 2가 모두 실패한 경우에만 호출됩니다. **전체 Step의 약 5%** 수준으로 예상됩니다.

> Retriever는 이미 Score ≥ 0.75인 템플릿을 매칭했으므로 **"어떤 템플릿인지"는 확실**합니다. Tier 3가 해결해야 하는 문제는 "변수 값을 어떻게 구분하는가"뿐입니다.

### 4.2. 구현 로직

```python
def extract_tier3(
    user_input: str,
    type_source: str,
    context_prefix: str,
    variables: list[str],
    llm_client
) -> dict | None:
    """
    SLM(생성형 LLM)으로 변수 추출.
    prompt_engineering_guide.md §2-1의 공식 프롬프트 사용.
    """
    from src.prompts import EXTRACTOR_TIER3_PROMPT

    prompt = EXTRACTOR_TIER3_PROMPT.format(
        user_input=user_input,
        matched_type_source=type_source,
        context_prefix=context_prefix
    )

    response = llm_client.invoke(prompt)

    try:
        import json
        result = json.loads(response.content)
        # null 값 포함 시 실패 처리
        if any(v is None for v in result.values()):
            return None
        return {k: str(v).strip() for k, v in result.items()
                if k in variables}
    except (json.JSONDecodeError, AttributeError):
        return None  # JSON 파싱 실패 → Approval Queue 등록
```

> 상세 프롬프트 명세는 [prompt_engineering_guide.md §2-1](prompt_engineering_guide.md) 참조.

---

## 5. 3-Tier 통합 Extractor 구현

```python
def extract_variables(
    user_input: str,
    template: dict,
    llm_client=None
) -> tuple[dict, int]:
    """
    3-Tier Extractor 통합 진입점.

    Args:
        user_input: 사용자 입력 TC 문장
        template: Retriever가 반환한 템플릿 (regex_pattern, type_source, variables 포함)
        llm_client: Tier 3 전용 LLM 클라이언트 (없으면 Tier 3 생략)

    Returns:
        (변수 딕셔너리, 사용된 Tier 번호)
        실패 시 ({}, -1) 반환
    """
    regex_pattern = template["regex_pattern"]
    type_source   = template["type_source"]
    context_prefix = template.get("context_prefix", "")
    variables     = json.loads(template["variables"])

    # ── Tier 1: Regex Named Group ──────────────────────────────
    result = extract_tier1(user_input, regex_pattern)
    if result:
        return result, 1

    # ── Tier 2: LCS Sequence Alignment ─────────────────────────
    result = extract_tier2(user_input, type_source, variables)
    if result:
        return result, 2

    # ── Tier 3: SLM Fallback ───────────────────────────────────
    if llm_client:
        result = extract_tier3(user_input, type_source, context_prefix, variables, llm_client)
        if result:
            return result, 3

    # 전 Tier 실패 → 상위에서 Approval Queue 등록 처리
    return {}, -1
```

---

## 6. META_CONTROL 타입(IF-ELSE, LOOP) 처리

조건문·반복문 META_CONTROL 타입은 변수 추출 방식이 다릅니다.

```
META_CONTROL_IFELSE 템플릿의 type_source:
  "만약 {condition}이면 {true_action}한다"

추출 대상:
  condition  → "차량 속도가 100 이상" (→ 재귀 Retriever 호출 대상)
  true_action → "와이퍼를 작동한다"  (→ 재귀 Retriever 호출 대상)
```

> **META_CONTROL 변수는 단일 값이 아니라 또 다른 TC 문장**입니다. Extractor가 추출한 `condition`, `true_action` 값은 **재귀적으로 Retriever → Extractor 파이프라인으로 다시 처리**됩니다.

```python
META_RECURSIVE_VARS = {"condition", "true_action", "false_action", "action", "unit_action"}

def is_recursive_var(var_name: str) -> bool:
    """해당 변수가 재귀 처리 대상인지 판별"""
    return var_name in META_RECURSIVE_VARS
```

상세 실행 흐름은 [execution_sequence.md §2](execution_sequence.md) 참조.

---

## 7. Tier별 성능 요약

```
입력 100건 기준 예상 처리 분포:

[Tier 1 Regex]    ████████████████████████████████████ 75건  (비용 0)
[Tier 2 Alignment]████████████                          20건  (비용 0)
[Tier 3 SLM]      ██                                     5건  (LLM ~650 tok/건)
[전 Tier 실패]     ░                                      0건  (Approval Queue)
```

| 지표 | 수치 |
| :--- | :--- |
| 평균 비용/100건 | ~3,250 tok (Tier 3 5% 가정) |
| 방안 B 대비 절감 | ~67% (방안 B는 전체 LLM 추출) |
| Tier 1 적중 목표 | ≥ 75% (regex_pattern 품질에 의존) |

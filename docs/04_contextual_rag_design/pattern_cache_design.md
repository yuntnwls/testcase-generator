# Pattern Cache Layer 설계

본 문서는 방안 C 아키텍처의 `Pattern Cache` 모듈 상세 설계를 다룹니다. Pattern Cache는 "확장 예정 기능"이 아닌, **방안 C 아키텍처의 핵심 레이어**입니다. Retriever 호출 전 최우선으로 동작하며, 정확도와 처리 속도를 함께 보장합니다.

*   **컴포넌트**: `src/core/pattern_cache.py`
*   **관련 문서**: [architecture.md](architecture.md)

---

## 1. 왜 Pattern Cache가 필요한가?

Pattern Cache는 단순한 비용 절감 수단이 아닙니다. **정확도와 속도를 동시에 끌어올리는 핵심 메커니즘**입니다.

| 관점 | 효과 | 근거 |
| :--- | :--- | :--- |
| **비용** | Retriever~Validator 전 단계 호출 0 | 캐시 히트 시 임베딩 연산, LLM 호출 없음 |
| **정확도** | **이미 검증 완료된 코드를 그대로 반환** | LLM Fallback으로 인한 새로운 환각 리스크 없음 |
| **일관성** | 동일 입력 → 항상 동일 출력 | 비결정적 LLM을 우회하므로 100% 재현 가능 |
| **응답 속도** | ms 단위 응답 | DB 검색과 LLM 호출 전 단계 생략 |

> LLM은 같은 입력에도 매번 다른 출력을 낼 수 있습니다. Pattern Cache를 먼저 조회하면, **"이미 사람이 검증하거나 Validator가 통과시킨 코드"**를 재사용하므로 정확도가 구조적으로 보장됩니다.

---

## 2. 설계 명세

### 2.1. 키(Key) 전략 — 정규화 후 해시

캐시 키는 입력 문장 원문이 아닌 **정규화된 형태**를 사용합니다. 동일 의도의 표현 변형(공백, 대소문자, 조사 등)을 같은 키로 처리해 히트율을 높입니다.

```python
import hashlib
import re

def normalize_input(text: str) -> str:
    """
    캐시 키 생성을 위한 입력 정규화.
    "좌측  헤드램프를 켜라" / "좌측 헤드램프 켜라" 를 동일하게 처리.
    """
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)         # 연속 공백 하나로
    text = re.sub(r'[을를은는이가]', '', text)  # 조사 제거
    text = re.sub(r'[.,!?]', '', text)        # 구두점 제거
    return text

def make_cache_key(text: str, variant: str) -> str:
    """
    정규화 텍스트 + 차종(variant) 컨텍스트를 포함한 캐시 키 생성.
    같은 표현도 차종마다 다른 ECU/Signal에 매핑될 수 있으므로 variant를 포함.
    """
    normalized = normalize_input(text)
    raw_key = f"{variant}::{normalized}"
    return hashlib.sha256(raw_key.encode()).hexdigest()[:16]
```

### 2.2. 값(Value) 구조 — 렌더링된 코드 + 메타데이터

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CacheEntry:
    rendered_code: str        # Jinja2 렌더링 완료, Validator 통과된 최종 코드
    template_id: str          # 생성에 사용된 Vector DB 템플릿 ID
    source_text: str          # 원본 입력 문장 (디버깅용)
    hit_count: int            # 캐시 조회 횟수 (히트율 분석용)
    created_at: datetime      # 최초 캐싱 시각
    validated: bool           # Validator 통과 여부 (항상 True여야 함)
```

> `rendered_code`는 **Validator가 통과한 코드**만 저장됩니다. 따라서 캐시에서 꺼낸 코드는 별도 재검증 없이 즉시 출력 가능합니다.

### 2.3. 교체 정책(Eviction) — LRU + 최대 사이즈

**LRU (Least Recently Used)** 란, 캐시가 가득 찼을 때 **"가장 오랫동안 사용되지 않은 항목을 먼저 제거"**하는 교체 알고리즘입니다.

```
캐시 상태 (순서: 왼쪽=오래됨, 오른쪽=최근 사용)

초기:   [A] [B] [C] [D] [E]   ← 최대 5개
새 항목 F 추가 시:
    → A가 가장 오래됨 → A 제거
    → [B] [C] [D] [E] [F]

D를 다시 조회하면:
    → D 순서 갱신 (최근 사용으로 뒤로 이동)
    → [B] [C] [E] [F] [D]
```

> **왜 LRU인가?** TC 배치 처리 특성상 한 세션에서 동일 패턴이 반복 등장합니다. LRU는 최근에 쓰인 패턴을 캐시에 유지하므로, 순차적으로 처리되는 TC 배치에서 히트율이 가장 높습니다.

다른 정책과의 비교:

| 정책 | 설명 | 이 시스템에서의 적합성 |
| :--- | :--- | :--- |
| **LRU** | 최근 미사용 항목 제거 | ✅ 배치 내 반복 패턴 유지에 최적 |
| FIFO | 먼저 들어온 항목 먼저 제거 | ❌ 자주 쓰는 초기 패턴이 밀려남 |
| LFU | 사용 빈도 낮은 항목 제거 | ⚠️ 초기 누적 기간 동안 정확도 낮음 |
| TTL | 시간 만료 후 제거 | ⚠️ 장기 반복 패턴을 불필요하게 제거 |

```python
from collections import OrderedDict

class PatternCache:
    """
    LRU(Least Recently Used) 기반 인메모리 캐시.
    - 최근에 가장 적게 쓰인 항목부터 제거
    - TC 배치 처리 특성상 세션 내 반복 패턴이 집중되므로 LRU가 최적
    """
    MAX_SIZE = 1000       # 최대 캐시 엔트리 수 (메모리 ~수 MB 수준)

    def __init__(self):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> CacheEntry | None:
        if key not in self._cache:
            return None
        # 조회 시 순서 갱신 (LRU: 최근 사용 → 뒤로)
        self._cache.move_to_end(key)
        entry = self._cache[key]
        entry.hit_count += 1
        return entry

    def put(self, key: str, entry: CacheEntry) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = entry
        # 최대 크기 초과 시 가장 오래된(앞쪽) 항목 제거
        if len(self._cache) > self.MAX_SIZE:
            self._cache.popitem(last=False)
```

### 2.4. 캐시 무효화(Invalidation) 전략

Vector DB 템플릿이 업데이트되면 해당 템플릿으로 생성된 캐시가 낡을 수 있습니다.

```python
def invalidate_by_template(cache: PatternCache, template_id: str) -> int:
    """
    특정 템플릿 ID를 사용한 캐시 엔트리 일괄 삭제.
    Vector DB 템플릿 수정 시 build_vector_db.py 후처리로 자동 호출.
    """
    keys_to_delete = [
        k for k, v in cache._cache.items()
        if v.template_id == template_id
    ]
    for k in keys_to_delete:
        del cache._cache[k]
    return len(keys_to_delete)  # 무효화된 엔트리 수 반환
```

---

## 3. 전체 처리 흐름 (Cache 포함)

```
자연어 TC Step 입력
        │
        ▼
✅ 1. normalize_input() + make_cache_key()
        │
        ▼
✅ 2. PatternCache.get(key)
        ├─ 히트 → CacheEntry.rendered_code 즉시 반환
        │         (Retriever, Extractor, Assembler, Validator 전부 생략)
        │         정확도: 100% (이미 검증된 코드)
        │         비용: 0
        │
        └─ 미스 ▼
✅/🔴 3~6. Retriever → Extractor → Assembler(Jinja2) → Validator
        │         (기존 파이프라인 전체 실행)
        │
        ▼
✅ 7. Validator 통과 시 PatternCache.put(key, CacheEntry) 저장
        │         이후 동일 패턴은 캐시에서 처리
        ▼
    출력 코드
```

---

## 4. 자가 학습 루프 — 캐시가 시스템을 스스로 개선

Pattern Cache는 단순 반복 패턴 처리 이상의 역할을 합니다. **운영 데이터가 쌓일수록 LLM Fallback 빈도가 구조적으로 감소**합니다.

```
초기 운영
    LLM Fallback이 처리한 결과도 Validator 통과 시 캐시에 저장
        ↓
시간 경과
    이전에 LLM이 힘겹게 처리했던 패턴이 캐시에서 즉시 처리
        ↓
장기 운영
    동일 차종·프로젝트 내 TC의 80%+ 가 캐시 히트 → 사실상 실시간 처리
```

> 방안 C의 최종 형태는 **"Contextual RAG가 LLM을 교육하고, 교육된 결과가 캐시에 쌓여 LLM을 점점 덜 필요로 하는 자가 성장 시스템"**입니다.

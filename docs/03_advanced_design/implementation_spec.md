# 구현을 위한 상세 데이터 명세서 (Implementation Spec)


## 1. 입/출력 인터페이스 규격 (Input/Output Interface Spec)

### 1-1. Input: TC Excel / TSV 구조
지능형 엔진이 파싱하여 Vector DB 검색 모드(Metadata Filter `type`)를 결정하는 기준 테이블입니다.
*   **파일 포맷**: 탭 분리 문자열(`.tsv`) 또는 엑셀(`.xlsx`)
*   **필수 헤더 (Column Mapping)**:
    1.  `TC_ID`: 트레이스 및 에러 로깅을 위한 식별자 (예: `TC_BODY_001`)
    2.  `초기화 (Init)`: `TYPE_INIT` 필터 적용
    3.  `시험전조건 (Pre-condition)`: `TYPE_PRECONDITION` 필터 적용
    4.  `시험방법 (Step/Action)`: `TYPE_ACTION` / `TYPE_CONTROL` 필터 적용
    5.  `판정조건 (Judgment)`: `TYPE_JUDGMENT` 필터 적용

### 1-2. Output: Target Script 골격 (Boilerplate)
분절된 템플릿(예: `simva.set_signal()`)들을 감싸서, 실제 IDE나 Test Environment에서 바로 실행 가능한 완전한 `.py` 파일로 조립(Assembly)하기 위한 뼈대입니다.

```python
# [Target Script Boilerplate 예시 - SIMVA 기준]
import time
from simva_framework import SimvaCore
from vehicle_signals import signals, profiles

def test_{tc_id}(simva: SimvaCore):
    """
    [TC Objective]: 자동 생성된 테스트 케이스 (Next-Gen Engine)
    """
    # 1. 초기화 (Init Phase)
    # {init_blocks}

    # 2. 시험 전 조건 (Pre-condition Phase)
    # {precond_blocks}

    # 3. 시험 방법 (Action Phase)
    # {action_blocks}

    # 4. 판정 조건 (Judgment Phase)
    # {judgment_blocks}
    
    return "PASS"
```

---

## 2. 내부 모듈 간 데이터 통신 객체 (DTO - Pydantic Models)

각 4단계 레이어 간에 데이터를 주고받을 때 명확히 타입이 지정된 Pydantic 모델을 사용합니다.

```python
from pydantic import BaseModel, Field
from typing import Dict, Optional, List

class VectorTemplate(BaseModel):
    """Vector DB에서 검색된 결과 객체"""
    template_id: str
    target_code: str
    metadata_type: str        # 예: "TYPE_ACTION"
    regex_pattern: Optional[str] # 정규식 추출용 (Tier 1)

class ExtractedVariables(BaseModel):
    """Extractor가 뽑아낸 원시(Raw) 변수들"""
    raw_signal: Optional[str] = Field(description="예: '운전석 윈도우'")
    raw_value: Optional[str]  = Field(description="예: '완전 개방'")

class NormalizedEntity(BaseModel):
    """Ontology DB를 거쳐 정규화된 최종 엔티티"""
    ecu_name: str             # 예: "BCM"
    signal_id: str            # 예: "WindowPos_FL"
    cast_value: any           # 예: 100 (Type Enforced int)

class AssemblyBlock(BaseModel):
    """최종 조립 대기 중인 코드 블럭"""
    tc_id: str
    phase: str                # "init", "precond", "action", "judgment"
    assembled_code: str
```

---

## 3. 실물 기술 스택 및 오픈소스 의존성 (Tech Stack)

독립적인 구현을 위해 확정/권장되는 서드파티 라이브러리 목록입니다.

1.  **Vector DB**: `ChromaDB` (로컬 파일 임베딩 용이, 파이썬 네이티브 지원 훌륭)
2.  **임베딩 모델 (Sentence Transformers)**: `all-MiniLM-L6-지능형 모델` (가볍고 로컬 실행이 빠름, 다국어 처리 필요시 `paraphrase-multilingual-MiniLM-L12-지능형 모델`)
3.  **Ontology DB**: `NetworkX` (파이썬 내장 그래프 라이브러리, 소규모 관리용) 또는 `Neo4j` (대규모 확장을 고려할 경우)
4.  **언어 모델 (LLM SDK)**: 
    *   `LangChain`: 프롬프트 체이닝 및 RAG 오케스트레이션
    *   `Ollama` (백엔드 로컬 Llama 3) 또는 `OpenAI(gpt-4o-mini)` API (배치 속도 극대화용)
5.  **데이터 검증 (Validation)**: `Pydantic 지능형 모델`

---

## 5. 설정 및 환경 변수 (Configuration & Bootstrapping)

### 5-1. 정적 환경 변수 (.env)
시스템 로딩 시 최초 1회 읽어 들이는 인프라 및 경로 설정입니다.

```env
# System Path
TC_FILE_PATH=./data/inputs/Body_Control_TC.xlsx
OUTPUT_SCRIPT_DIR=./outputs/scripts

# Vector DB Settings
CHROMA_PERSIST_DIR=./data/vector_db_storage
EMBEDDING_MODEL_NAME=all-MiniLM-L6-지능형 모델
SIMILARITY_THRESHOLD=0.85
```

### 5-2. 동적 LLM 스위칭 (UI Dynamic Configuration)
사용자가 **관리자 UI(대시보드)**에서 실시간으로 LLM 제공자(Provider)와 모델(Model)을 변경할 수 있도록 설계되어야 합니다. `.env`에 하드코딩하지 않고 데이터베이스나 인메모리 Config 객체로 관리되어 즉시 반영(Hot-Reload) 대상이 됩니다.

*   **UI 설정 항목 예시 (Settings Modal)**:
    - **LLM Provider**: `[ Dropdown: OpenSource(Ollama) | OpenAI | AzureOpenAI | Anthropic ]`
    - **Current Model**: `[ Dropdown: llama3:8b | gpt-4o-mini | claude-3-haiku ... ]`
    - **API Endpoint / Key**: (Provider에 따라 동적 생성되는 Input Box)
    - **Temperature**: `[ Slider: 0.0 ~ 1.0 ]` (Fallbacks에서는 환각 방지를 위해 0.0 권장)

*   **백엔드 설계 요구사항 (Factory Pattern)**:
    UI에서 설정이 변경되면, 즉시 `LLMFactory` 클래스가 이전 세션을 닫고 선택된 Provider의 LangChain 객체(`ChatOllama`, `ChatOpenAI` 등)를 새로 인스턴스화하여 Core Engine에 주입해야 합니다.

*   **저장 매체**: 내부 SQLite (`config.db`) 내 `llm_settings` 테이블을 활용하거나, 파일 기반(`settings.json`)으로 저장하여 재부팅 시에도 마지막에 UI에서 선택한 모델이 유지되도록 구성합니다.

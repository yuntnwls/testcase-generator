# 프로젝트 디렉토리 구조 및 설정 파일 규격

본 문서는 **Phase 2 (구현 단계)**를 시작하기 위해 물리적으로 생성할 프로젝트의 파일/폴더 아키텍처와 주요 설정(`config.yaml`)의 규격을 정의합니다.

---

## 1. 디렉토리 아키텍처 (Directory Structure)

관심사의 분리(Separation of Concerns) 원칙에 따라 크게 `core`, `adapters`, `db`, `ui` 4개의 레이어로 물리적인 폴더를 분리합니다.

```text
testcase-generator/
├── config/
│   └── config.yaml                 # 전체 시스템 통합 설정 파일 (로깅, LLM 등)
├── data/                           # 영구 저장 데이터 (git 무시 권장)
│   ├── vector_db/                  # ChromaDB 로컬 파일 저장소
│   ├── ontology/
│   │   └── mock_ontology_db.json   # 선행조건/관계 룰 파일
│   └── tc_data/                    # 사용자 업로드 또는 샘플 TC 데이터 (mock_tc_data.tsv)
├── logs/                           # 구조화된 로그 출력 폴더 (.gitignore 처리)
│   └── app.jsonl                   # 기계 및 분석 도구용 순수 JSON JSONL 로그
├── src/
│   ├── core/                       # Core Engine (LLM 및 데이터 흐름 제어)
│   │   ├── __init__.py
│   │   ├── engine.py               # 파이프라인 메인 관제 (Trace ID 발급, UI 통신)
│   │   ├── parser.py               # 엑셀 TC 파싱 및 Validation (Retry Loop 포함)
│   │   ├── rag_engine.py           # VectorDB & Ontology 하이브리드 검색
│   │   ├── prompt_builder.py       # 동적 프롬프트 생성기
│   │   ├── llm_provider.py         # LLM Interface 및 Provider 팩토리 (DI 대상)
│   │   └── models.py               # Pydantic IR 모델 및 에러 정의
│   ├── adapters/                   # 타겟 언어별 어댑터 프로세스 (독립 실행)
│   │   ├── __init__.py
│   │   ├── base_adapter.py         # BaseAdapter 추상 클래스 (SDK, StdIO 규약)
│   │   ├── simva_adapter.py        # SIMVA 타겟 생성기
│   │   └── capl_adapter.py         # (Future) CAPL 타겟 생성기
│   └── ui/
│       └── streamlit_app.py        # 메인 웹 서비스 UI 인터페이스
├── tests/                          # 단위 테스트 및 통합 테스트
│   ├── integration/                # 외부 의존성(로컬) 연결 E2E 연동 테스트
│   │   ├── test_pipeline_local_llm.py # Ollama 연결 통합 변환 파이프라인 테스트
│   │   └── test_rag_actual.py      # 구축된 임베딩(Vector DB) 기반 RAG 실제 검색 테스트
│   └── test_parser.py              # 파서 정규식 및 Validation 유닛 테스트
├── requirements.txt                # 파이썬 패키지 의존성
└── main.py                         # CLI 진입점 및 의존성 주입(DI) 부트스트래퍼
```

### 1.1. 각 레이어별 설계 제약 (Constraints)
- **`src/core/` 규칙**: 이 폴더 내부의 코드는 `Target Language(SIMVA)`나 특정 `LLM(OpenAI)`에 종속적인 코드를 단 한 줄도 가져서는 안 됩니다. 인터페이스와 설정 파일에만 의존해야 합니다.
- **`src/adapters/` 규칙**: 메인 프로세스와 메모리 공유를 엄격히 금지합니다. 오직 `stdin`으로 JSON을 받고 `stdout`으로 최종 코드를 출력하며, 패키지 `import` 시 상위 디렉토리(`core`)를 참조하지 않도록 독립성을 유지해야 합니다.
- **`data/` 규칙**: 시스템이 재구동되어도 유지되어야 하는 상태(State) 데이터이며, 데이터 소스 경로를 코드에 하드코딩하지 않고 반드시 `config.yaml`을 통해 관리합니다.

---

## 2. 통합 설정 파일 (`config.yaml`) 스키마 설계

사용자(또는 관리자)가 파이썬 코드를 한 줄도 수정하지 않고 시스템의 동작 방식을 바꿀 수 있어야 합니다. 

```yaml
# ==========================================
# Universal Test Script Generator - Config
# ==========================================

# 1. LLM Provider 설정 (의존성 주입 대상)
llm:
  # 사용 가능한 타입: "mock", "local", "openai", "gemini"
  type: "local" 
  max_retries: 3 # LLM Self-Correction (Topic 1) 최대 재시도 횟수
  
  # Local CPU LLM 설정 (type이 'local'일 때 작동, 비용 절감형 테스트용)
  local:
    endpoint: "http://localhost:11434/api/generate" # Ollama 기본 주소
    model_name: "llama3:8b" 
    timeout_sec: 120
    
  # OpenAI / Gemini API 설정 (Production 용)
  openai:
    api_key: "${OPENAI_API_KEY}"
    model_name: "gpt-4o"
    temperature: 0.1

# 2. Database (RAG) 설정
database:
  vector_db_path: "./data/vector_db"
  ontology_path: "./data/mock_ontology_db.json"
  similarity_threshold: 0.75 # 이 점수 이하면 UNKNOWN 처리 (정확도 확보)

# 3. Target Adapter 설정 (Subprocess 실행 방식)
target:
  active_adapter: "simva" 
  adapters:
    simva:
      executable_path: "./src/adapters/simva_adapter.py"
      # Adapter 프로세스 띄울 때 사용할 Python 인터프리터 경로
      python_bin: "python" 

# 4. UI 및 추적성(Traceability) 설정
system:
  log_level: "INFO" # DEBUG, INFO, WARNING, ERROR
  ui_theme: "light" # light, dark
  enable_progress_bar: true
  
  logging:
    # structlog Dual-Output 설정
    console_log_enabled: true
    json_log_path: "./logs/app.jsonl"
```

## 3. 설정 파일 작동 원리 (Dependency Injection)

`src/core/llm_provider.py` 내부에서는 위 yaml 파일을 읽어서 다음과 같이 **동적 팩토리 패턴**으로 객체를 생성합니다.

```python
# src/core/llm_provider.py (가상 구현체)
from abc import ABC, abstractmethod
import yaml
import os

class ILLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str: pass

class LocalOllamaProvider(ILLMProvider):
    def __init__(self, config):
        self.endpoint = config['local']['endpoint']
        # ... Ollama 초기화
        
class GeminiProvider(ILLMProvider):
    def __init__(self, config):
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(config['gemini']['model_name'])
        
    def generate(self, prompt: str) -> str:
        # Pydantic JSON 응답을 강제하는 Generation Config 활용 가능
        response = self.model.generate_content(prompt)
        return response.text

# Factory Function
def get_llm_provider(config_path: str) -> ILLMProvider:
    with open(config_path, 'r') as f:
        cfg = yaml.safe_load(f)
        
    llm_type = cfg['llm']['type']
    
    if llm_type == "local":
        return LocalOllamaProvider(cfg['llm'])
    elif llm_type == "gemini":
        return GeminiProvider(cfg['llm'])
    elif llm_type == "openai":
        return OpenAIProvider(cfg['llm'])
    else:
        raise ValueError(f"지원하지 않는 LLM 타입입니다: {llm_type}")
```

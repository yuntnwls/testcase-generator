# 프로젝트 디렉토리 구조 및 설정 파일 규격

본 문서는 **Phase 2 (구현 단계)**를 시작하기 위해 물리적으로 생성할 프로젝트의 파일/폴더 아키텍처와 주요 설정(`config.yaml`)의 규격을 정의합니다.

---

## 1. 디렉토리 아키텍처 (Directory Structure)

관심사의 분리(Separation of Concerns) 원칙에 따라 크게 `core`, `adapters`, `db`, `ui` 4개의 레이어로 물리적인 폴더를 분리합니다.

```text
testcase-generator/
├── config/
│   └── config.yaml                 # 전체 시스템 통합 설정 파일
├── data/                           # 영구 저장 데이터 (git 무시 권장)
│   ├── vector_db/                  # ChromaDB 로컬 파일 저장소
│   └── ontology/
│       └── graph_rules.json        # 선행조건/관계 룰 파일
├── src/
│   ├── core/                       # Core Engine (LLM 및 데이터 흐름 제어)
│   │   ├── __init__.py
│   │   ├── parser.py               # 엑셀 TC 파싱 모듈
│   │   ├── rag_engine.py           # VectorDB & Ontology 연동 모듈
│   │   ├── prompt_builder.py       # 동적 프롬프트 생성기
│   │   ├── llm_provider.py         # LLM Interface 및 Factory
│   │   └── models.py               # Pydantic IR 모델 정의 (BaseIR, SetIR 등)
│   ├── adapters/                   # 타겟 언어별 어댑터 프로세스 (독립 실행)
│   │   ├── __init__.py
│   │   ├── simva_adapter.py        # SIMVA 타겟 파이썬 생성기
│   │   └── capl_adapter.py         # (Future) CAPL 타겟 생성기
│   └── ui/
│       └── streamlit_app.py        # 메인 웹 서비스 UI 인터페이스
├── tests/                          # 단위 테스트 및 통합 테스트
│   ├── ui_mock/
│   ├── test_rag.py
│   └── test_parser.py
├── requirements.txt                # 파이썬 패키지 의존성
└── main.py                         # CLI 진입점 (혹은 ui/streamlit_app.py 직접 실행)
```

### 1.1. 각 레이어별 설계 제약 (Constraints)
- **`src/core/` 규칙**: 이 폴더 내부의 코드는 `Target Language(SIMVA)`나 특정 `LLM(OpenAI)`에 종속적인 코드를 단 한 줄도 가져서는 안 됩니다. 인터페이스와 설정 파일에만 의존해야 합니다.
- **`src/adapters/` 규칙**: 메인 프로세스와 메모리 공유를 엄격히 금지합니다. 오직 `stdin`으로 JSON을 받고 `stdout`으로 최종 코드를 출력하며, 패키지 `import` 시 상위 디렉토리(`core`)를 참조하지 않도록 독립성을 유지해야 합니다.
- **`data/` 규칙**: 시스템이 재구동되어도 유지되어야 하는 상태(State) 데이터이며, DB 교체(예: 로컬 파일 -> 원격 DB서버)가 언제든 가능하도록 파이썬 코드 상위 경로를 절대 참조(Hard-coding)하지 않고 반드시 `config.yaml`을 통해 경로를 받아와야 합니다.

---

## 2. 통합 설정 파일 (`config.yaml`) 스키마 설계

사용자(또는 관리자)가 파이썬 코드를 한 줄도 수정하지 않고 시스템의 동작 방식을 바꿀 수 있어야 합니다. 

```yaml
# ==========================================
# Universal Test Script Generator - Config
# ==========================================

# 1. LLM Provider 설정 (로컬 및 클라우드 동적 스위칭)
llm:
  # 사용 가능한 타입: "local", "openai", "gemini"
  type: "local" 
  
  # Local CPU LLM 설정 (type이 'local'일 때 작동)
  local:
    endpoint: "http://localhost:11434/api/generate" # Ollama 기본 주소
    model_name: "llama3:8b" # 또는 사내 파인튜닝 모델
    timeout_sec: 120
    
  # OpenAI 설정 (type이 'openai'일 때 작동)
  openai:
    api_key: "${OPENAI_API_KEY}" # 환경변수 권장
    model_name: "gpt-4o"
    temperature: 0.1
    
  # Google Gemini API 설정 (type이 'gemini'일 때 작동)
  gemini:
    api_key: "${GEMINI_API_KEY}"
    model_name: "gemini-1.5-pro"
    temperature: 0.1

# 2. Database (RAG) 설정
database:
  vector_db_path: "./data/vector_db"
  ontology_path: "./data/ontology/graph_rules.json"
  similarity_threshold: 0.75 # 이 점수 이하면 UNKNOWN 처리 (정확도 확보)

# 3. Target Adapter 설정
target:
  # 현재 사용할 어댑터 종류
  active_adapter: "simva" 
  
  adapters:
    simva:
      executable_path: "./src/adapters/simva_adapter.py"
      signal_registry_path: "./example_targets/simva_signals.py"
      macro_registry_path: "./example_targets/simva_macros.py"

# 4. UI 및 Logging 설정
system:
  log_level: "INFO" # DEBUG, INFO, WARNING, ERROR
  ui_theme: "light" # light, dark
  enable_progress_bar: true
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

# SIMVA Test Automation Solution

자연어 기반의 테스트 케이스(TC)를 분석하여 **SIMVA 자동화 스크립트(Python)**로 변환해주는 AI 기반 솔루션입니다.

## 🚀 주요 기능

- **자동 변환 (LLM-based Generation)**: Excel 또는 TSV 형식의 자연어 TC를 분석하여 최적의 SIMVA Python 코드를 생성합니다.
- **시그널 매핑 (Smart Mapping)**: `signals.py` 및 `Signal.cfg`를 참조하여 TC 내의 변수명을 실제 코드 프로젝트의 시그널 경로로 정확하게 매핑합니다.
- **하이브리드 입력 방식**:
    - **Excel/TSV 업로드**: 대량의 TC를 한 번에 변환.
    - **GUI 직접 입력**: Streamlit 대시보드를 통해 화면에서 직접 TC를 작성하고 수정 가능.
- **정적 검증**: 생성된 코드의 문법 오류 및 시그널 유효성을 사전에 검사합니다.

## 🛠 기술 스택

- **Language**: Python 3.9+
- **Frontend**: Streamlit (대시보드 및 데이터 편집)
- **Data Analysis**: Pandas, Regular Expressions
- **Core Engine**: LLM (OpenAI GPT 등), AST (Python 정적 분석)

## 📂 프로젝트 구조

```text
TestscriptGenerator/
├── data/               # 매뉴얼, 샘플 TC, Signal.cfg 등 원천 데이터
├── docs/               # 상세 분석 및 설계 문서
│   ├── 01_analysis/    # TC 및 시그널 데이터 분석 결과
│   └── 02_design/      # 시스템 아키텍처 및 상세 설계서
├── src/                # 실제 구현 소스 코드 (예정)
└── README.md           # 프로젝트 개요 (본 파일)
```

## 📝 문서 가이드

자세한 설계 및 분석 내용은 아래 문서를 참조하십시오.
1. [상세 분석 보고서](docs/01_analysis/analysis_report.md)
2. [상세 설계서](docs/02_design/detailed_design.md)
3. [GUI 개발 제안서](docs/02_design/ui_proposal.md)

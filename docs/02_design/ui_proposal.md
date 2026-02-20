# [범용 테스트 스크립트 자동화 UI 제안서]

## 1. 개요
사용자가 엑셀 파일을 업로드하거나, 화면에서 직접 테스트 케이스(TC)를 입력하여 Python 스크립트로 변환할 수 있는 도구(GUI)의 기술 스택과 설계를 제안합니다.

## 2. 추천 기술 스택: Python + Streamlit
가장 효율적이고 파이썬 친화적인 **Streamlit**을 강력히 추천합니다.

### 2.1. 선정 이유
1.  **단일 언어(Python) 통일**:
    - 파싱 로직(`pandas`), 시그널 로더(`signals.py` 분석), 코드 생성기(LLM)가 모두 Python이므로, 별도의 API 서버 구축 없이 하나의 프로세스에서 즉시 연동 가능합니다.
2.  **강력한 데이터 핸들링**:
    - 엑셀과 같은 **테이블 편집 기능(`st.data_editor`)**을 기본 제공하여, 엑셀을 업로드하고 화면에서 바로 수정하거나 빈 테이블에 직접 입력하는 UX를 손쉽게 구현할 수 있습니다.
3.  **개발 속도**:
    - 복잡한 프론트엔드(HTML/CSS/JS) 지식 없이도 몇 시간 내에 기능이 완벽히 동작하는 프로토타입을 만들 수 있습니다.

### 2.2. 비교 (vs React/Web)
| 구분 | Streamlit (추천) | React + FastAPI | Electron (Desktop) |
| :--- | :--- | :--- | :--- |
| **언어** | Python 100% | JS/TS + Python | JS/TS + Python |
| **개발 난이도** | 하 | 상 (Frontend 별도 개발) | 상 |
| **데이터 연동** | 직접 호출 (Memory 공유) | REST API 통신 | IPC/API 통신 |
| **적합성** | **내부 도구 / 엔지니어 툴** | 대고객 서비스 (SaaS) | 설치형 배포 필요 시 |

## 3. 상세 기능 설계 (UX Flow)

### 3.1. 화면 구성 (Layout)
- **사이드바**: 설정 (OpenAI API Key 입력, Signal.cfg 경로 설정, LLM 모델 선택)
- **메인 탭 1: 파일 변환 (File Convert)**
    - 엑셀/TSV 파일 드래그 앤 드롭 업로드.
    - 업로드된 내용 미리보기 (DataFrame).
    - [변환] 버튼 클릭 시 Python 스크립트 생성 및 다운로드.
- **메인 탭 2: 수동 생성 (Manual Builder)**
    - 엑셀과 유사한 **Editable Data Processing Grid** 제공.
    - **자동완성 지원**: 'Signal Name' 입력 시 `Signal Registry`에서 검색된 유사 시그널 추천.
    - 단계별 입력(Step-by-Step) 폼 제공:
        - Step 1: Pre-condition 입력
        - Step 2: Test Action 입력 (시그널 선택 + 값 입력)
        - Step 3: Expected Result 입력

### 3.2. 핵심 기능 구현 방안
1.  **엑셀 편집기 (Editable DataFrame)**:
    ```python
    import streamlit as st
    import pandas as pd

    # 빈 템플릿 또는 업로드된 데이터 로드
    df = pd.DataFrame(columns=["Step", "Action", "Value", "Description"])
    
    # 엑셀처럼 편집 가능한 위젯
    edited_df = st.data_editor(df, num_rows="dynamic")
    ```

2.  **시그널 검색 연동**:
    - 사용자가 입력창에 "Door"를 치면, 백엔드의 `SignalRegistry.search("Door")`를 호출하여 `signals.BDC.DoorStatus` 등의 후보를 드롭다운으로 보여줍니다.

## 4. 결론 및 제안
현재 개발 중인 핵심 로직(파서, 로더, 생성기)을 그대로 활용하면서 사용자 편의성을 높이기 위해 **Streamlit** 기반의 웹 애플리케이션으로 개발 방향을 잡는 것을 제안합니다.

이 제안이 승인되면, 구현 단계에서 `app.py`를 추가하여 웹 인터페이스를 제공할 수 있습니다.

# [SIMVA 자동화 솔루션 상세 설계서]

## 1. 시스템 아키텍처 설계

### 1.1. 전체 구성도
```mermaid
graph TD
    subgraph Input_Layer [입력 계층]
        TC_File[TC 정의서 (Excel/TSV)]
        Signal_CFG[Signal.cfg (CSV)]
    end

    subgraph Parsing_Layer [분석 및 파싱 계층]
        TC_Parser[TC 파서 (Macro & Regex)]
        Signal_Loader[시그널 로더 (Index & Vector DB)]
        TC_File --> TC_Parser
        Signal_CFG --> Signal_Loader
    end

    subgraph Logic_Layer [변환 및 생성 계층]
        Mapper[매핑 엔진 (Fuzzy/RAG Matcher)]
        Prompt_Engine[프롬프트 엔진 (Context 구성)]
        LLM[LLM (OpenAI GPT)]
        
        TC_Parser --> Mapper
        Signal_Loader --> Mapper
        Mapper -- "매핑된 시그널 정보" --> Prompt_Engine
        TC_Parser -- "Action Step 정보" --> Prompt_Engine
        Prompt_Engine --> LLM
    end

    subgraph Output_Layer [출력 계층]
        Code_Gen[코드 생성기]
        Validator[정적 검증기 (Syntax Check)]
        Final_Script[Python Test Script (.py)]
        
        LLM --> Code_Gen
        Code_Gen --> Validator
        Validator --> Final_Script
    end
```

## 2. 모듈별 상세 설계 및 구현 계획

### 2.1. Signal Loader (Code Registry 구축) - **핵심 변경**
- **기존 설계**: `Signal.cfg`만 참조 -> **변경 설계**: `signals.py`를 **Source of Truth**로 사용.
- **책임**: Python 프로젝트 내 `signals.py`를 로드하여 사용 가능한 모든 시그널 경로(`signals.BDC.SignalName`)를 인덱싱.
- **구현 상세**:
    - **Method**: `load_signal_definitions()`
    - **Logic**:
        1. `signals.py`를 `import`하거나 `ast`로 파싱.
        2. `signals` 모듈 하위의 클래스(Profile)와 속성(Signal)을 순회.
        3. **Mapping Dictionary** 생성:
            - Key: `Signal Name` (예: `NM_State_BDC_FD_BCAN1`)
            - Value: `Full Path` (예: `signals.BDC.NM_State_BDC_FD_BCAN1`)
            - Metadata: `Signal.cfg`에서 로드한 데이터 타입 정보 병합 (Optional).
    - **Search Strategy**: 
        - 입력된 TC 변수명과 Mapping Dictionary의 **Key** 간 유사도 검색 수행.
        - 검색 결과로 **Value (Full Path)**를 반환하여 코드 생성에 즉시 사용 가능하도록 함.

### 2.2. TC Parser (엑셀 파서)
- **책임**: 비정형 텍스트(`#1. (Set = 1)`)를 구조화된 데이터로 변환.
- **구현 상세**:
    - **Class**: `TCParser`
    - **Logic**:
        - 정규식 `re.compile(r"(\d+)\.\s*\(([^=]+)\s*=\s*([^)]+)\)")` 활용.
        - `Step` 객체 리스트 생성: `[{'step': 1, 'action': 'VehicleSpeed', 'value': '0x5'}, ...]`

### 2.3. Mapper & Prompt Engine (핵심 로직)
- **책임**: 파싱된 데이터와 시그널 DB를 결합하여 LLM 프롬프트 생성.
- **Prompt Template 전략**:
    - **Role Definition**: "SIMVA 스크립트 변환 전문가"
    - **Signal Dictionary Injection**:
        ```text
        [Relevant Signals]
        - Query: "VehicleSpeed" -> Found: "VehicleSpeed_Info_BDC" (uint16)
        - Query: "Lamp_Puddle" -> Found: "PuddleLamp_Status" (bool)
        ```
    - **Rule Injection**:
        ```text
        [Rules]
        1. Convert 'Set X = Y' to 'simva.set_signal(signals.BDC.X, Y)'
        2. Convert 'Wait(T)' to 'simva.wait(T/1000.0)'
        ```

### 2.4. Code Generator & Validator
- **책임**: LLM 응답 수신 및 유효성 검증.
- **구현 상세**:
    - **Validation Logic**:
        - Python `ast` 모듈을 사용하여 Syntax Error 검사.
        - 생성된 코드 내 `signals.XXX` 경로가 실제 `SignalDatabase`에 존재하는지 Cross-Check.
    - **Error Handling**: 검증 실패 시 에러 로그와 함께 재생성 요청(Retry) 또는 주석 처리하여 출력.

## 3. 데이터 흐름 예시 (Data Flow Walkthrough)

1.  **Input**: TC의 `Test Procedure` 셀에서 `"1. (Lamp_PuddleLamp = On)"` 문자열 읽기.
2.  **Parsing**: `Action="Lamp_PuddleLamp"`, `Value="On"` 추출.
3.  **Signal Search**: `"Lamp_PuddleLamp"`로 `Signal.cfg` 검색 -> 가장 유사한 `"BDC_PuddleLamp_Control"` 발견.
4.  **Prompting**: 
    - "Set `BDC_PuddleLamp_Control` to `1` (On=1). Use `simva.set_signal`."
5.  **Generation**: 
    - `simva.set_signal(signals.BDC.BDC_PuddleLamp_Control, 1)` 코드 생성.
6.  **Writing**: 결과 `.py` 파일에 함수 본문으로 작성.

## 4. 향후 확장성
- **RAG 고도화**: 단순 문자열 유사도를 넘어, 시그널 설명(`Description`)까지 포함한 벡터 검색 도입 가능.
- **GUI 연동**: 변환 과정을 시각화하고, 매핑이 불확실한 경우 사용자가 직접 선택하게 하는 UI 툴로 발전 가능.
 pocket.

import pandas as pd
import re
from typing import List, Dict

class TCParser:
    """
    엑셀 또는 TSV 파일 형식의 테스트 케이스를 읽어들여
    파이프라인에서 순회할 수 있는 단위(Step) 딕셔너리로 변환합니다.
    """
    def __init__(self):
        pass

    def parse_file(self, file_path: str) -> List[Dict]:
        """
        파일 형식(tsv, csv, xlsx)에 따라 읽어들이고 표준화된 구조로 매핑합니다.
        
        예상 출력 구조:
        [
            {
                "tc_id": "SYS_TEST_01",
                "tc_title": "고속도로 정속 주행 시나리오",
                "steps": [
                    {"step_id": 1, "text": "시동을 켠다."},
                    {"step_id": 2, "text": "기어를 D로 변경한다."}
                ]
            }
        ]
        """
        if file_path.endswith('.tsv') or file_path.endswith('.csv'):
            sep = '\t' if file_path.endswith('.tsv') else ','
            df = pd.read_csv(file_path, sep=sep)
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
            
        return self._transform_df_to_tc_list(df)
        
    def _transform_df_to_tc_list(self, df: pd.DataFrame) -> List[Dict]:
        """
        데이터프레임 그룹화 로직 (여기서는 Mock 구조를 하드코딩 패턴으로 추출)
        """
        # 실제 현업 데이터(mock_tc_data.tsv) 컬럼 기준 필수 검사
        required_base_cols = ["T/Case ID", "검증 목적"]
        step_cols = ["Test Step", "시험 방법"]
        
        missing_base = [c for c in required_base_cols if c not in df.columns]
        has_step_col = any(c in df.columns for c in step_cols)
        
        if missing_base or not has_step_col:
             raise ValueError(f"Missing required columns in TC DataFrame. Base: {missing_base}, Step Col Missing: {not has_step_col}")
             
        # 현실적인 파싱: 각 행을 하나의 TC로 보고, Test Step 또는 시험 방법 내부의 번호 매겨진 텍스트를 파싱
        tc_list = []
        for idx, row in df.iterrows():
            tc_id = str(row.get("T/Case ID", f"TC_{idx+1:03d}"))
            tc_title = str(row.get("검증 목적", f"Untitled_TC_{idx}"))
            
            # Test Step 컬럼을 우선적으로 사용, 없으면 시험 방법 사용
            raw_method = ""
            if "Test Step" in df.columns and pd.notna(row.get("Test Step")):
                raw_method = str(row.get("Test Step"))
            else:
                raw_method = str(row.get("시험 방법", ""))
            
            # 정규식을 이용해 "1. ~ \n 2. ~" 형태의 문자열 분리
            # 먼저 줄바꿈으로 나누고 빈 줄 제거
            lines = [line.strip() for line in raw_method.split('\n') if line.strip()]
            
            steps = []
            step_counter = 1
            for line in lines:
                # '1. (Ignition = ON)' 같은 앞자리 포맷 제거 정규식
                cleaned_line = re.sub(r'^\d+\.\s*', '', line).strip()
                if cleaned_line:
                    # '그렇지 않으면' 등 else를 의미하는 문구로 시작하면 이전 스텝에 병합
                    if steps and re.match(r'^(그렇지\s*않|아니면|그\s*외|else|otherwise)', cleaned_line, re.IGNORECASE):
                        steps[-1]["text"] += " " + cleaned_line
                    else:
                        steps.append({
                            "step_id": step_counter,
                            "text": cleaned_line
                        })
                        step_counter += 1
                    
            # Expected Result 필드 추출
            expected_result_text = ""
            if "Expected Result" in df.columns and pd.notna(row.get("Expected Result")):
                expected_result_text = str(row.get("Expected Result")).strip()
                
            tc_list.append({
                "tc_id": tc_id,
                "tc_title": tc_title,
                "steps": steps,
                "expected_result": expected_result_text
            })
            
        return tc_list

if __name__ == "__main__":
    # 로컬 테스트
    parser = TCParser()
    try:
        tcs = parser.parse_file("./data/tc_samples/mock_tc_data.tsv")
        print(tcs[0])
    except Exception as e:
        print(f"Test failed or file missing: {e}")

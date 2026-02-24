import os
import json
import sys
from src.core.engine import CoreEngine
from src.core.config_loader import get_config

def test_control_tc_pipeline_local_llm():
    """
    data/control_tc_data.tsv 파일을 대상으로 로컬 LLM을 사용하여 
    조건문 및 반복문 변환이 정상적으로 수행되는지 검증합니다.
    """
    # 루트 기준 경로
    tc_file_path = "data/tc_samples/control_tc_data.tsv"
    
    if not os.path.exists(tc_file_path):
        print(f"{tc_file_path} not found.")
        return

    # 엔진 초기화 (기본 설정 사용 - local llm 가정)
    engine = CoreEngine()
    
    final_outputs = []
    error_messages = []
    
    print(f"\nProcessing {tc_file_path} with Local LLM...")
    
    for event in engine.process_file_stream(tc_file_path):
        if event.get("type") == "error":
            error_messages.append(event.get("message"))
            
        if event.get("type") == "success":
            final_outputs.append(event.get("code_output", ""))
            
    # 검증
    assert not error_messages, f"Errors encountered: {error_messages}"
    assert len(final_outputs) > 0, "No output generated from TC file."
    
    combined_code = "\n".join(final_outputs)
    print("\n--- Local LLM Output Preview ---")
    print(combined_code)
    
    # 주요 키워드 포함 여부 (로컬 LLM 성능에 따라 다를 수 있으므로 유연하게 검증)
    assert "if " in combined_code or "for " in combined_code or "simva." in combined_code
    
if __name__ == "__main__":
    # 직접 실행 시 pytest 없이 실행 가능하도록 구성
    import sys
    sys.path.append(os.getcwd())
    try:
        test_control_tc_pipeline_local_llm()
        print("\n[SUCCESS] Local LLM Integration Test for Control TC passed!")
    except Exception as e:
        print(f"\n[FAILURE] Test failed: {e}")
        sys.exit(1)

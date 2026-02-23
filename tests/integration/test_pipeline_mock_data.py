import pytest
import os
from src.core.engine import CoreEngine

@pytest.mark.skipif(
    os.environ.get("SKIP_LOCAL_LLM_TEST", "false").lower() == "true",
    reason="Requires Local Ollama instance running."
)
def test_mock_tc_data_pipeline():
    """
    data/mock_tc_data.tsv 파일을 대상으로 전체 파이프라인(엔진 ~ 어댑터 통신)이 
    정상 작동하며 Exit 코드가 발생하지 않는지 검증합니다.
    """
    engine = CoreEngine()
    
    # 루트 기준 경로
    tc_file_path = "data/mock_tc_data.tsv"
    
    # 데이터가 없으면 스킵
    if not os.path.exists(tc_file_path):
        pytest.skip(f"mock_tc_data.tsv not found at {tc_file_path}")
        
    final_output = ""
    error_message = None
    
    # 1개의 TC만 처리되도록 break 처리 
    # (LLM 처리가 전체 TC 5개에 걸리면 시간이 너무 오래 걸릴 수 있으므로 1~2개 성공 여부만 봅니다.)
    tc_count = 0
    
    for event in engine.process_file_stream(tc_file_path):
        if event.get("type") == "error":
            error_message = event.get("message")
            break
            
        if event.get("type") == "success":
            final_output = event.get("code_output", "")
            tc_count += 1
            if tc_count >= 1: # 1개 TC 변환 검증 성공 시 종료
                break
                
    assert error_message is None, f"Pipeline Error Encountered: {error_message}"
    assert "simva.set_signal" in final_output or "simva.check_signal" in final_output or "simva.get_signal" in final_output or "Wait" in final_output or "FIXME" in final_output, "Adapter output structure invalid."

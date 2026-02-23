import pytest
import os
import json
import logging
from src.core.engine import CoreEngine
from src.core.config_loader import get_config
from src.core.llm_provider import LocalCPUProvider

# 이 테스트는 Ollama가 로컬에 실행 중이어야 통과합니다.
# CI 환경 등에서 Ollama가 없다면 스킵하도록 마커 추가
@pytest.mark.skipif(
    os.environ.get("SKIP_LOCAL_LLM_TEST", "false").lower() == "true",
    reason="Requires Local Ollama instance running."
)
def test_full_pipeline_with_local_llm(tmp_path, capfd):
    """
    Parser -> RAG(ChromaDB) -> LLM(Ollama) -> Adapter(subprocess)
    전체 파이프라인이 정상적으로 동작하는지 End-to-End 테스트합니다.
    """
    config = get_config()
    
    # 임시 Test Case 파일 생성
    test_tc_content = "T/Case ID\t검증 목적\t시험 전 조건\t시험 방법\t판정 조건\n"
    test_tc_content += "TC_E2E_01\t통합 검증\t\t1. 엑셀 페달을 10% 밟는다.\t정상 작동\n"
    tc_file_path = tmp_path / "test_e2e.tsv"
    tc_file_path.write_text(test_tc_content, encoding='utf-8')
    
    engine = CoreEngine()
    
    # 실행 및 결과 수집
    final_output = ""
    for event in engine.process_file_stream(str(tc_file_path)):
        if event.get("type") == "success":
            final_output = event.get("code_output", "")
    print(f"\n[DEBUG] Pipeline Final Output:\n{final_output}")
    
    # 번역된 타겟 코드가 확인되었는지 확인
    assert "simva.set_signal" in final_output or "simva.check_signal" in final_output or "simva.get_signal" in final_output or "FIXME" in final_output, "Adapter did not output expected SIMVA code."
    
    # 엑셀 페달 10% 밟기는 "VehicleSpeed, 10" 근처로 번역될 확률이 높음.
    # 단, 로컬 LLM의 비결정성 때문에 매우 엄격한 텍스트 매칭보다는 핵심 키워드로 검증합니다.
    assert "VehicleSpeed" in final_output or "UNKNOWN" in final_output, "Failed to map to VehicleSpeed or gracefully degrade to UNKNOWN."

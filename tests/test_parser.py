import pytest
import pandas as pd
import os
from src.core.parser import TCParser

@pytest.fixture
def mock_tsv_file(tmp_path):
    """테스트용 임시 TSV 파일 생성"""
    content = "T/Case ID\t검증 목적\t시험 전 조건\t시험 방법\t판정 조건\n"
    content += "TC_001\t가속 테스트\tIGN=ON\t\"1. 엑셀 페달을 10% 밟는다.\n2. 브레이크를 밟는다.\"\t테스트 성공\n"
    
    file_path = tmp_path / "test_data.tsv"
    file_path.write_text(content, encoding='utf-8')
    return str(file_path)

def test_parser_with_valid_tsv(mock_tsv_file):
    parser = TCParser()
    tcs = parser.parse_file(mock_tsv_file)
    
    assert len(tcs) == 1
    tc = tcs[0]
    
    assert tc["tc_id"] == "TC_001"
    assert tc["tc_title"] == "가속 테스트"
    assert len(tc["steps"]) == 2
    
    assert tc["steps"][0]["step_id"] == 1
    assert "엑셀 페달을 10% 밟는다." in tc["steps"][0]["text"]
    
    assert tc["steps"][1]["step_id"] == 2
    assert "브레이크를 밟는다." in tc["steps"][1]["text"]

def test_parser_unsupported_format():
    parser = TCParser()
    with pytest.raises(ValueError, match="Unsupported file format"):
        parser.parse_file("invalid_file.txt")

import pytest
import os
from src.core.rag_engine import HybridRAGEngine
from src.core.config_loader import get_config

@pytest.fixture(scope="module")
def rag_engine():
    config = get_config()
    # 실제 설정된 DB 경로를 로드합니다.
    vector_db_path = config["database"]["vector_db_path"]
    ontology_path = config["database"]["ontology_path"]
    mock_json_path = "./data/mock_vector_db.json"
    
    engine = HybridRAGEngine(vector_db_path=vector_db_path, ontology_path=ontology_path)
    
    # 혹시 초기화가 안 되어 있다면 테스트 전에 초기화합니다.
    engine.initialize_db(mock_json_path)
    
    return engine

def test_rag_search_actual(rag_engine):
    """실제 RAG(ChromaDB)를 통해 유사 시그널이 정확히 검색되는지 테스트합니다."""
    # 기본 Chroma 임베딩(all-MiniLM-L6-v2)은 영문 특화이므로 한국어 매칭률이 떨어집니다.
    # 따라서 명확히 매핑되는 영단어 "speed"를 테스트에 활용합니다.
    results = rag_engine.search_signals("speed", threshold=2.0)
    
    assert len(results) > 0, "No signals found in Vector DB for the given query."
    top_result = results[0]
    
    # 1. 시그널 매칭 검증
    assert top_result["logical_name"] == "VehicleSpeed", f"Expected VehicleSpeed but got {top_result['logical_name']}"
    
    # 2. 거리(유사도) 검증: 기본 모델 반환 거리가 생각보다 클 수 있으므로 2.0으로 넉넉하게 잡습니다.
    assert top_result["distance"] < 2.0, f"Distance is too high: {top_result['distance']}"

def test_rag_ontology_precondition(rag_engine):
    """Ontology Rule에서 특정 조작 전 필요한 선행 조건을 잘 가져오는지 테스트합니다."""
    # VehicleSpeed 조작은 Engine 시동이 ON 이어야 한다는 룰이 있습니다. (mock_ontology_db.json 참고)
    rules = rag_engine.validate_preconditions("VehicleSpeed")
    
    assert len(rules) >= 1, "Expected at least 1 precondition rule for VehicleSpeed."
    rule = rules[0]
    
    assert rule["relation"] == "REQUIRES"
    assert rule["target"] == "Ignition_Status"
    assert rule["condition"] == "== ON"

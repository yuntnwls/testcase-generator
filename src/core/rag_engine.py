import json
import os
import chromadb
from pathlib import Path

class HybridRAGEngine:
    """
    Vector DB (ChromaDB) 기반 시그널 의미 검색과
    JSON/Graph 기반 Ontology (제약 조건) 검증을 결합한 하이브리드 RAG 엔진
    """
    def __init__(self, vector_db_path: str, ontology_path: str):
        self.vector_db_path = vector_db_path
        self.ontology_path = ontology_path
        
        # 1. Initialize ChromaDB Client
        # PersistentClient를 사용하여 디스크에 저장
        Path(self.vector_db_path).mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=self.vector_db_path)
        
        # 기본 임베딩 모델(all-MiniLM-L6-v2) 자동 다운로드 및 사용
        self.collection = self.chroma_client.get_or_create_collection(name="signals")
        
        # 2. Load Ontology Rules
        self.ontology_rules = self._load_ontology()
        
    def _load_ontology(self) -> list:
        if not os.path.exists(self.ontology_path):
            return []
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("relationships", [])

    def initialize_db(self, mock_json_path: str):
        """
        초기 1회만 호출하여 mock_vector_db.json 데이터를 ChromaDB에 주입합니다.
        (테스트 및 셋업용)
        """
        if self.collection.count() > 0:
            return # 이미 데이터가 있으면 건너뜀
            
        if not os.path.exists(mock_json_path):
            raise FileNotFoundError(f"Mock Vector DB source not found: {mock_json_path}")
            
        with open(mock_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        ids = []
        documents = []
        metadatas = []
        
        for item in data:
            ids.append(item["id"])
            documents.append(item["text"])  # 이 텍스트가 임베딩 변환의 기준이 됩니다.
            
            # ChromaDB metadata는 중첩 딕셔너리를 지원하지 않으므로 플래튼(Flatten) 하거나 JSON String으로 저장
            flat_meta = {
                "logical_name": item["metadata"]["logical_name"],
                "data_type": item["metadata"].get("data_type", ""),
                "unit": item["metadata"].get("unit", ""),
                "description": item["metadata"].get("description", ""),
                "allowed_values": ",".join(item["metadata"].get("allowed_values", []))
            }
            metadatas.append(flat_meta)
            
        # 벡터 변환 및 저장 (SentenceTransformer 자동 호출)
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"ChromaDB Initialized with {len(ids)} signals.")

    def search_signals(self, query_text: str, top_k: int = 1, threshold: float = 1.0) -> list:
        """
        입력된 사용자 자연어 문장에서 가장 유사한 시그널을 Vector DB에서 찾습니다.
        (ChromaDB의 기본 distance는 작은 값이 더 유사함을 의미합니다.)
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k
        )
        
        matches = []
        # results["distances"][0] 에 각 결과의 거리 점수가 들어있음 (보통 L2 distance)
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            # 임시 스레스홀드 로직: 거리가 너무 멀면(예: 1.5 이상) 무시
            if distance > threshold:
                continue
                
            matches.append({
                "logical_name": results["metadatas"][0][i]["logical_name"],
                "data_type": results["metadatas"][0][i]["data_type"],
                "description": results["metadatas"][0][i]["description"],
                "allowed_values": results["metadatas"][0][i]["allowed_values"],
                "distance": distance
            })
            
        return matches

    def validate_preconditions(self, target_signal: str, step_action: str = "SET") -> list:
        """
        Ontology (mock_ontology_db.json)를 뒤져 해당 시그널 조작 전 필요한 선행 조건(Pre-condition) 룰을 반환합니다.
        """
        applicable_rules = []
        for rule in self.ontology_rules:
            if rule.get("source") == target_signal and rule.get("relation") == "REQUIRES":
                # 예: VehicleSpeed 조작은 Ignition_Status=ON을 요구함.
                applicable_rules.append(rule)
        return applicable_rules

if __name__ == "__main__":
    # 간단한 디버그용 실행 (단위 테스트)
    import sys
    engine = HybridRAGEngine("./data/vector_db", "./data/mock_ontology_db.json")
    engine.initialize_db("./data/mock_vector_db.json")
    
    res = engine.search_signals("시속 60으로 달린다")
    print(f"Search Result: {res}")
    
    rules = engine.validate_preconditions("VehicleSpeed")
    print(f"Rules for VehicleSpeed: {rules}")

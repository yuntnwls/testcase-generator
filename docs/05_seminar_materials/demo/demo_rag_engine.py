import os
import json
from src.core.rag_engine import HybridRAGEngine

class DemoHybridRAGEngine(HybridRAGEngine):
    """
    데모 전용 HybridRAGEngine.
    코어 엔진(rag_engine.py)의 기존 포맷(방안 A) 호환성을 유지하기 위해,
    방안 C (Action Vector DB + Signal Ontology Graph) 시연에 필요한
    커스텀 파싱 및 로드 로직만 데모 스크립트 레벨에서 오버라이딩합니다.
    """
    def _load_ontology(self) -> dict:
        if not os.path.exists(self.ontology_path):
            return {"nodes": [], "edges": []}
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data

    def initialize_db(self, mock_json_path: str):
        if self.collection.count() > 0:
            return
            
        if not os.path.exists(mock_json_path):
            raise FileNotFoundError(f"Mock Vector DB source not found: {mock_json_path}")
            
        with open(mock_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 방안 C 포맷 지원: 루트가 리스트면 그대로, 딕셔너리이고 "records"가 있으면 그걸 사용
        records = data.get("records", data) if isinstance(data, dict) else data

        ids = []
        documents = []
        metadatas = []
        
        for item in records:
            ids.append(item["id"])
            doc_text = item.get("vector_source", item.get("text", ""))
            documents.append(doc_text)
            
            flat_meta = {}
            for k, v in item.items():
                if k not in ["id", "vector_source"]:
                    if isinstance(v, (list, dict)):
                        flat_meta[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        flat_meta[k] = v
                        
            metadatas.append(flat_meta)
            
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"ChromaDB Initialized with {len(ids)} action templates.")

    def search_signals(self, query_text: str, top_k: int = 1, threshold: float = 1.0) -> list:
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k
        )
        matches = []
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            if distance > threshold:
                continue
                
            match_data = results["metadatas"][0][i].copy() if results["metadatas"] and results["metadatas"][0] else {}
            match_data["id"] = results["ids"][0][i]
            match_data["distance"] = distance
            matches.append(match_data)
        return matches

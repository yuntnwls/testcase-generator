import os
import sys
import time
import tempfile
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가하여 src 모듈 임포트 허용
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config_loader import get_config
from src.core.rag_engine import HybridRAGEngine
from src.core.engine import CoreEngine
from demo_rag_engine import DemoHybridRAGEngine

def print_separator():
    print("\n" + "="*80 + "\n")

def init_demo_environment():
    """데모 전용 임시 DB(Vector DB & Ontology) 경로를 설정하고 RAG 엔진을 초기화합니다."""
    print("⏳ 시스템 엔진 및 데모용 샘플 DB(로컬 환경)를 로드 중입니다...")
    
    demo_dir = Path(__file__).resolve().parent
    data_dir = demo_dir / "data"
    chroma_path = data_dir / ".chroma_demo"
    ontology_path = data_dir / "sample_ontology.json"
    vector_json_path = data_dir / "sample_vector_db.json"
    
    # 1. 데모용 독립 RAG 엔진 초기화 (시각화용)
    rag_engine = DemoHybridRAGEngine(
        vector_db_path=str(chroma_path),
        ontology_path=str(ontology_path)
    )
    rag_engine.initialize_db(str(vector_json_path))
    
    # 2. 실제 코드 생성용 CoreEngine 초기화 
    # (주의: CoreEngine 내부에서도 RAG 인스턴스를 만들지만, 데모 스크립트 특성 상 
    # 검색 과정을 시각적으로 보여주기 위해 독립 RAG 인스턴스(rag_engine)를 메인에 띄워 놓습니다)
    core_engine = CoreEngine()
    
    print("✅ RAG 검색 모듈 & LLM 변환 엔진 연동 완료!")
    return rag_engine, core_engine

def show_rag_search_process(rag_engine, query_text):
    """자연어 문장이 Vector DB와 Ontology를 거치는 2-Step RAG 과정을 시각적으로 보여줍니다."""
    print(f"\n🔍 [1단계] Vector DB 검색 (Action 판별)")
    print(f"입력 문장: '{query_text}'")
    time.sleep(0.5)
    
    # 1. ChromaDB 검색 (Action 템플릿 탐색)
    # 문장 전체를 Vector DB에 던져서 의미상 가장 가까운 Action(제어, 대기, 확인 등)을 찾음
    matches = rag_engine.search_signals(query_text, top_k=1, threshold=1.5)
    
    if not matches:
        print("❌ [RAG] Vector DB에서 매칭되는 Action을 찾지 못했습니다.")
        return False
        
    top_match = matches[0]
    action_id = top_match.get('id', 'Unknown')
    similarity = max(0, int((2.0 - top_match.get('distance', 1.0)) / 2.0 * 100))
    
    print(f"🟢 [Vector DB 매칭 성공] (유사도: {similarity}점) -> '{action_id}' 액션 도출")
    print(f"   ▶ 타겟 API 템플릿: {top_match.get('target_code', 'N/A')}")
    print(f"   ▶ 액션 속성(설명): {top_match.get('context_prefix', '')}")
    
    # 2. Ontology 검색 시뮬레이션 (Signal 탐색)
    print(f"\n🔍 [2단계] Ontology DB 검색 (Signal 및 제약조건 탐색)")
    time.sleep(0.5)
    
    nodes = {node["id"]: node for node in rag_engine.ontology_rules.get("nodes", [])}
    edges = rag_engine.ontology_rules.get("edges", [])
    
    # 더미 Entity Recognition: query_text 에 synonym이 있는지 확인
    target_concept = None
    target_physical = None
    
    for n_id, n_data in nodes.items():
        if n_data.get("node_type") == "concept":
            synonyms = n_data.get("synonyms", [])
            label = n_data.get("label", "")
            match_candidates = synonyms + [label]
            for cand in match_candidates:
                if cand.replace(" ", "") in query_text.replace(" ", ""):
                    target_concept = n_data
                    break
        if target_concept:
            break
            
    if target_concept:
        print(f"🟢 [Ontology 매칭 성공] 컨셉 노드 '{target_concept['label']}' 발견")
        # Physical 노드 치환
        for edge in edges:
            if edge.get("target") == target_concept["id"] and edge.get("relation") == "represents":
                source_id = edge.get("source")
                if source_id in nodes:
                    target_physical = nodes[source_id]
                    ecu = target_physical.get("ecu", "Unknown")
                    sig = target_physical.get("signal_id", "Unknown")
                    print(f"   ✅ [Graph Hop] 구현 물리 시그널 매핑: signals.{ecu}.{sig}")
                    break
                    
        # 3. 연결된 제약조건(Constraint) 엣지 탐색
        rules = []
        for edge in edges:
            if edge.get("source") == target_concept["id"] and edge.get("relation") == "constrained_by":
                constraint_id = edge.get("target")
                if constraint_id in nodes:
                    rules.append(nodes[constraint_id].get("description", "제약 조건 발견"))
                    
        if rules:
            print(f"   🔵 [Graph Hop] 제약조건(Constraint) 노출:")
            for rule in rules:
                print(f"      ▶ {rule}")
                
    else:
        print(f"⚪ [Ontology] 문장에서 매칭되는 시그널을 찾지 못했습니다.")
        
    print("\n   (LLM에게 조립된 템플릿 + 제약조건 + 시그널 Context를 전달하여 코드를 생성합니다.)")
    time.sleep(0.5)
    return True

def run_llm_code_generation(core_engine, tc_text):
    """실제 LLM/파싱 엔진을 통해 최종 Python 코드를 합성합니다."""
    print(f"\n⚙️ [2단계] 코드 합성 (Direct Synthesis)")
    time.sleep(0.5)
    
    tc_content = "T/Case ID\t검증 목적\t시험 전 조건\t시험 방법\t판정 조건\n"
    tc_content += f"TC_DEMO_01\t라이브 데모\t\t1. {tc_text}\t\n"
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.tsv', encoding='utf-8') as tmp:
        tmp.write(tc_content)
        tmp_path = tmp.name

    final_output = ""
    error_msg = ""
    
    try:
        # 엔진 스트림 수신 대기 (진행 로고 출력)
        sys.stdout.write("🧠 [LLM ⇄ RAG] 코드 생성 중")
        sys.stdout.flush()
        
        for event in core_engine.process_file_stream(tmp_path):
            if event.get("type") == "success":
                final_output = event.get("code_output", "")
            elif event.get("type") == "error":
                error_msg = event.get("message", "Unknown Error")
            # 진행 중 상황을 표현하기 위해 마침표 찍기
            sys.stdout.write(".")
            sys.stdout.flush()
            
    except Exception as e:
        error_msg = str(e)
    finally:
        os.unlink(tmp_path) 
        print(" [조립 완료!]")

    if final_output:
        print("\n✨ [최종 생성된 테스트 스크립트 코드]")
        print("-" * 65)
        print(final_output.strip())
        print("-" * 65)
        return final_output
    else:
        print("\n❌ [생성 실패]")
        print(f"문제를 LLM이 해결하지 못했습니다: {error_msg}")
        return None

def main():
    print_separator()
    print("🚀 [Live Demo] Contextual RAG 기반 TC 자동화 파이프라인 🚀")
    print("-> 자연어가 어떻게 시그널로 매핑되고(RAG), 다시 코드로 합성(LLM)되는지 관찰합니다.")
    print_separator()
    
    rag_engine, core_engine = init_demo_environment()
    
    # 데모 앱 레벨 캐싱
    cache = {}
    
    while True:
        print_separator()
        tc_input = input("\n자연어 테스트 스텝 입력 (종료: q) \n(ex: '좌측 전조등을 켜라') > ")
        
        if not tc_input or tc_input.lower() == 'q':
            break
            
        if tc_input in cache:
            print(f"\n⚡ [Pattern Cache HIT!] -> LLM 연산 스킵 (0.001초 반환)")
            print("-" * 65)
            print(cache[tc_input].strip())
            print("-" * 65)
            continue
            
        # 1. RAG 시각화
        success = show_rag_search_process(rag_engine, tc_input)
        
        # 2. 코드 생성 실행
        if success:
            code = run_llm_code_generation(core_engine, tc_input)
            if code:
                cache[tc_input] = code

if __name__ == "__main__":
    main()

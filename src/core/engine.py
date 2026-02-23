import uuid
import json
import subprocess
import structlog
from typing import Union, List
from pydantic import TypeAdapter, ValidationError

from src.core.config_loader import get_config
from src.core.llm_provider import LLMFactory
from src.core.rag_engine import HybridRAGEngine
from src.core.prompt_builder import PromptBuilder
from src.core.parser import TCParser
from src.core.models import TestCaseIR, AnyIR, UnknownIR

# 기본 로거 설정 (실제 환경에서는 JSON 포맷터 등 추가 설정 필요)
structlog.configure()
logger = structlog.get_logger()

class CoreEngine:
    def __init__(self, llm_provider=None, rag_engine=None):
        self.config = get_config()
        self.llm = llm_provider or LLMFactory.create_provider(self.config["llm"])
        self.rag = rag_engine or HybridRAGEngine(
            vector_db_path=self.config["database"]["vector_db_path"],
            ontology_path=self.config["database"]["ontology_path"]
        )
        self.parser = TCParser()
        self.max_retries = self.config["llm"].get("max_retries", 3)
        self.ir_adapter = TypeAdapter(AnyIR)

    def process_file_stream(self, file_path: str, selected_tc_ids: list = None):
        """
        주어진 TC 파일을 읽어 전체 파이프라인 수행 후 진행 상황을 Generator로 Yield 합니다.
        selected_tc_ids가 제공되면 해당 ID를 가진 TC만 처리합니다.
        """
        tc_list = self.parser.parse_file(file_path)
        
        # TC 필터링 로직
        if selected_tc_ids:
            tc_list = [tc for tc in tc_list if tc["tc_id"] in selected_tc_ids]
            
        total_tcs = len(tc_list)
        all_tc_irs = [] # 통합 처리를 위한 IR 리스트
        
        for tc_idx, tc_data in enumerate(tc_list, 1):
            trace_id = str(uuid.uuid4())
            t_logger = logger.bind(trace_id=trace_id, tc_id=tc_data["tc_id"])
            t_logger.info("Starting TC conversion", title=tc_data["tc_title"], tc_index=tc_idx, total_tcs=total_tcs)
            
            yield {
                "type": "info", 
                "trace_id": trace_id, 
                "tc_id": tc_data["tc_id"],
                "tc_title": tc_data["tc_title"],
                "tc_index": tc_idx,
                "total_tcs": total_tcs,
                "message": f"[{tc_idx}/{total_tcs}] LLM Processing: {tc_data['tc_title']}"
            }
            
            final_irs = []
            total_steps = len(tc_data["steps"])
            
            for idx, step in enumerate(tc_data["steps"]):
                t_logger.info(f"Processing step {step['step_id']}: {step['text']}")
                ir_obj_list = self._process_step_with_retry(step, t_logger)
                final_irs.extend(ir_obj_list)
                
                # UI 진행 상황 Yield
                yield {
                    "type": "progress", 
                    "trace_id": trace_id, 
                    "tc_id": tc_data["tc_id"],
                    "tc_title": tc_data["tc_title"],
                    "tc_index": tc_idx,
                    "total_tcs": total_tcs,
                    "current": idx + 1, 
                    "total": total_steps, 
                    "message": f"Parsed step {step['step_id']}: {step['text']}"
                }
                
            # 전체 IR을 묶어서 TestCaseIR 모델로 검증 및 생성
            tc_ir_obj = TestCaseIR(
                tc_id=tc_data["tc_id"],
                tc_title=tc_data["tc_title"],
                steps=final_irs
            )
            all_tc_irs.append(tc_ir_obj)

        if all_tc_irs:
            # Note: For batch processing, the trace_id, tc_id, tc_title, tc_index, total_tcs
            # in the yielded messages below will refer to the *batch operation itself*,
            # not individual TCs within the batch, unless the adapter explicitly provides
            # per-TC information in its stderr output.
            batch_trace_id = str(uuid.uuid4()) # Generate a new trace_id for the batch operation
            batch_logger = logger.bind(trace_id=batch_trace_id, tc_id="BATCH_PROCESS")
            batch_logger.info("All LLM conversions finished. Sending batch to Adapter...")
            yield {
                "type": "info", 
                "trace_id": batch_trace_id,
                "message": f"Consolidating {len(all_tc_irs)} TCs and invoking Target Adapter...",
                "total_tcs": total_tcs # This total_tcs refers to the original count of TCs
            }
            # Batch 처리 (List[TestCaseIR])
            yield from self._send_to_adapter_stream(all_tc_irs, batch_trace_id, batch_logger, 1, 1) # tc_index, total_tcs are for the batch itself

    def process_file(self, file_path: str, selected_tc_ids: list = None):
        """기존 백그라운드용 동기 실행 래퍼"""
        for _ in self.process_file_stream(file_path, selected_tc_ids):
            pass

    def _process_step_with_retry(self, step: dict, t_logger) -> AnyIR:
        """
        단일 스텝에 대해 RAG -> LLM 조립 후, Pydantic 에러 시 Self-Correction Loop 수행
        """
        user_text = step["text"]
        step_id = step["step_id"]
        
        # 1. RAG Search (top_k 확장: 복합 문장에서 여러 시그널을 커버하기 위해)
        top_k = self.config["database"].get("top_k", 5)
        rag_signals = self.rag.search_signals(user_text, top_k=top_k, threshold=self.config["database"]["similarity_threshold"])
        
        # 검색된 모든 시그널에 대해 Ontology 제약 조건을 통합 수집, 중복 제거
        rag_rules = []
        seen_rules = set()
        for sig in rag_signals:
            for rule in self.rag.validate_preconditions(sig["logical_name"]):
                rule_key = (rule.get('source'), rule.get('relation'), rule.get('target'))
                if rule_key not in seen_rules:
                    seen_rules.add(rule_key)
                    rag_rules.append(rule)
            
        system_prompt = PromptBuilder.get_system_prompt()
        base_prompt = PromptBuilder.build_prompt(user_text, rag_signals, rag_rules)
        
        current_prompt = base_prompt
        last_error = ""

        # Retry Loop (Topic 1)
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    t_logger.warning("Retrying LLM generation", attempt=attempt, reason=last_error)
                    
                # LLM 호출
                raw_json_str = self.llm.generate(current_prompt, system_prompt)
                
                # 순수 JSON 추출 (마크다운 백틱 등 제거)
                clean_json_str = self._clean_llm_json(raw_json_str)
                
                # Pydantic Validation
                parsed_json = json.loads(clean_json_str)
                
                # 정규화: 항상 리스트 형태로 처리 (하나의 스텝에서 여러 액션이 나올 수 있음)
                if isinstance(parsed_json, dict):
                    parsed_json = [parsed_json]
                    
                for idx_item, item in enumerate(parsed_json):
                    if isinstance(item, dict):
                        item["step_id"] = step_id
                        # 여러 IR 객체가 생성될 경우 구분을 위해 약간의 텍스트 변형을 줄 수도 있지만
                        # 여기서는 원본 텍스트를 그대로 유지
                        item["original_text"] = user_text
                
                # 강제 검증 수행 (리스트 타입으로 검증)
                # self.ir_adapter를 List[AnyIR]로 생성했다고 가정하거나 여기서 직접 검증할 수 있음
                list_adapter = TypeAdapter(list[AnyIR])
                valid_ir_list = list_adapter.validate_python(parsed_json)
                return valid_ir_list
                
            except ValidationError as ve:
                last_error = str(ve)
                current_prompt = base_prompt + f"\n\n[SYSTEM ERROR IN PREVIOUS ATTEMPT]\nPydantic Validation Failed:\n{last_error}\nPlease fix the JSON structure, ensure 'value' fields are primitives (not dicts), and try again."
            except Exception as e:
                last_error = str(e)
                current_prompt = base_prompt + f"\n\n[SYSTEM ERROR IN PREVIOUS ATTEMPT]\nError: {last_error}\nPlease fix the format and try again."

        # Retry 초과 시 Graceful Degradation (Fallback to UNKNOWN)
        t_logger.error("Max retries exceeded. Falling back to UNKNOWN IR.", text=user_text, error=last_error)
        return [UnknownIR(
            step_id=step_id,
            original_text=user_text,
            reason=f"Failed after {self.max_retries} retries. Last error: {last_error}"
        )]

    def _clean_llm_json(self, text: str) -> str:
        """ 마크다운 코드블럭(```json) 등을 제거하고 순수 JSON 텍스트만 추출합니다. """
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _send_to_adapter_stream(self, tc_ir: Union[TestCaseIR, List[TestCaseIR]], trace_id: str, t_logger, tc_index: int = 1, total_tcs: int = 1):
        """
        Topic 2. 서브프로세스 어댑터로 IR 전달 (실시간 stderr 스트리밍 지원)
        """
        # Batch 여부에 따라 식별자 설정
        if isinstance(tc_ir, list):
            tc_id = "BATCH_RESULT"
            tc_title = f"Combined Script ({len(tc_ir)} TCs)"
        else:
            tc_id = tc_ir.tc_id
            tc_title = tc_ir.tc_title
            
        adapter_cfg = self.config["target"]["adapters"][self.config["target"]["active_adapter"]]
        exec_path = adapter_cfg["executable_path"]
        python_bin = adapter_cfg.get("python_bin", "python")
        
        import sys
        
        # 유연한 직렬화
        multi_ir_adapter = TypeAdapter(Union[TestCaseIR, List[TestCaseIR]])
        json_payload = multi_ir_adapter.dump_json(tc_ir).decode('utf-8')
        
        # Windows 환경에서 Popen의 text=True 시 발생할 수 있는 cp949 인코딩 오류 방지
        # 가상환경 안전성을 위해 python_bin이 단순 'python'일 경우 현재 실행 중인 sys.executable을 사용
        actual_python_bin = sys.executable if python_bin == "python" else python_bin
        
        # 하위 서브프로세스에서 PYTHONPATH를 상속받아 `src` 모듈을 인식하도록 강제
        import os
        env = os.environ.copy()
        if "PYTHONPATH" not in env:
             env["PYTHONPATH"] = os.getcwd()
             
        try:
            process = subprocess.Popen(
                [actual_python_bin, exec_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, # 문자열 모드
                encoding='utf-8', # 파이프 통신은 반드시 utf-8로 강제
                env=env
            )
            
            t_logger.info("Executing Adapter subprocess", target=self.config["target"]["active_adapter"], exec_path=exec_path)
            
            # 파이썬에서 가장 안전하게 stdout과 stderr를 동시에 처리하는 방법.
            # UI 실시간 업데이트를 위해 한정된 데모 환경에서는 `communicate`로
            # 데이터를 밀어넣고 완료된 후 에러/로그를 한 번에 yield 처리하도록 수정합니다.
            # (Pipe blocking 이슈 원천 차단)
            stdout_data, stderr_data = process.communicate(input=json_payload)
            
            if stderr_data:
                for line in stderr_data.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.startswith("[PROGRESS]"):
                        t_logger.info("Adapter Progress", detail=line)
                        try:
                            parts = line.split(" ")[1].split("/")
                            yield {
                                "type": "adapter_progress", 
                                "current": int(parts[0]), 
                                "total": int(parts[1]), 
                                "trace_id": trace_id,
                                "tc_id": tc_id,
                                "tc_title": tc_title,
                                "tc_index": tc_index,
                                "total_tcs": total_tcs
                            }
                        except:
                            pass
                    elif line.startswith("[ERROR]"):
                        t_logger.error("Adapter Error", detail=line)
                        yield {
                            "type": "error", 
                            "message": line, 
                            "trace_id": trace_id,
                            "tc_id": tc_id,
                            "tc_title": tc_title,
                            "tc_index": tc_index,
                            "total_tcs": total_tcs
                        }
                    else:
                        t_logger.debug("Adapter Log", detail=line)
            
            if process.returncode == 0:
                t_logger.info("Adapter translation completed successfully.")
                yield {
                    "type": "success", 
                    "trace_id": trace_id, 
                    "tc_id": tc_id,
                    "tc_title": tc_title,
                    "code_output": stdout_data,
                    "tc_index": tc_index,
                    "total_tcs": total_tcs
                }
            else:
                t_logger.error("Adapter failed with non-zero exit code.", code=process.returncode)
                error_context = stderr_data if stderr_data else "No stderr output"
                yield {
                    "type": "error", 
                    "trace_id": trace_id, 
                    "tc_id": tc_id,
                    "tc_title": tc_title,
                    "message": f"Adapter failed with exit code {process.returncode}:\n{error_context}",
                    "tc_index": tc_index,
                    "total_tcs": total_tcs
                }
                
        except Exception as e:
            t_logger.error("Failed to execute adapter subprocess", error=str(e))
            yield {
                "type": "error", 
                "trace_id": trace_id, 
                "message": str(e),
                "tc_index": tc_index,
                "total_tcs": total_tcs
            }


    def _send_to_adapter(self, tc_ir: TestCaseIR, trace_id: str, t_logger):
        for _ in self._send_to_adapter_stream(tc_ir, trace_id, t_logger):
            pass

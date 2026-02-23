import sys
import json
import traceback
from abc import ABC, abstractmethod
from pydantic import TypeAdapter, ValidationError

# Engine 파트의 모델을 직접 import하여 타입 안전성을 보장받습니다.
# 만약 완전히 분리된 저장소나 환경이라면 Pydantic 모델을 공통 라이브러리(SDK)로 추출하는 것이 좋습니다.
from src.core.models import TestCaseIR, AnyIR, IRType

class BaseAdapter(ABC):
    """
    Core Engine에서 넘겨준 IR JSON (stdin)을 파싱하여
    순수한 타겟 스크립트 텍스트 (stdout)로 변환해주는 추상 클래스 프레임워크.
    """
    def __init__(self):
        self.parsed_tc = None
        self.ir_adapter = TypeAdapter(TestCaseIR)

    def log_progress(self, current: int, total: int):
        """UI 진행률 업데이트용 표준 로그 출력 (stderr)"""
        sys.stderr.write(f"[PROGRESS] {current}/{total}\n")
        sys.stderr.flush()

    def log_info(self, message: str):
        sys.stderr.write(f"[INFO] {message}\n")
        sys.stderr.flush()

    def log_error(self, message: str):
        sys.stderr.write(f"[ERROR] {message}\n")
        sys.stderr.flush()

    @abstractmethod
    def generate_header(self) -> str:
        """스크립트 최상단 공통 import 및 전역 초기화 코드 생성"""
        pass

    @abstractmethod
    def translate_test_case_header(self, tc_id: str, tc_title: str) -> str:
        """개별 TC의 함수 정의(def) 시작 부분 생성"""
        pass

    @abstractmethod
    def translate_action(self, ir_step: 'SetIR', indent: int) -> str:
        """SET 타입의 IR을 타겟 코드로 변환"""
        pass

    @abstractmethod
    def translate_check(self, ir_step: 'CheckIR', indent: int) -> str:
        """CHECK 타입의 IR을 타겟 코드로 변환"""
        pass
        
    @abstractmethod
    def translate_wait(self, ir_step: 'WaitIR', indent: int) -> str:
        pass
        
    @abstractmethod
    def translate_macro_call(self, ir_step: 'MacroCallIR', indent: int) -> str:
        pass

    @abstractmethod
    def translate_macro_def(self, ir_step: 'MacroDefinitionIR', indent: int) -> str:
        """사용자 정의 함수 정의 IR 변환"""
        pass

    @abstractmethod
    def translate_condition(self, ir_step: 'ConditionIR', indent: int) -> str:
        """조건문(if-else) IR 변환"""
        pass

    @abstractmethod
    def translate_loop(self, ir_step: 'LoopIR', indent: int) -> str:
        """반복문(for/while) IR 변환"""
        pass

    @abstractmethod
    def translate_complex_logic(self, ir_step: 'ComplexLogicIR', indent: int) -> str:
        """복잡한 로직(Smart Adapter LLM 처리) 변환"""
        pass

    @abstractmethod
    def generate_footer(self) -> str:
        """스크립트 최상단 마무리 코드 생성 (선택 사항)"""
        pass

    def get_indent(self, level: int) -> str:
        """들여쓰기 문자열 생성 (기본: 4 공백)"""
        return "    " * level

    def translate_step(self, step: AnyIR, indent: int = 1) -> str:
        """개별 IR 단계를 코드로 변환 (재귀 호출 지원)"""
        indent_str = self.get_indent(indent)
        code_lines = []
        
        # 원본 자연어를 주석으로 추가
        code_lines.append(f"{indent_str}# Step {step.step_id}: {step.original_text}")
        
        try:
            translated_code = ""
            if step.type == IRType.SET:
                translated_code = self.translate_action(step, indent)
            elif step.type == IRType.CHECK:
                translated_code = self.translate_check(step, indent)
            elif step.type == IRType.WAIT:
                translated_code = self.translate_wait(step, indent)
            elif step.type == IRType.MACRO_CALL:
                translated_code = self.translate_macro_call(step, indent)
            elif step.type == IRType.MACRO_DEF:
                translated_code = self.translate_macro_def(step, indent)
            elif step.type == IRType.CONDITION:
                translated_code = self.translate_condition(step, indent)
            elif step.type == IRType.LOOP:
                translated_code = self.translate_loop(step, indent)
            elif step.type == IRType.COMPLEX_LOGIC:
                translated_code = self.translate_complex_logic(step, indent)
            elif step.type == IRType.UNKNOWN:
                translated_code = f"{indent_str}# FIXME (UNKNOWN IR): {step.original_text} | Reason: {step.reason}"
            else:
                translated_code = f"{indent_str}# [WARNING] Unsupported IR Type: {step.type}"
            
            if translated_code:
                code_lines.append(translated_code)
                
        except Exception as eval_err:
            error_msg = f"{indent_str}# [ERROR TRANSLATING STEP {step.step_id}]: {str(eval_err)}"
            code_lines.append(error_msg)
            self.log_error(f"Step {step.step_id} translation failed: {str(eval_err)}")
            
        return "\n".join(code_lines) + "\n"

    def run(self):
        """어댑터의 메인 실행 루프 (변경 금지 템플릿 메서드)"""
        import io
        from typing import List, Union
        from pydantic import TypeAdapter
        
        # 유연한 입력을 위해 Union 타입 어댑터 생성
        multi_ir_adapter = TypeAdapter(Union[TestCaseIR, List[TestCaseIR]])
        
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
        
        try:
            input_text = sys.stdin.read()
            if not input_text.strip():
                 self.log_info("Received empty stdin payload. Exiting.")
                 return
                 
            parsed_data = multi_ir_adapter.validate_json(input_text)
            
            # 리스트 여부 확인하여 통합 처리
            tc_list = parsed_data if isinstance(parsed_data, list) else [parsed_data]
            
            self.log_info(f"Starting Adapter Translation for {len(tc_list)} TCs")

            # 1. 공통 Header 출력 (맨 처음에 단 한 번)
            print(self.generate_header())

            for tc_idx, tc_obj in enumerate(tc_list):
                self.parsed_tc = tc_obj # 하위 메서드에서 참조할 수 있도록 설정
                
                # 2. TC 시작 정의 (함수명 등)
                print(self.translate_test_case_header(tc_obj.tc_id, tc_obj.tc_title))
                
                steps = tc_obj.steps
                total_steps = len(steps)
                
                # 3. 본문 변환 (들여쓰기 1단계 기본 적용)
                for s_idx, step in enumerate(steps):
                    print(self.translate_step(step, indent=1))
                    if len(tc_list) == 1:
                        self.log_progress(s_idx + 1, total_steps)
                
                if len(tc_list) > 1:
                    self.log_progress(tc_idx + 1, len(tc_list))
                
                print("") # TC 간 공백

            # 4. Footer 출력
            print(self.generate_footer())
            self.log_info("Translation sequence completed.")
            
        except ValidationError as ve:
             self.log_error("Invalid JSON Schema payload received from Core Engine.")
             sys.stderr.write(traceback.format_exc())
             sys.exit(1)
        except Exception as e:
             self.log_error(f"CRITICAL ADAPTER ERROR: {str(e)}")
             sys.stderr.write(traceback.format_exc())
             sys.exit(1)

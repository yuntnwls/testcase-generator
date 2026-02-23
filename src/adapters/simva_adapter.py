from src.adapters.base_adapter import BaseAdapter

class SimvaAdapter(BaseAdapter):
    """
    SIMVA 테스트 프레임워크 전용 파이썬 스크립트 생성기입니다.
    실제 testcase.py 패턴을 반영하여 복잡한 제어 로직과 다중 모듈 구조를 지원합니다.
    """
    
    def generate_header(self) -> str:
        # 기본 임포트 섹션 (logging 제외)
        header_lines = [
            "from simvabasic import simva",
            "from references import signals, profiles",
            "import testcases.config as config",
            "import testcases.functions.precondition as precondition",
            "import testcases.functions.cleanup as cleanup",
            "import testcases.functions.method as method",
            "import testcases.functions.acquisition as acquisition",
            "import testcases.functions.outputcheck as check",
            "import testcases.quantity as q",
            ""
        ]
        return "\n".join(header_lines)

    def translate_test_case_header(self, tc_id: str, tc_title: str) -> str:
        import re
        # TC ID와 타이틀을 조합하여 메인 함수명 생성
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', f"{tc_id}_{tc_title}")
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        
        return f"def {clean_name}():"

    def _format_value(self, val) -> str:
        """가급적 q. 상수로 매핑하거나 문자열 쿼트 처리"""
        if isinstance(val, str):
            # 이미 q. 접두사가 있거나 signals. 가 있으면 그대로 사용
            if val.startswith("q.") or val.startswith("signals."):
                return val
            # 특정 키워드는 q. 상수로 매핑 (대문자로 시작하고 언더바가 있거나, 전체가 대문자인 경우 등)
            import re
            if re.match(r'^[A-Z][a-zA-Z0-9_]*$', val) and ("_" in val or val.isupper()):
                return f"q.{val}"
            # ON, OFF 등 특수 키워드
            if val in ["ON", "OFF", "TRUNK", "LIFTGATE"]:
                return f"q.{val}"
            return f"'{val}'"
        return str(val)

    def _format_signal(self, sig: str) -> str:
        """시그널 명에 적절한 접두사 보정 및 공백/특수문자 정제"""
        if sig.startswith("signals."):
            return sig
        # 공백, 하이픈 등 시그널 명에 사용 불가한 문자를 언더바로 치환
        import re
        sig = re.sub(r'[\s\-]+', '_', sig).strip('_')
        # 기본적으로 signals.BDC. 접두사가 많이 사용됨
        return f"signals.BDC.{sig}"

    def translate_action(self, ir_step, indent: int) -> str:
        indent_str = self.get_indent(indent)
        sig = self._format_signal(ir_step.logical_signal)
        val = self._format_value(ir_step.value)
        return f"{indent_str}simva.set_signal({sig}, {val})"

    def translate_check(self, ir_step, indent: int) -> str:
        indent_str = self.get_indent(indent)
        sig = self._format_signal(ir_step.logical_signal)
        val = self._format_value(ir_step.expected_value)
        
        # 1. 단발성 체크
        if ir_step.duration_sec is None or ir_step.duration_sec == 0:
             op_map = {"==": "is_eq", "!=": "is_ne", "<": "is_lt", ">": "is_gt", "<=": "is_le", ">=": "is_ge"}
             func = op_map.get(ir_step.operator.value, "is_eq")
             return f"{indent_str}simva.{func}({sig}, {val})"
        
        # 2. 지속 시간 체크
        else:
             op_map = {"==": "keep_eq", "!=": "keep_ne", "<": "keep_lt", ">": "keep_gt", "<=": "keep_le", ">=": "keep_ge"}
             func = op_map.get(ir_step.operator.value, "keep_eq")
             return f"{indent_str}simva.{func}({sig}, {val}, {ir_step.duration_sec})"
        
    def translate_wait(self, ir_step, indent: int) -> str:
        indent_str = self.get_indent(indent)
        return f"{indent_str}simva.wait({ir_step.duration_sec})"
        
    def translate_macro_call(self, ir_step, indent: int) -> str:
        indent_str = self.get_indent(indent)
        macro_name = ir_step.macro_name
        if "Precondition" in macro_name:
            return f"{indent_str}precondition.{macro_name}()"
        elif "CleanUp" in macro_name:
            return f"{indent_str}cleanup.{macro_name}()"
        elif "Alarm" in macro_name:
            return f"{indent_str}check.{macro_name}()"
        
        args_str = ""
        if ir_step.arguments:
            args_str = ", ".join([f"{k}={self._format_value(v)}" for k,v in ir_step.arguments.items()])
        
        # SIMVA 공식 지원 함수 목록 (simva_manual.md 기준)
        SIMVA_VALID_FUNCTIONS = {
            "reset_ecu", "add_measuring", "get_measuring_series", "get_acquisition_series",
            "get_signal", "set_signal", "wait",
            "is_eq", "is_ne", "is_lt", "is_gt", "is_le", "is_ge", "is_btw_ex", "is_btw_in",
            "turn_eq", "turn_ne", "turn_lt", "turn_gt", "turn_le", "turn_ge", "turn_btw_ex", "turn_btw_in",
            "keep_eq", "keep_ne", "keep_lt", "keep_gt", "keep_le", "keep_ge", "keep_btw_ex", "keep_btw_in",
            "set_acceleration", "set_interrupt",
            "add_acquisition_signal", "start_acquisition",
            "pulsing", "onoff_pulsing", "keep_duration",
        }
        
        if macro_name in SIMVA_VALID_FUNCTIONS:
            return f"{indent_str}simva.{macro_name}({args_str})"
        else:
            # 지원하지 않는 함수 호출 방지 - 주석으로 대체
            return f"{indent_str}# FIXME: Unknown macro '{macro_name}' - not a valid SIMVA function. Please implement manually."

    def translate_macro_def(self, ir_step, indent: int) -> str:
        header = f"\n# --- DEFINITION FOR {ir_step.category}.py ---"
        indent_str = self.get_indent(indent)
        def_line = f"{indent_str}def {ir_step.macro_name}({', '.join(ir_step.parameters or [])}):"
        
        body_parts = []
        for step in ir_step.body:
            body_parts.append(self.translate_step(step, indent=indent + 1))
        
        return f"{header}\n{def_line}\n" + "".join(body_parts) + "# --------------------------------------\n"

    def translate_condition(self, ir_step, indent: int) -> str:
        indent_str = self.get_indent(indent)
        
        # 구조화된 조건 필드가 있는 경우 실제 코드로 변환
        if ir_step.condition_signal and ir_step.condition_operator and ir_step.condition_value is not None:
            sig = self._format_signal(ir_step.condition_signal)
            val = self._format_value(ir_step.condition_value)
            
            # Operator 매핑 (translate_check과 동일한 로직 공유 가능)
            op_map = {"==": "is_eq", "!=": "is_ne", "<": "is_lt", ">": "is_gt", "<=": "is_le", ">=": "is_ge"}
            func = op_map.get(ir_step.condition_operator.value, "is_eq")
            
            cond_expr = f"simva.{func}({sig}, {val})"
        else:
            # 필드가 없으면 기존처럼 자연어 텍스트를 주석과 함께 사용 (Fallback)
            cond_expr = f"True  # FIXME: Manual check required for condition: {ir_step.condition_text}"
            
        cond = f"if {cond_expr}:"
        
        if_body = "".join([self.translate_step(s, indent + 1) for s in ir_step.if_body])
        else_part = ""
        if ir_step.else_body:
            else_part = f"{indent_str}else:\n" + "".join([self.translate_step(s, indent + 1) for s in ir_step.else_body])
            
        return f"{indent_str}{cond}\n{if_body}{else_part}"

    def translate_loop(self, ir_step, indent: int) -> str:
        indent_str = self.get_indent(indent)
        loop_line = f"for i in range({ir_step.count}):"
        body = "".join([self.translate_step(s, indent + 1) for s in ir_step.body])
        return f"{indent_str}{loop_line}\n{body}"

    def translate_complex_logic(self, ir_step, indent: int) -> str:
        indent_str = self.get_indent(indent + 1)
        # Smart Adapter LLM이 동적으로 코드를 생성해야 하는 부분
        # 현재는 지시사항을 주석으로 남기고 Dummy 코드를 생성
        return f"{indent_str}# [SMART ADAPTER LLM REQUIRED]\n{indent_str}# Instruction: {ir_step.instruction}\n{indent_str}pass"

    def generate_footer(self) -> str:
        return "\n# End of Generated Script"

if __name__ == "__main__":
    adapter = SimvaAdapter()
    adapter.run()

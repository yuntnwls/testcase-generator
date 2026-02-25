# Contextual RAG — Jinja2 템플릿 엔진 설계

본 문서는 방안 C의 **Assembler 단계**에서 Jinja2를 코드 조립 엔진으로 활용하는 방법을 정의합니다.

> 참조: [architecture.md](../architecture.md) §Assembler, [db/vector_db_design.md](../db/vector_db_design.md) §3.1 `target_code` 필드

---

## 1. Jinja2란 무엇인가?

**Jinja2**는 Python에서 가장 널리 사용되는 **텍스트 템플릿 엔진(Template Engine)** 라이브러리입니다. 2006년에 Flask·Django 개발자들이 만들었으며, 현재는 Ansible(인프라 자동화), GitHub Actions(YAML 생성), 각종 코드 제너레이터 등 텍스트를 동적으로 생성해야 하는 모든 분야에서 사용됩니다.

### 템플릿 엔진이란?

"고정된 뼈대(Template)에 동적인 데이터를 채워 넣어 최종 텍스트를 만드는 도구"입니다.

```
뼈대(Template)          +     데이터(Variables)      =    최종 출력(Rendered Text)
─────────────────────────────────────────────────────────────────────────────
"안녕하세요, {{ name }}님!   +  { "name": "홍길동" }   =   "안녕하세요, 홍길동님!
 주문 번호는                   "order_id": "A-001"       주문 번호는
 {{ order_id }}입니다."      }                            A-001입니다."
```

### Jinja2의 4가지 핵심 문법

| 문법 | 용도 | 예시 |
| :--- | :--- | :--- |
| `{{ variable }}` | 변수 출력 | `{{ signal }}` → `VehicleSpeed` |
| `{{ value \| filter }}` | 필터 적용 (값 변환) | `{{ "5" \| float }}` → `5.0` |
| `{% if 조건 %}...{% endif %}` | 조건 분기 | `{% if data_type == "boolean" %}` |
| `{% for x in list %}...{% endfor %}` | 반복 | `{% for step in steps %}` |

### Python 웹 프레임워크에서의 사용 예 (참고)

Flask나 Django에서는 HTML 파일에 데이터를 주입할 때 사용합니다.

```html
<!-- templates/welcome.html (Jinja2 템플릿) -->
<h1>안녕하세요, {{ user.name }}님</h1>
{% for item in cart %}
  <li>{{ item.name }} - {{ item.price | int }}원</li>
{% endfor %}
```

```python
# Flask에서 렌더링
return render_template("welcome.html", user=user, cart=cart_items)
```

### 본 프로젝트에서의 활용 — HTML 대신 Python 코드 생성

HTML 생성과 원리는 동일하되, **출력 대상이 HTML이 아닌 Python 테스트 코드**입니다.

```
웹 프레임워크: HTML 템플릿 + 사용자 데이터 → 웹페이지
본 프로젝트:  코드 템플릿 + TC 변수 데이터  → Python 테스트 스크립트
```

---

## 2. Jinja2가 왜 필요한가?

### 기존 방식의 한계 — Python `.format()` 또는 f-string

현재 Vector DB의 `target_code` 필드는 단순 문자열 플레이스홀더를 사용합니다.

```python
# Vector DB target_code 필드
target_code = "simva.set_signal(signals.{ecu}.{signal}, \"{value}\")"

# Assembler에서 조립
code = target_code.format(ecu="CGW", signal="VehicleSpeed", value="0")
# 결과: simva.set_signal(signals.CGW.VehicleSpeed, "0")
```

이 방식은 **단순 변수 치환**에는 충분하지만, 아래 상황에서는 한계가 드러납니다.

| 상황 | 문제 |
| :--- | :--- |
| 값이 숫자 vs 문자열 | `"1"` vs `1` 타입에 따라 따옴표 처리가 달라져야 함 |
| 선택적 파라미터 | duration이 없는 경우 `wait()` 인수 생략 필요 |
| 중첩 코드 (if/for) | 내부 블록의 들여쓰기 자동 처리 불가 |
| 다중 조건 | 3개 이상의 분기가 있을 때 유연하게 대응 불가 |

### Jinja2의 해법

Jinja2는 Python에서 가장 널리 사용되는 **텍스트 템플릿 엔진**입니다. HTML 렌더링(Flask, Django)으로 유명하지만, **코드 생성**에도 강력하게 활용됩니다.

```
{{ variable }}         ← 변수 출력
{% if 조건 %}...{% endif %}  ← 조건 분기
{% for x in list %}...{% endfor %}  ← 반복
{{ value | filter }}   ← 필터 (변환/포맷)
```

---

## 2. Assembler에서의 역할

```
3-Tier Extractor 결과
    {signal: "차량속도", value: "0", ecu: "CGW", data_type: "uint16"}
                    │
                    ▼
        Vector DB의 target_code (Jinja2 템플릿 문자열)
            "simva.set_signal(signals.{{ ecu }}.{{ signal }}, {{ value | cast(data_type) }})"
                    │
                    ▼
        Jinja2 Environment.from_string().render(**variables)
                    │
                    ▼
        최종 조립된 코드
            "simva.set_signal(signals.CGW.VehicleSpeed, 0)"
```

Vector DB의 `target_code` 필드가 Jinja2 템플릿 문자열로 저장되며, Assembler가 추출된 변수로 렌더링합니다.

---

## 3. 기본 예시 — 타입별 템플릿

### 3.1 ACTION — 단순 값 설정

**Vector DB `target_code`:**
```jinja
simva.set_signal(signals.{{ ecu }}.{{ signal }}, {{ value | to_python_value(data_type) }})
```

**Assembler 입력 변수:**
```python
{
    "ecu": "CGW",
    "signal": "VehicleSpeed",
    "value": "0",
    "data_type": "uint16"
}
```

**렌더링 결과:**
```python
simva.set_signal(signals.CGW.VehicleSpeed, 0)
```

---

### 3.2 TYPE_WAIT — 대기

**Vector DB `target_code`:**
```jinja
simva.wait({{ duration | float }})
```

**렌더링 결과 (duration="5"):**
```python
simva.wait(5.0)
```

> `| float` 필터로 `"5"` → `5.0`으로 자동 캐스팅됩니다.

---

### 3.3 TYPE_CHECK — 상태 확인 (값 타입별 분기)

**Vector DB `target_code`:**
```jinja
{% if check_type == "eq" %}
result = simva.is_eq(signals.{{ ecu }}.{{ signal }}, {{ value | to_python_value(data_type) }})
{% elif check_type == "ge" %}
result = simva.is_ge(signals.{{ ecu }}.{{ signal }}, {{ value | to_python_value(data_type) }})
{% elif check_type == "keep" %}
result = simva.keep_eq(signals.{{ ecu }}.{{ signal }}, {{ value | to_python_value(data_type) }}, {{ duration | float }})
{% endif %}
```

**렌더링 결과 (check_type="keep", duration="10"):**
```python
result = simva.keep_eq(signals.BDC.HazardLamp, 1, 10.0)
```

---

### 3.4 META_CONTROL_IFELSE — 조건문 (재귀 조립)

If-Else 구조는 `true_action`, `false_action`이 **이미 조립된 코드 블록**으로 주입됩니다. Jinja2의 `indent` 필터가 들여쓰기를 자동 처리합니다.

**Vector DB `target_code`:**
```jinja
if {{ condition }}:
{{ true_action | indent(4, first=True) }}
else:
{{ false_action | indent(4, first=True) }}
```

**Assembler 입력 변수** (재귀적으로 먼저 조립된 값):
```python
{
    "condition": "simva.is_eq(signals.CGW.VehicleSpeed, 0)",
    "true_action": "simva.set_signal(signals.BDC.DoorLock, 1)",
    "false_action": "simva.set_signal(signals.BDC.DoorLock, 0)"
}
```

**렌더링 결과:**
```python
if simva.is_eq(signals.CGW.VehicleSpeed, 0):
    simva.set_signal(signals.BDC.DoorLock, 1)
else:
    simva.set_signal(signals.BDC.DoorLock, 0)
```

> `indent(4, first=True)` 필터가 각 줄 앞에 공백 4칸을 자동으로 추가합니다.

---

### 3.5 META_CONTROL_LOOP — 반복문

**Vector DB `target_code`:**
```jinja
for i in range({{ count | int }}):
{{ action | indent(4, first=True) }}
```

**렌더링 결과 (count="3", action이 여러 줄인 경우):**
```python
for i in range(3):
    simva.set_signal(signals.BCM.WindowPos, 100)
    simva.wait(1.0)
    simva.set_signal(signals.BCM.WindowPos, 0)
    simva.wait(1.0)
```

> 여러 줄 `action`에도 `indent` 필터 하나로 들여쓰기가 모두 처리됩니다.

---

## 4. 커스텀 필터 설계

Jinja2에 커스텀 필터를 등록하면, 도메인 특화 변환을 템플릿 안에서 선언적으로 처리할 수 있습니다.

```python
from jinja2 import Environment

def to_python_value(value: str, data_type: str) -> str:
    """
    신호 data_type에 맞춰 Python 리터럴로 변환하는 커스텀 필터.
    
    Examples:
        "1" + "boolean" -> "True"
        "1" + "uint8"   -> "1"
        "1" + "float32" -> "1.0"
        "ON" + "string" -> '"ON"'
    """
    match data_type:
        case "boolean":
            return "True" if value in ("1", "ON", "True", "켜짐") else "False"
        case "float32" | "float64":
            return str(float(value))
        case "uint8" | "uint16" | "int16" | "int32":
            return str(int(value))
        case _:  # string 등 나머지
            return f'"{value}"'

# Jinja2 환경에 커스텀 필터 등록
env = Environment()
env.filters["to_python_value"] = to_python_value

# 템플릿 렌더링
template_str = "simva.set_signal(signals.{{ ecu }}.{{ signal }}, {{ value | to_python_value(data_type) }})"
template = env.from_string(template_str)
code = template.render(ecu="CGW", signal="IG_Status", value="ON", data_type="boolean")

# 결과: simva.set_signal(signals.CGW.IG_Status, True)
print(code)
```

---

## 5. 방안 B vs C — Assembler 비교

| 항목 | 방안 B (Python format) | 방안 C (Jinja2) |
| :--- | :--- | :--- |
| **단순 변수 치환** | ✅ 가능 | ✅ 동일 |
| **타입별 값 포맷** | ⚠️ Assembler 코드에서 처리 | ✅ `\| to_python_value` 필터로 템플릿 내 처리 |
| **들여쓰기 자동화** | ❌ 직접 구현 필요 | ✅ `\| indent` 필터 |
| **조건 분기 (if/elif)** | ❌ 별도 template 여러 개 필요 | ✅ 하나의 템플릿에서 처리 |
| **선택적 파라미터** | ❌ format 에러 발생 가능 | ✅ `{% if var is defined %}` |
| **템플릿 가독성** | ⚠️ 보통 | ✅ 선언적, 의도가 명확 |
| **테스트 용이성** | ⚠️ Assembler 코드 테스트 필요 | ✅ 템플릿 파일 단독 테스트 가능 |

---

## 6. Vector DB 스키마 업데이트 (방안 C Jinja2 적용)

방안 C에서는 Vector DB의 `target_code` 필드를 **Jinja2 템플릿 문자열**로 저장합니다.

```json
{
  "id": "check_signal_keep",
  "context_prefix": "특정 시그널이 지정된 시간 동안 기대값을 지속적으로 유지하는지 판정하는 동작. 판정 조건 컬럼에서 '~동안 유지', 'keep' 패턴에 사용됨.",
  "type_source": "{signal}이 {duration}초 동안 {value}을 유지해야 한다",
  "type": "TYPE_CHECK",
  "regex_pattern": "^.*?(?P<signal>[\\S\\s]+?)이\\s+(?P<duration>[0-9.]+)초\\s+동안\\s+(?P<value>[\\S]+)을?\\s+유지.*$",
  "variables": "[\"signal\", \"value\", \"duration\"]",
  "target_code": "result = simva.keep_eq(signals.{{ ecu }}.{{ signal }}, {{ value | to_python_value(data_type) }}, {{ duration | float }})"
}
```

기존 `{variable}` → Jinja2 `{{ variable }}`로 표기만 바뀌며, 필터(`| to_python_value`, `| float`, `| indent`)를 추가로 활용할 수 있습니다.

---

## 7. 전체 Assembler 구현 예시

```python
from jinja2 import Environment
from ontology_router import OntologyRouter

class JinjaAssembler:
    """
    Jinja2 기반 코드 조립기.
    Extractor가 추출한 변수 + Ontology 매핑 결과를 받아 최종 코드를 생성합니다.
    """
    
    def __init__(self):
        self.env = Environment()
        self.env.filters["to_python_value"] = self._to_python_value
        self.ontology = OntologyRouter()

    def assemble(self, template_match: TemplateMatch, raw_vars: dict) -> str:
        """
        Args:
            template_match: Vector DB 검색 결과 (target_code Jinja2 템플릿 포함)
            raw_vars: Extractor가 추출한 원시 변수 {"signal": "차량속도", "value": "0"}
        Returns:
            최종 Python 코드 문자열
        """
        # 1. Ontology로 시그널명 번역: "차량속도" → ecu="CGW", signal="VehicleSpeed"
        ontology_result = self.ontology.resolve(
            signal_text=raw_vars.get("signal"),
            variant=current_variant   # 현재 차종 컨텍스트
        )
        
        # 2. 변수 병합
        render_vars = {**raw_vars, **ontology_result}
        # render_vars = {
        #     "signal": "VehicleSpeed", "ecu": "CGW",
        #     "value": "0", "data_type": "uint16"
        # }
        
        # 3. Jinja2 렌더링
        template = self.env.from_string(template_match.target_code)
        return template.render(**render_vars).strip()

    @staticmethod
    def _to_python_value(value: str, data_type: str) -> str:
        match data_type:
            case "boolean": return "True" if value in ("1", "ON", "켜짐", "True") else "False"
            case "float32" | "float64": return str(float(value))
            case "uint8" | "uint16" | "int16" | "int32": return str(int(value))
            case _: return f'"{value}"'
```

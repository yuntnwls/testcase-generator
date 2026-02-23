import os
import json
import csv
import random

# Ensure data directory exists
data_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(data_dir, exist_ok=True)

# 1. Generate Mock Vector DB (Signal Dictionary)
mock_signals = [
    {
        "id": "sig_veh_spd",
        "text": "속도, 차속, 엑셀, 가속, 감속, 브레이크 밟기, 시속, km/h, speed, velocity",
        "metadata": {
            "logical_name": "VehicleSpeed",
            "data_type": "float",
            "unit": "km/h",
            "description": "차량의 주행 속도 제어"
        }
    },
    {
        "id": "sig_ign_sta",
        "text": "엔진, 시동, 발동기, 켜다, 끄다, ignition, engine, start, stop, IGN",
        "metadata": {
            "logical_name": "Ignition_Status",
            "data_type": "enum",
            "allowed_values": ["ON", "OFF"],
            "description": "차량 엔진 시동 상태 제어"
        }
    },
    {
        "id": "sig_hlmp_sta",
        "text": "전조등, 헤드램프, 앞불, 라이트, 상향등, 하향등, headlamp, light, illumination",
        "metadata": {
            "logical_name": "HeadLamp_State",
            "data_type": "enum",
            "allowed_values": ["OFF", "LOW", "HIGH"],
            "description": "차량 전조등 조명 제어"
        }
    },
    {
        "id": "sig_door_sta",
        "text": "문, 도어, 열림, 닫힘, 잠금, 해제, door, lock, unlock, open, close",
        "metadata": {
            "logical_name": "Door_Status",
            "data_type": "enum",
            "allowed_values": ["OPEN", "CLOSED", "LOCKED", "UNLOCKED"],
            "description": "차량 도어 개폐 및 잠금 상태 제어"
        }
    },
    {
        "id": "sig_wiper_sta",
        "text": "와이퍼, 유리닦이, 비, 눈, 워셔액, 작동, 정지, wiper, rain, washer",
        "metadata": {
            "logical_name": "Wiper_State",
            "data_type": "enum",
            "allowed_values": ["OFF", "LOW", "HIGH", "AUTO"],
            "description": "앞유리 와이퍼 작동 상태"
        }
    },
    {
        "id": "sig_hazard_sw",
        "text": "비상등, 해저드, 경광등, 긴급 깜빡이, 양방향 깜빡이, hazard, emergency light, blinker, flasher",
        "metadata": {
            "logical_name": "HazardLightSw",
            "data_type": "enum",
            "allowed_values": ["ON", "OFF"],
            "description": "비상등(해저드 램프) 스위치 제어"
        }
    },
    {
        "id": "sig_warn_lamp",
        "text": "경고, 알람, 경보, 위험, 알림, 경고등, warning, alarm, alert, danger",
        "metadata": {
            "logical_name": "WarningLamp",
            "data_type": "enum",
            "allowed_values": ["ON", "OFF"],
            "description": "경고등/알람 상태 제어"
        }
    }
]

vector_db_path = os.path.join(data_dir, 'mock_vector_db.json')
with open(vector_db_path, 'w', encoding='utf-8') as f:
    json.dump(mock_signals, f, ensure_ascii=False, indent=2)

print(f"Generated Mock Vector DB: {vector_db_path}")

# 2. Generate Mock TC Data
tc_headers = [
    "대상 제어기", "대분류", "중분류", "소분류", "Requirement ID", "검증 목적", "T/Case ID", 
    "협조 제어기", "시험 전 조건", "시험 방법", "판정 조건", "결과", "Version", "적용 지역", 
    "Variant Option", "검증 시점", "검증 환경", "신호/변수", "TC 개발 기준(기능 안전 대상)", 
    "초기화(Clean up)", "플랜트 버전", "자동화 스크립트 버전", "데이터 저장 방법", 
    "시험 전 조건(RB/자동화)", "시험 방법(RB/자동화)", "판정 조건(RB/자동화)"
]

mock_test_cases = []
controllers = ["BDC (BCM)", "VCU", "ICU", "MCU"]
categories = {
    "LAMP": ["Front Lamp", "Rear Lamp", "Interior Lamp"],
    "DOOR": ["Power Window", "Door Lock", "Tailgate"],
    "WIPER": ["Front Wiper", "Rear Wiper", "Washer"]
}

# Generate 50 realistic rows of mock data
for i in range(1, 51):
    major_cat = random.choice(list(categories.keys()))
    minor_cat = random.choice(categories[major_cat])
    controller = random.choice(controllers)
    req_id = f"REQ_{major_cat}_{minor_cat.replace(' ', '')}_v1"
    tc_id = f"TC_{major_cat}_{i:03d}"
    
    # Generate somewhat random test steps
    methods = [
        f"(VehicleSpeed = {random.choice([0, 10, 50, 100])})",
        f"(Lamp_LightSwSta = {random.choice(['On', 'Off'])})",
        f"({random.choice(['5초 후 KEY_IN', 'Wait(500)', 'Wait(1000)'])})"
    ]
    random.shuffle(methods)
    # 셔플 후 순차적으로 번호 부여
    numbered_methods = [f"{i+1}. {m}" for i, m in enumerate(methods[:random.randint(1, 3)])]
    test_method = "\n".join(numbered_methods)
    
    conditions = [
        f"(Lamp_PuddleLamp = {random.choice(['On', 'Off'])})",
        f"(Door_Status = {random.choice(['LOCKED', 'UNLOCKED'])})",
        f"(CheckOverKPH({random.choice([10, 50])}))"
    ]
    random.shuffle(conditions)
    # 셔플 후 순차적으로 번호 부여
    numbered_conditions = [f"{i+1}. {c}" for i, c in enumerate(conditions[:random.randint(1, 2)])]
    judgement = "\n".join(numbered_conditions)
    
    precon = f"1. (Initial_Engine{random.choice(['ON', 'OFF'])})" if random.random() > 0.5 else ""
    
    row = {
        "대상 제어기": controller,
        "대분류": "제어기능",
        "중분류": major_cat,
        "소분류": minor_cat,
        "Requirement ID": req_id,
        "검증 목적": f"{minor_cat} 기능 점검 샘플 TC",
        "T/Case ID": tc_id,
        "협조 제어기": "M/F SW",
        "시험 전 조건": precon,
        "시험 방법": test_method,
        "판정 조건": judgement,
        "결과": "",
        "Version": "1.0",
        "적용 지역": "ALL",
        "Variant Option": "",
        "검증 시점": "",
        "검증 환경": "SIL",
        "신호/변수": "",
        "TC 개발 기준(기능 안전 대상)": "",
        "초기화(Clean up)": "[Cleanup]\n1. (Reset = OFF)",
        "플랜트 버전": "",
        "자동화 스크립트 버전": "",
        "데이터 저장 방법": "",
        "시험 전 조건(RB/자동화)": precon,
        "시험 방법(RB/자동화)": test_method,
        "판정 조건(RB/자동화)": judgement
    }
    mock_test_cases.append(row)


mock_tc_path = os.path.join(data_dir, 'mock_tc_data.tsv')
with open(mock_tc_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=tc_headers, delimiter='\t')
    writer.writeheader()
    writer.writerows(mock_test_cases)

print(f"Generated Mock TSV Test Cases ({len(mock_test_cases)} rows): {mock_tc_path}")

# 3. Generate Mock Ontology (Graph DB / Knowledge Graph)
mock_ontology = {
    "nodes": [
        { "id": "Ignition_Status", "type": "Signal", "description": "엔진 시동 상태" },
        { "id": "VehicleSpeed", "type": "Signal", "description": "차량 주행 속도" },
        { "id": "HeadLamp_State", "type": "Signal", "description": "전조등 상태" },
        { "id": "Battery_Voltage", "type": "Signal", "description": "배터리 전압" },
        { "id": "Door_Status", "type": "Signal", "description": "도어 잠금 상태" },
        { "id": "Wiper_State", "type": "Signal", "description": "와이퍼 상태" },
        { "id": "HazardLightSw", "type": "Signal", "description": "비상등 스위치" },
        { "id": "WarningLamp", "type": "Signal", "description": "경고등/알람" }
    ],
    "relationships": [
        {
            "source": "VehicleSpeed",
            "relation": "REQUIRES",
            "target": "Ignition_Status",
            "condition": "== ON",
            "description": "차량 속도를 올리려면 반드시 엔진 시동(IGN)이 켜져 있어야 합니다."
        },
        {
            "source": "HeadLamp_State",
            "relation": "AFFECTS",
            "target": "Battery_Voltage",
            "effect": "DECREASE",
            "description": "전조등을 켜면 배터리 전압이 일시적으로 하강할 수 있습니다."
        },
        {
            "source": "Wiper_State",
            "relation": "REQUIRES",
            "target": "Ignition_Status",
            "condition": "== ON",
            "description": "와이퍼 모터는 시동이 켜진(또는 ACC) 상태에서만 전원을 공급받아 동작합니다."
        },
        {
            "source": "VehicleSpeed",
            "relation": "CONFLICTS_WITH",
            "target": "Door_Status",
            "condition": "== OPEN",
            "description": "주행 중(Velocity > 0)일 때는 도어가 열려(OPEN) 있어서는 안 됩니다. (위험 요소)"
        }
    ]
}

ontology_db_path = os.path.join(data_dir, 'mock_ontology_db.json')
with open(ontology_db_path, 'w', encoding='utf-8') as f:
    json.dump(mock_ontology, f, ensure_ascii=False, indent=2)

print(f"Generated Mock Ontology DB (Graph Rules): {ontology_db_path}")

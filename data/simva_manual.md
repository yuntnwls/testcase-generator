# SIMVA Script API Manual

[Create TestSuite] 
- 이전에 Script 사용한 적이 없다면,
    **TestSuite 생성 시** 자동으로 Script를 사용할 수 있는 파이썬 프로젝트 환경 구축
- 생성된 TestSuite.py에 add할 Testcase 작성 예시
    ```python
    def testcase1():
    		simvasimva.enable_traceback()
    		# traceback 활성화하고 시작하면 에러 출력 더 자세히 볼 수 있음
        simva.wait(1)
        simva.set_signal(signals.BDC.C_WPC_NFCReset_LCAN_BDC, 1)
        simva.reset_ecu(profiles.BDC)
        simva.wait(1)
        simva.is_eq(signals.BDC.C_WPC_NFCReset_LCAN_BDC, 1)
        simva.wait(1)
        simva.keep_ge(signals.BDC.C_WPC_NFCReset_LCAN_BDC, 0, 2.5)
    		# 제어문, 반복문 사용 가능 
        for i in range(1,10):
            simva.set_signal(signals.PDC.BatteryVoltage, i)
            simva.wait(1)
    		# 원하는 판정 함수 없을 시 요청하면 제공 가능하고, 
    		# 아래 함수 통해서 measuring 데이터 사용해서 직접 로직 구현도 가능
        series = simva.get_measuring_series(signals.PDC.BatteryVoltage)
        print(f"\nBatteryVoltage: \n{series}")
    ```
    
- TestSuite.py에  testcase 추가 (여러 개 추가 가능, 각각 다른 TestSuite에서 testcase  재활용 가능)
- run.bat 실행을 통해 스크립트 실행
    - 실행 전 Testbench Connect까지 실행 후 터미널에서 해당 명령어 실행
    ```python
    .\run.bat [Test Suite 파일명]
    ```

[사용 가능한 함수]
| 함수명 | 설명 | 주요 파라미터 |
| --- | --- | --- |
| reset_ecu | ECU(또는 전체 ECU) 리셋 | ecu_name: str = "" |
| add_measuring | 측정 신호 추가 | key: int |
| get_measuring_series | 측정 신호의  Time(sec),Value 배열 데이터 반환 | key: int |
| get_acquisition_series | 측정 신호의  Time(sec),Value 배열 데이터 반환 | key: int |
| get_signal | 신호 값 읽기 | key: int |
| set_signal | 신호 값 설정 | key: int, value: float |
| wait | 지정 시간(초)만큼 대기 | duration_sec: float |
| is_eq | 신호 값이 특정 값과 같은지 검사 | key: int, value: float |
| is_ne | 신호 값이 특정 값과 다른지 검사 | key: int, value: float |
| is_lt | 신호 값이 특정 값보다 작은지 검사 | key: int, value: float |
| is_gt | 신호 값이 특정 값보다 큰지 검사 | key: int, value: float |
| is_le | 신호 값이 특정 값 이하인지 검사 | key: int, value: float |
| is_ge | 신호 값이 특정 값 이상인지 검사 | key: int, value: float |
| is_btw_ex | min < (signal's value) < max | key: int, min: float, max: float |
| is_btw_in | min ≤ (signal's value) ≤ max | key: int, min: float, max: float |
| turn_eq | 일정 시간 동안 신호 값이 특정 값이 된 적이 있는지 검사 | key: int, value: float, duration_sec: float |
| turn_ne | 일정 시간 동안 신호 값이 특정 값이 아닌 적이 있는지 검사 | key: int, value: float, duration_sec: float |
| turn_lt | 일정 시간 동안 신호 값이 특정 값보다 작은 적이 있는지 검사 | key: int, value: float, duration_sec: float |
| turn_gt | 일정 시간 동안 신호 값이 특정 값보다 큰 적이 있는지 검사 | key: int, value: float, duration_sec: float |
| turn_le | 일정 시간 동안 신호 값이 특정 값 이하인 적이 있는지 검사 | key: int, value: float, duration_sec: float |
| turn_ge | 일정 시간 동안 신호 값이 특정 값 이상인 적이 있는지 검사 | key: int, value: float, duration_sec: float |
| turn_btw_ex | 일정 시간 동안 min < (signal's value) < max 인 적이 있는지 | key: int, min: float, max: float, duration_sec: float |
| turn_btw_in | 일정 시간 동안  min ≤ (signal's value) ≤ max 인 적이 있는지 | key: int, min: float, max: float, duration_sec: float |
| keep_eq | 일정 시간 동안 신호 값이 계속 특정 값인지 검사 | key: int, value: float, duration_sec: float |
| keep_ne | 일정 시간 동안 신호 값이 계속 특정 값이 아닌지 검사 | key: int, value: float, duration_sec: float |
| keep_lt | 일정 시간 동안 신호 값이 계속 특정 값보다 작은지 검사 | key: int, value: float, duration_sec: float |
| keep_gt | 일정 시간 동안 신호 값이 계속 특정 값보다 큰지 검사 | key: int, value: float, duration_sec: float |
| keep_le | 일정 시간 동안 신호 값이 계속 특정 값 이하인지 검사 | key: int, value: float, duration_sec: float |
| keep_ge | 일정 시간 동안 신호 값이 계속 특정 값 이상인지 검사 | key: int, value: float, duration_sec: float |
| keep_btw_ex | 일정 시간 동안 min < (signal's value) < max 가 계속 유지되는지 | key: int, min: float, max: float, duration_sec: float |
| keep_btw_in | 일정 시간 동안 min ≤ (signal's value) ≤ max 가 계속 유지되는지 | key: int, min: float, max: float, duration_sec: float |
| set_acceleration | 시뮬레이션 가속도 설정 | acceleration: int |
| set_interrupt | 신호 인터럽트 주기 설정 | key: int, interrupt_period_sec: float |
| add_acquisition_signal | acquisition 신호 추가 | key: int |
| start_acquisition | acquisition 시작 | duration_sec: float |
| pulsing | 신호 pulsing 체크 | key: int, pulsing_value: float, pulsing_duration_sec: float, tolerance_time_sec: float |
| onoff_pulsing | 신호 on/off pulsing 체크 | key: int, on_value: float, off_value: float, on_duration_sec: float, off_duration_sec: float, total_duration_sec: float, tolerance_time_Sec: float |
| keep_duration | 신호 값이 일정 시간 동안 유지되는지 체크 | key: int, keep_value: float, duration_sec: float, wait_time_sec: float , tolerance_time_sec: float |

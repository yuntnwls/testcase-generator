from simvabasic import simva
from references import signals, profiles

import testcases.config as config
import testcases.functions.precondition as precondition
import testcases.functions.cleanup as cleanup
import testcases.functions.method as method
import testcases.functions.acquisition as acquisition
import testcases.functions.outputcheck as check
import testcases.quantity as q
import logging

logger = logging.getLogger(__name__)

def BAlarm_Func_TGate_232_1_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_DRV()
    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Unlock_BTN_ON)
    check.BAlarmState_DISARM_Turns()

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=2, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=2, hazard_on_sec=0.5, hazard_off_sec=0.5)
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results(series["buzzer"], expected_count=2, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
    
    acquisition.pulse_results(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
    
    check.Alarm_Off_Check()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_232_1_2():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_AST()
    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Unlock_BTN_ON)
    check.BAlarmState_DISARM_Turns()

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=2, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=2, hazard_on_sec=0.5, hazard_off_sec=0.5)
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results(series["buzzer"], expected_count=2, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
    
    acquisition.pulse_results(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
    
    check.Alarm_Off_Check()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_232_1_3():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_RL()
    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Unlock_BTN_ON)
    check.BAlarmState_DISARM_Turns()

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=2, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=2, hazard_on_sec=0.5, hazard_off_sec=0.5)
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results(series["buzzer"], expected_count=2, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
    
    acquisition.pulse_results(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
    
    check.Alarm_Off_Check()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_232_1_4():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_RR()
    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Unlock_BTN_ON)
    check.BAlarmState_DISARM_Turns()

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=2, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=2, hazard_on_sec=0.5, hazard_off_sec=0.5)
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results(series["buzzer"], expected_count=2, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
    
    acquisition.pulse_results(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
    
    check.Alarm_Off_Check()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_237_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM()
    method.All_Close()
    method.RKE1_Trunk_BTN_Press()

    check.BAlarmState_DISARM_Turns()
    check.Alarm_Off_Check()

    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_238_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM()
    method.All_Close()
    method.Passive_Trunk_BTN_Press()

    check.BAlarmState_DISARM_Turns()
    check.Alarm_Off_Check()

    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_239_1():
    if config.ELECTRIC_VEHICLE:
        return
    
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_DRV()
    method.ACCSW_On()
    check.BAlarmState_ALARM_Turns()
    check.Alarm_Off_Check()
    cleanup.CleanUp_BAlarm()


def BAlarm_Func_TGate_240_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM()
    method.DRV_Door_Close()
    method.All_Door_Knob_SW_Lock()

    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Lock_BTN_ON)
    simva.wait(config.DELAY_50MS)
    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Lock_BTN_OFF)

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=1, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=1, hazard_on_sec=0.5, hazard_off_sec=0.5)
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results(series["buzzer"], expected_count=1, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
    
    acquisition.pulse_results(series["hazard"], expected_count=1, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
    check.Alarm_Off_Check()
    check.BAlarmState_ARMWAIT_Turns()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_242_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM()
    method.DRV_Door_Close()
    method.Passive_Lock_BTN_Press()

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=1, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=1, hazard_on_sec=0.5, hazard_off_sec=0.5)
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results(series["buzzer"], expected_count=1, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
    
    acquisition.pulse_results(series["hazard"], expected_count=1, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
    
    check.BAlarmState_ARMWAIT_Turns()   # 출력 확인 위치 고민 필요
    
    check.Alarm_Off_Check()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_247_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_Hood()
    method.RKE1_Lock_BTN_Press()
    check.BAlarmState_PREARM_Turns()
    check.Alarm_Off_Check()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_248_1():
    precondition.Precondition_BAlarm_ALARM_Hood()
    method.All_Door_Knob_SW_Unlock()
    method.Passive_Lock_BTN_Press()
    check.BAlarmState_PREARM_Turns(config.DELAY_5SEC)
    check.Alarm_Off_Check()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_251_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return

    precondition.Precondition_BAlarm_ALARM()
    acquisition.BAlarm_On()
    method.DRV_Door_Close()
    check.BAlarmState_REARM_Turns()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_252_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_DRV()
    acquisition.BAlarm_On()
    check.BAlarmState_ALARM_Turns()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_253_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_DRV()
   
    if simva.get_signal(signals.BDC.E_EOL_Country) in [q.DOMESTIC, q.CANADA, q.USA]: # 0: DOMESTIC, 5: CANADA, 6: USA
        acquisition.check_hazard_horn_pulse_test(expected_count=7, on_duration_sec=1, off_duration_sec=1)
        method.DRV_Door_Close(False)
        acquisition.check_hazard_horn_pulse_test(expected_count=7, on_duration_sec=1, off_duration_sec=1)

        simva.wait(config.DELAY_10SEC)
        acquisition.check_hazard_horn_pulse_test(expected_count=14, on_duration_sec=1, off_duration_sec=1)

    elif simva.get_signal(signals.BDC.E_EOL_Country) in [q.EUROPE]:  # 3: EUROPE
        acquisition.check_hazard_horn_pulse_test(expected_count=10, on_duration_sec=0.45, off_duration_sec=0.45)
        method.DRV_Door_Close(False)
        acquisition.check_hazard_horn_pulse_test(expected_count=20, on_duration_sec=0.45, off_duration_sec=0.45)

    simva.wait(config.DELAY_1500MS)
    
    for i in range(0,150):
        check.Horn_Off_Is()
        if config.EXIST_BDC and config.EXIST_PDC:
            check.Hazard_Off_Is()
        elif config.EXIST_BDC and not config.EXIST_PDC:
            check.Hazard_Inactive_Is()

        simva.wait(config.DELAY_10MS)

    check.BAlarmState_REARM_Turns()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_254_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return

    precondition.Precondition_BAlarm_ALARM_DRV()

    if simva.get_signal(signals.BDC.E_EOL_Country) in [q.DOMESTIC, q.CANADA, q.USA]: # 0: DOMESTIC, 5: CANADA, 6: USA

        series = acquisition.acquire_hazard_horn(horn_expected_count=7, horn_on_sec=1, horn_off_sec=1, 
                                                 hazard_expected_count=7, hazard_on_sec=1, hazard_off_sec=1)
        acquisition.pulse_results(series["horn"], expected_count=7, on_sec=1, off_sec=1,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=7, on_sec=1, off_sec=1,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF) 
        
        method.AST_Door_Open()

        series = acquisition.acquire_hazard_horn(horn_expected_count=7, horn_on_sec=1, horn_off_sec=1, 
                                                 hazard_expected_count=7, hazard_on_sec=1, hazard_off_sec=1)
        acquisition.pulse_results(series["horn"], expected_count=7, on_sec=1, off_sec=1,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=7, on_sec=1, off_sec=1,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF) 

        simva.wait(config.DELAY_10SEC)

        series = acquisition.acquire_hazard_horn(horn_expected_count=14, horn_on_sec=1, horn_off_sec=1, 
                                                 hazard_expected_count=14, hazard_on_sec=1, hazard_off_sec=1)
        acquisition.pulse_results(series["horn"], expected_count=14, on_sec=1, off_sec=1,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=14, on_sec=1, off_sec=1,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF) 

    elif simva.get_signal(signals.BDC.E_EOL_Country) in [q.EUROPE]:  # 3: EUROPE

        series = acquisition.acquire_hazard_horn(horn_expected_count=10, horn_on_sec=0.45, horn_off_sec=0.45, 
                                                 hazard_expected_count=10, hazard_on_sec=0.45, hazard_off_sec=0.45)
        acquisition.pulse_results(series["horn"], expected_count=10, on_sec=0.45, off_sec=0.45,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=10, on_sec=0.45, off_sec=0.45,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF) 

        method.AST_Door_Open(False)

        series = acquisition.acquire_hazard_horn(horn_expected_count=20, horn_on_sec=0.45, horn_off_sec=0.45, 
                                                 hazard_expected_count=20, hazard_on_sec=0.45, hazard_off_sec=0.45)
        acquisition.pulse_results(series["horn"], expected_count=20, on_sec=0.45, off_sec=0.45,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=20, on_sec=0.45, off_sec=0.45,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
    
    simva.wait(config.DELAY_1500MS)

    for i in range(0, 150):
        check.Horn_Off_Is()
        if config.EXIST_BDC and config.EXIST_PDC:
            check.Hazard_Off_Is()
        elif config.EXIST_BDC and not config.EXIST_PDC:
            check.Hazard_Inactive_Is()

        simva.wait(config.DELAY_10MS)

    check.BAlarmState_ALARM_Keeps()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_256_1():

    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return

    precondition.Precondition_BAlarm_ALARM()
    method.All_Close()
    method.All_Door_Knob_SW_Lock()
    simva.set_signal(signals.BDC.E_SMK_RKECMD, 2)

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=2, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=2, hazard_on_sec=0.5, hazard_off_sec=0.5)

    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results(series["buzzer"], expected_count=2, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
    
    acquisition.pulse_results_delay(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF, delay_sec=0.05) 

    check.BAlarmState_AUTOLOCKTIMER1_Turns()

    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Unlock_BTN_OFF)
    simva.wait(config.DELAY_100MS)
    method.All_Door_Knob_SW_Unlock()
    simva.wait(config.DELAY_2SEC)
    
    if config.EXIST_BDC and not config.EXIST_PDC:
        check.Hazard_Inactive_Turns(config.DELAY_2SEC)
        check.Hazard_Inactive_Keeps(config.DELAY_5SEC)
    
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_258_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM()
    method.DRV_Door_Close()
    method.All_Door_Knob_SW_Lock()
    method.Passive_Lock_BTN_Press_On()
    
    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=2, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=2, hazard_on_sec=0.5, hazard_off_sec=0.5)
    if (simva.get_signal(signals.BDC.E_EOL_DrHdl) in [q.EOL_DoorHandleButton_Toggle, q.EOL_DoorHandleButton_ToggleTouch] and
            simva.get_signal(signals.BDC.E_EOL_Country) not in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]):
        acquisition.pulse_results(series["buzzer"], expected_count=2, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
    
    acquisition.pulse_results_delay(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF, delay_sec=0.05)
    
    check.BAlarmState_AUTOLOCKTIMER1_Turns()
    method.Passive_Lock_BTN_Press_Off()
    method.All_Door_Knob_SW_Unlock()
    simva.wait(config.DELAY_2SEC)

    if config.EXIST_BDC and config.EXIST_PDC:
        acquisition.Hazard_Off_Turns()
        check.Hazard_Off_Keeps(config.DELAY_2SEC)
    elif config.EXIST_BDC and not config.EXIST_PDC:
        check.Hazard_Inactive_Turns(config.DELAY_2SEC)
        check.Hazard_Inactive_Keeps(config.DELAY_2SEC)
    
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_260_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_Hood()
    simva.wait(config.DELAY_1SEC)
    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Unlock_BTN_ON)

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=2, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=2, hazard_on_sec=0.5, hazard_off_sec=0.5)
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results(series["buzzer"], expected_count=2, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 

    acquisition.pulse_results_delay(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF, delay_sec=0.05)
    
    check.BAlarmState_AUTOLOCKTIMER2_Turns()
    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Unlock_BTN_OFF)
    method.All_Door_Knob_SW_Unlock()
    simva.wait(config.DELAY_2SEC)

    if config.EXIST_BDC and config.EXIST_PDC:
        acquisition.Hazard_Off_Turns()
        check.Hazard_Off_Keeps(config.DELAY_2SEC)
    elif config.EXIST_BDC and not config.EXIST_PDC:
        check.Hazard_Inactive_Turns(config.DELAY_2SEC)
        check.Hazard_Inactive_Keeps(config.DELAY_2SEC)
    
    cleanup.CleanUp_BAlarm()


def BAlarm_Func_TGate_262_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return

    precondition.Precondition_BAlarm_ALARM_DRV()
    
    if simva.get_signal(signals.BDC.E_EOL_Country) in [q.DOMESTIC, q.CANADA, q.USA]:
        series = acquisition.acquire_hazard_horn(horn_expected_count = 7, horn_on_sec = 1, horn_off_sec = 1, 
                        hazard_expected_count = 7, hazard_on_sec = 1, hazard_off_sec = 1)
        acquisition.pulse_results(series["horn"], expected_count=7, on_sec=1, off_sec=1,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=7, on_sec=1, off_sec=1,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
        
        method.DRV_Door_Close(False)

        series = acquisition.acquire_hazard_horn(horn_expected_count = 7, horn_on_sec = 1, horn_off_sec = 1, 
                        hazard_expected_count = 7, hazard_on_sec = 1, hazard_off_sec = 1)

        acquisition.pulse_results(series["horn"], expected_count=7, on_sec=1, off_sec=1,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=7, on_sec=1, off_sec=1,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)

        simva.wait(config.DELAY_10SEC)
        simva.wait(config.DELAY_200MS)

        series = acquisition.acquire_hazard_horn(horn_expected_count = 14, horn_on_sec = 1, horn_off_sec = 1, 
                        hazard_expected_count = 14, hazard_on_sec = 1, hazard_off_sec = 1)

        acquisition.pulse_results(series["horn"], expected_count=14, on_sec=1, off_sec=1,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=14, on_sec=1, off_sec=1,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)

    if simva.get_signal(signals.BDC.E_EOL_Country) == q.EUROPE:
        series = acquisition.acquire_hazard_horn(horn_expected_count = 10, horn_on_sec = 0.45, horn_off_sec = 0.45, 
                        hazard_expected_count = 10, hazard_on_sec = 0.45, hazard_off_sec = 0.45)

        acquisition.pulse_results(series["horn"], expected_count=10, on_sec=0.45, off_sec=0.45,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=10, on_sec=0.45, off_sec=0.45,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
        
        method.DRV_Door_Close(False)

        series = acquisition.acquire_hazard_horn(horn_expected_count = 20, horn_on_sec = 0.45, horn_off_sec = 0.45, 
                        hazard_expected_count = 20, hazard_on_sec = 0.45, hazard_off_sec = 0.45)

        acquisition.pulse_results(series["horn"], expected_count=20, on_sec=0.45, off_sec=0.45,
                                  key=signals.BDC.BAlarm_BrglrHrnRlySta_BCAN1, name="Horn",
                                  on_value=q.Horn_ON, off_value=q.Horn_OFF)
        acquisition.pulse_results(series["hazard"], expected_count=20, on_sec=0.45, off_sec=0.45,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF)
        
        simva.wait(config.DELAY_1500MS)

        for _ in range(0, 150):
            check.Horn_Off_Is()
            if config.EXIST_BDC and config.EXIST_PDC:
                check.Hazard_Off_Is()
            elif config.EXIST_BDC and not config.EXIST_PDC:
                check.Hazard_Inactive_Is()
            simva.wait(config.DELAY_10MS)
        
        check.BAlarmState_REARM_Turns()
        cleanup.CleanUp_BAlarm()


def BAlarm_Func_TGate_264_1():
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.DOMESTIC, q.CANADA, q.USA]:
        return
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_Hood()
    method.Hood_SW_Off()

    acquisition.BAlarm_On_Cycle1()
    simva.wait(4)
    method.DRV_Door_Open()

    if config.EXIST_BDC and config.EXIST_PDC:
        check.Hazard_Off_Keeps(4)
    elif config.EXIST_BDC and not config.EXIST_PDC:
        check.Hazard_Inactive_Keeps(4)
    
    simva.wait(0.6)
    acquisition.BAlarm_On_Cycle1()
    simva.wait(config.DELAY_1500MS)

    for i in range(0, 150):
        check.Horn_Off_Is()
        if config.EXIST_BDC and config.EXIST_PDC:
            check.Hazard_Off_Is()
        elif config.EXIST_BDC and not config.EXIST_PDC:
            check.Hazard_Inactive_Is()
        
        simva.wait(config.DELAY_10MS)

    check.BAlarmState_ALARM_Turns()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_TGate_265_1():
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.DOMESTIC, q.CANADA, q.USA]:
        return
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_Hood()
    method.Hood_SW_Off()
    acquisition.BAlarm_On_Cycle1()

    simva.wait(config.DELAY_4SEC)
    method.Trunk_SW_On()

    if config.EXIST_BDC and config.EXIST_PDC:
        check.Hazard_Off_Keeps(4)
    elif config.EXIST_BDC and not config.EXIST_PDC:
        check.Hazard_Off_Keeps(4)
    
    simva.wait(0.6)
    acquisition.BAlarm_On_Cycle1()
    simva.wait(config.DELAY_1500MS)

    for i in range(0, 150):
        check.Horn_Off_Is()
        if config.EXIST_BDC and config.EXIST_PDC:
            check.Hazard_Off_Is()
        elif config.EXIST_BDC and not config.EXIST_PDC:
            check.Hazard_Inactive_Is()
        
        simva.wait(config.DELAY_10MS)

    check.BAlarmState_ALARM_Turns()
    cleanup.CleanUp_BAlarm()


def BAlarm_Func_Frunk_230_1_2():

    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ARM()
    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Unlock_BTN_ON)
    method.AST_Door_Open(False)

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=2, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=2, hazard_on_sec=0.5, hazard_off_sec=0.5)

    if simva.get_signal(signals.BDC.E_EOL_Country) in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF) 
    else:
        acquisition.pulse_results(series["buzzer"], expected_count=2, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
        acquisition.pulse_results(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF) 

    check.BAlarmState_DISARM_Turns()

    cleanup.CleanUp_BAlarm()


def BAlarm_Func_TGate_266_1():
    if simva.get_signal(signals.BDC.E_EOL_Country) not in [q.DOMESTIC, q.CANADA, q.USA]:
        return
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ALARM_Hood()
    method.Hood_SW_Off()
    acquisition.BAlarm_On_Cycle1()
    simva.wait(config.DELAY_4SEC)
    method.Hood_SW_On()

    if config.EXIST_BDC and config.EXIST_PDC:
        check.Hazard_Off_Keeps(config.DELAY_4SEC)
    elif config.EXIST_BDC and not config.EXIST_PDC:
        check.Hazard_Inactive_Keeps(config.DELAY_4SEC)
    
    simva.wait(config.DELAY_600MS)
    acquisition.BAlarm_On_Cycle1()
    simva.wait(config.DELAY_1500MS)

    for _ in range(0, 150):
        check.Horn_Off_Is()
        if config.EXIST_BDC and config.EXIST_PDC:
            check.Hazard_Off_Is()
        elif config.EXIST_BDC and not config.EXIST_PDC:
            check.Hazard_Inactive_Is()
        simva.wait(config.DELAY_10MS)
    
    check.BAlarmState_ALARM_Turns()
    cleanup.CleanUp_BAlarm()

def BAlarm_Func_Frunk_224_1():
    if simva.get_signal(signals.BDC.E_EOL_TrunkTg) == q.EOL_Trunk_Type_TRUNK:
        return
    
    precondition.Precondition_BAlarm_ARM()
    simva.set_signal(signals.BDC.E_SMK_RKECMD, q.RKE1_Unlock_BTN_ON)

    series = acquisition.acquire_buzzer_hazard(buzzer_expected_count=2, buzzer_on_sec=0.01, buzzer_off_sec=0.19,hazard_expected_count=2, hazard_on_sec=0.5, hazard_off_sec=0.5)

    if simva.get_signal(signals.BDC.E_EOL_Country) in [q.EUROPE, q.COMMON, q.MIDDLE_EAST]:
        acquisition.pulse_results_delay(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF, delay_sec=0.05)
    else:
        acquisition.pulse_results(series["buzzer"], expected_count=2, on_sec=0.01, off_sec=0.19,
                                  key=signals.BDC.Pwm_P_ExternalBuzzer_OUT, name="Buzzer",
                                  on_value=q.Buzzer_ON, off_value=q.Buzzer_OFF) 
        acquisition.pulse_results_delay(series["hazard"], expected_count=2, on_sec=0.5, off_sec=0.5,
                                  key=signals.BDC.Lamp_HiPrioHzrdReq_BCAN1, name="Hazard",
                                  on_value=q.Hazard_ON, off_value=q.Hazard_OFF, delay_sec=0.05)
    
    check.BAlarmState_AUTOLOCKTIMER1_Turns()
    cleanup.CleanUp_BAlarm()
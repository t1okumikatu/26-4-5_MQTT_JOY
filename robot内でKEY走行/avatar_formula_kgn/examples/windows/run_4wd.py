import msvcrt
from time import sleep, time
import argparse
import sys
import pathlib
import serial
import serial.tools.list_ports
import math


current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir) + '/../../') # give 1st priority to the directory where pykeigan exists

from pykeigan import uartcontroller
from pykeigan import utils


def select_port():
    print('Available COM ports list')

    portlist = serial.tools.list_ports.comports()

    if not portlist:
        print('No available port')
        sys.exit()

    print('i : name')
    print('--------')
    for i, port in enumerate(portlist):
        print(i, ':', port.device)

    print('- Enter the port number (0~)')
    portnum = input()
    portnum = int(portnum)

    portdev = None
    if portnum in range(len(portlist)):
        portdev = portlist[portnum].device

    print('Conncted to', portdev)
    print('--------')

    return portdev


# ログ情報callback
def on_motor_log_cb(device_id, log):
    print("[ID:",device_id,'] log {} '.format(log))
    error = log['error_codes']
    if error == 0x0: 
        # print('Command Success')
        pass
    elif error == 0x14: 
        print('\n***** Motor is Disabled. Please do enable_action(). *****\n')
    elif error == 0x06: 
        print('\n***** Invalid parameter *****\n')


# モーター回転情報callback
def on_motor_measurement_cb(device_id, measurement):
    #meas = "\r[",device_id,']{} '.format(measurement)
    #print(meas, end="")
    meas = device_id , '{} '.format(measurement)
    t = measurement['motor_time']
    isEnabled = measurement['isEnabled']
    mode = measurement['mode']
    #temp = measurement['temperature']
    drv_fault = measurement['drv_fault']
    position = measurement['position']
    degree = round(utils.rad2deg(position), 1)
    #ext_pos = measurement['ext_position']
    velocity = measurement['velocity']
    rpm = round(utils.rad_per_sec2rpm(velocity), 1)
    torque = round(measurement['torque'], 2)
    # print(meas)
    print("id, time, enabled, mode, drv_fault, inEnc[degree], vel[rpm], trq[Nm] = ", device_id, t, isEnabled, mode, drv_fault, degree, rpm, torque)
    


def pos_test(ids_array, rpm, degree):
    dev.enable_action_sync(ids_array)

    rps = utils.rpm2rad_per_sec(rpm)

    rps_array = []

    for id in ids_array:
        rps_array.append(rps)

    dev.set_speed_sync(ids_array, rps_array)

    # 減速機設定
    gear_ratio = -51 # 減速比（モーターと出力方向は逆）

    rad = utils.deg2rad(gear_ratio*degree)

    rad_array = []

    for id in ids_array:
        rad_array.append(rad)

    print(ids_array, rad_array)

    # 相対位置
    dev.move_by_dist_sync(ids_array, rad_array)
    

def motor_config(dev, ids):
    dev.set_qcurrent_p_sync(ids, [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2])
    dev.set_qcurrent_i_sync(ids, [1, 1, 1, 1, 1, 1, 1, 1])
    dev.set_max_torque_sync(ids, [4,4,4,4,4,4,4,4])
    #dev.set_max_torque_sync(ids, [6,6,6,6,6,6,6,6])
    #dev.set_max_torque(id_a, 1.0)
    dev.set_speed_p_sync(ids, [10,10,10,10,10,10,10,10])
    #dev.set_position_p(id_a, 2.0)
    dev.set_position_p_sync(ids, [5,5,5,5,5,5,5,5])
    dev.set_position_i_sync(ids, [10,10,10,10,10,10,10,10])


gear_ratio = -21

def run_straight(dev, ids, rpm):
    rps = utils.rpm2rad_per_sec(rpm*gear_ratio)
    #dev.run_at_velocity_sync(ids, [-rps, -rps, rps, rps])
    #dev.run_at_velocity(4, rps)
    dev.run_at_velocity_sync([1, 2, 3], [-rps, -rps, rps])
    #rps = utils.rpm2rad_per_sec(rpm*gear_ratio)
    #dev.run_at_velocity_sync([2, 4], [-rps, rps])

def turn_in_place(dev, ids, rpm):
    rps = utils.rpm2rad_per_sec(rpm*gear_ratio)
    dev.run_at_velocity_sync(ids, [rps, rps, rps, rps])

def rotation(dev, ids, rpm, ratio):
    rps = utils.rpm2rad_per_sec(rpm*gear_ratio)
    dev.run_at_velocity_sync(ids, [-rps, -rps, rps*ratio, rps*ratio])

def enable_all(dev, ids):
    dev.enable_action_sync(ids)
    #dev.enable_action_sync([2, 4])

def disable_all(dev, ids):
    dev.disable_action_sync(ids)


# Select port connecting to KeiganMotor
dev = uartcontroller.UARTController(select_port())
dev.on_motor_measurement_value_cb = on_motor_measurement_cb
dev.on_motor_log_cb = on_motor_log_cb

# 負荷、電圧など条件により最適化必要
# max_torque は位置決め時間、ハンチングにも影響（大きいほど良好）
# motor_measurement における torque は暫定仕様として、電流値 [A] をそのまま吐き出している（係数1）
# 減速機を取り付けた状態で、測定 torque が 0.1 以上での継続運転は、避けて下さい。出力軸トルクが 5Nm を越えるため、破損につながります。

# 1: 左前, 2: 左後, 3:右前, 4:右後
ids = [1, 2, 3, 4]

# motor_config(dev, ids)

gear_ratio = -21

dev.set_max_torque_sync(ids, [10,10,10,10])
dev.set_speed_p_sync(ids, [14,14,14,14])
dev.set_qcurrent_p_sync(ids, [0.2, 0.2, 0.2, 0.2])
dev.set_qcurrent_i_sync(ids, [2.0, 2.0, 2.0, 2.0])

print('run 4wd example')


if __name__ == '__main__':
    try:
        while True:
            dev.read_motor_measurement_sync(ids)
            sleep(0.1)
            
            if msvcrt.kbhit():
                c = msvcrt.getwch()
                print(c)

                if c == 'r': # 速度制御
                    enable_all(dev, ids)
                    run_straight(dev, ids, 40)

                elif c == 's': # 速度制御
                    enable_all(dev, ids)
                    run_straight(dev, ids, -40)

                elif c == 't': # 旋回
                    enable_all(dev, ids)
                    turn_in_place(dev, ids, 30)

                elif c == 'u': # 旋回
                    enable_all(dev, ids)
                    turn_in_place(dev, ids, -30)

                elif c == 'p': # 
                    enable_all(dev, ids)
                    rotation(dev, ids, 20, 0.6)

                elif c == 'e': # ディスエーブル
                    disable_all(dev, ids)
                

              
            


    except KeyboardInterrupt:
        if dev:
            dev.disable_action_sync(ids)             

        print('Ctrl-C')

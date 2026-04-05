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


def select_current_id():
    print('Select the current driver ID (Address)')
    print('- Enter the number (1~255) as driver ID (default id is 1)')
    id = input()
    id = int(id)
    return id

def select_new_id():
    print('Select the new driver ID (Address)')
    print('- Enter the number (1~255) as driver ID (default id is 1)')
    id = input()
    id = int(id)
    return id

def select_gear_ratio():
    print('Set the gear ratio to write')
    r = input()
    r = int(r)
    return r


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

    return portdev


# ログ情報callback
def on_motor_log_cb(device_id, log):
    print("[ID:",device_id,'] log {} '.format(log))
    if log['error_codes'] == 0: print('Command Success')


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
    #print(meas)
    print("id, time, enabled, mode, drv_fault, inEnc[degree], vel[rpm], trq[Nm] = ", device_id, t, isEnabled, mode, drv_fault, degree, rpm, torque)
    

def scan_device_id():
    global dev
    for i in range(1,16):
        resp = dev.read_device_id(i)
        if resp == i: 
            print("Scan Device id: ", i, " -->  found: True", dev.read_device_info(i))
        else:
            print("Scan Device id: ", i, " -->  found: False")

    if 0xFF == dev.read_device_id(0xFF):
        print("Device ID is 0xFF")

        sleep(0.05)



# sin曲線 位置制御を定期実行（外部エンコーダベース）
def sine_wave(id):
    # sine wave / 正弦波諸元
    period = 10 # 周期 [s]
    ampDegree = 90 # 振幅 [degree]
    t = 0 
    res = 0.03 # 時間分解能 [s]
    centerDeg = 90
    cnt = 1
    index = 0
    while True:
        theta = t * 2 * math.pi / period
        #print(cnt, theta)
        cnt += 1
        deg = centerDeg + ampDegree * math.sin(theta)
        print('degree:      ', deg)
        target = utils.deg2rad(deg)

        ## 単体制御
        #dev.move_to_ext_pos(1, target)
        #dev.read_motor_measurement(1)
        #print(time.time())

        
        gear_ratio = 50
        cnt = 0
        dev.move_to_pos(id, target*gear_ratio)
        

        ## 全体制御
        # for id in id_list:
        #     index_bytes = utils.uint16_t2bytes(index)
        #     print(id, 'tx', time.time(), index)
        #     dev.move_to_ext_pos(id, target)
            #dev.move_to_ext_pos_blocking(id, target, identifier=index_bytes)
            #sleep(0.002)
        index += 1
        if index > 65535:
            index = 0
        #print(target)
        #sleep(res-0.005)
        sleep(res-0.01)
        #read_measurement()
        t += res



# Select port connecting to KeiganMotor
dev = uartcontroller.UARTController(select_port())
dev.on_motor_measurement_value_cb = on_motor_measurement_cb
dev.on_motor_log_cb = on_motor_log_cb

# デバイスIDをスキャンする（アクチュエータが見つかった場合のみレスポンスが true）
scan_device_id()

# 現在のデバイスIDを入力する
id_a = select_current_id()

id_a_new = select_new_id()


ids = [1, 2, 3, 4, 5, 6, 7, 8]

# dev.set_speed(id_a, utils.rpm2rad_per_sec(1000))
# dev.set_qcurrent_p_sync(ids, [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2])
# dev.set_qcurrent_i_sync(ids, [2, 2, 2, 2, 2, 2, 2, 2])
# #dev.set_curve_type_sync(ids, [0, 0, 0, 0, 0, 0, 0, 0])
# dev.set_max_torque(id_a, 6.0)
# #dev.set_max_torque(id_a, 1.0)
# dev.set_speed_p(id_a, 10)
# #dev.set_position_p(id_a, 2.0)
# dev.set_position_p(id_a, 5)
# dev.set_position_i(id_a, 10)

print('q current p gain', dev.read_qcurrent_p(id_a))
print('q current i gain', dev.read_qcurrent_i(id_a))
#dev.set_max_torque(id_a, 2) # 最大トルク（電流）
dev.set_pos_control_threshold(id_a, utils.deg2rad(90)) # PID制御を有効にする目標値との角度の差 [radians]
#dev.set_position_p(id_a, 3.0) # 位置Pゲイン
#dev.set_position_i(id_a, 20.0) # 位置Iゲイン


print('Device info is ', dev.read_device_info(id_a))
# print('Gear ratio is ', dev.read_gear_ratio(id_a))

print("Enter d to set new driver ID. Change from: ", id_a, " to : ", id_a_new)


if __name__ == '__main__':
    try:
        while True:
            # デバイスの測定値を取得
            dev.read_motor_measurement(id_a)
            sleep(0.1)

            #dev.move_to_ext_pos_sync(7, [0, 0, 0, 0, 0, 0, 1])
            #sleep(5)
            
            if msvcrt.kbhit():
                c = msvcrt.getwch()
                print(c)

                if c == 'd':
                    # ドライバIDを変更し、フラッシュに保存する, save_all_registers() 不要
                    dev.set_device_id(id_a, id_a_new)
                    id_a = id_a_new

                elif c == 'f':
                    # factory setting
                    dev.set_motor_model(id_a, 'M4018') # 2023年 STEP2 版

                elif c == 'a':
                    # factory setting
                    dev.set_motor_model(id_a, 'M4820') # 2022年 STEP1 版

                elif c == 'b':
                    # factory setting
                    dev.set_motor_model(id_a, 'M4625') 

                elif c == 'c':
                    # factory setting
                    dev.set_motor_model(id_a, 'M6829') 

                # elif c == 'b':
                #     # ギヤ比を 50 に設定
                #     dev.set_gear_ratio(id_a, 50)

                elif c == 'z':
                    # Scan driver id
                    scan_device_id()  

                elif c == 'r':
                    # 速度制御のテスト
                    #dev.enable_action_sync(ids)
                    dev.set_max_torque(id_a, 6.5)
                    dev.set_qcurrent_p(id_a, 0.05)
                    dev.set_speed_p(id_a, 14)
                    dev.enable_action(id_a)
                    # dev.set_speed_p(id_a, 10)
                    rps = utils.rpm2rad_per_sec(1000)
                    dev.run_at_velocity(id_a, rps)
                    #dev.run_at_velocity_sync(ids, [rps, rps, rps, rps, rps, rps, rps, rps])
                
                elif c == 's':
                    # 速度制御のテスト
                    dev.enable_action_sync(ids)
                    #dev.set_speed_p(id_a, 10)
                    #dev.set_safe_run_settings(id_a, True, 300, 1)
                    rps = utils.rpm2rad_per_sec(1000)
                    dev.run_at_velocity(id_a, -rps)
                    #dev.run_at_velocity_sync(ids, [-rps, -rps, -rps, -rps, -rps, -rps, -rps, -rps])

                elif c == 'p':
                    # 位置制御のテスト
                    gear_ratio = -51
                    dev.enable_action(id_a)
                    #dev.set_max_torque(id_a, 4.0)
                    #dev.set_max_torque(id_a, 1.0)
                    dev.set_qcurrent_p(id_a, 0.1)
                    dev.set_qcurrent_i(id_a, 2)
                    dev.set_max_torque(id_a, 50.0)
                    dev.set_speed_p(id_a, 14)
                    #dev.set_position_p(id_a, 2.0)
                    dev.set_position_p(id_a, 3)
                    dev.set_position_i(id_a, 5)
                    dev.set_speed(id_a, utils.rpm2rad_per_sec(100))
                    dev.move_by_dist(id_a, utils.deg2rad(15*gear_ratio))

                elif c == 'q':
                    # 位置制御のテスト
                    gear_ratio = -51
                    dev.enable_action(id_a)
                    #dev.set_max_torque(id_a, 4.0)
                    #dev.set_max_torque(id_a, 1.0)
                    dev.set_speed_p(id_a, 10)
                    #dev.set_position_p(id_a, 2.0)
                    dev.set_position_p(id_a, 5)
                    dev.set_position_i(id_a, 10)
                    dev.set_speed(id_a, utils.rpm2rad_per_sec(100))
                    dev.move_by_dist(id_a, utils.deg2rad(-15*gear_ratio))


                elif c == 'l':
                    dev.set_max_torque(id_a, 0.02)
                    dev.set_speed(id_a, utils.rpm2rad_per_sec(100))
                    dev.set_position_p(id_a, 1.0)
                    # dev.set_pos_control_threshold(id, utils.deg2rad(0.01)) 
                    #dev.set_speed_p(id_a, 14)
                    # dev.set_qcurrent_i = 5
                    # dev.set_qcurrent_p = 0.05

                elif c == 'e':
                    dev.disable_action_sync(ids)

                elif c == 'x':
                    # 外部エンコーダベースの位置制御テスト
                    dev.enable_action(id_a)
                    dev.set_speed(id_a, utils.rpm2rad_per_sec(1000))
                    #dev.set_gear_ratio(id_a, 50.0)
                    dev.move_to_ext_pos(id_a, utils.deg2rad(90)) # 1.57

                elif c == 'y':
                    # 外部エンコーダベースの位置制御テスト
                    dev.enable_action(id_a)
                    dev.set_speed(id_a, utils.rpm2rad_per_sec(1000))
                    #dev.set_gear_ratio(id_a, 50.0)
                    dev.move_to_ext_pos(id_a, utils.deg2rad(0))
                    #ext_pos = dev.motor_measurement_value['ext_position']
                    #dev.move_to_ext_pos(id_a, ext_pos + utils.deg2rad(90))

                elif c == 'g':
                    # 外部エンコーダベースの位置制御テスト
                    dev.enable_action(id_a)
                    dev.set_speed(id_a, utils.rpm2rad_per_sec(1000))
                    #dev.set_gear_ratio(id_a, 50.0)
                    dev.move_to_ext_pos(id_a, utils.deg2rad(180))
                    #ext_pos = dev.motor_measurement_value['ext_position']
                    #dev.move_to_ext_pos(id_a, ext_pos - utils.deg2rad(90))

                elif c == 'h':
                    # 現在の位置を外部エンコーダの原点とみなす
                    dev.preset_ext_position(id_a, 0)

                elif c == 'i':
                    dev.reset_register(id_a, 0x5C)
                
                elif c == 'k':
                    # 保存して再起動
                    dev.save_all_registers(id_a)
                    dev.reboot(id_a)

                elif c == 'j':
                    dev.reset_all_registers(id_a)
                    dev.save_all_registers(id_a)
                    dev.reboot(id_a)

                elif c == 'w':
                    sine_wave(id_a)





    except KeyboardInterrupt:
        if dev:
            dev.disable_action_sync(ids)
        print('Ctrl-C')

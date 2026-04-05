import msvcrt
from time import sleep, time
import argparse
import sys
import pathlib
import serial
import serial.tools.list_ports


current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir) + '/../../') # give 1st priority to the directory where pykeigan exists

from pykeigan import uartcontroller
from pykeigan import utils


def select_id():
    print('Set driver ID (Address) to handle')
    print('- Enter the number (1~255) as driver ID (default id is 1)')
    id = input()
    id = int(id)
    return id


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
    temp = measurement['temperature']
    position = measurement['position']
    ext_pos = measurement['ext_position']
    velocity = measurement['velocity']
    torque = measurement['torque']
    # print(meas)
    print("id, time, enabled, mode, tempC, inEnc[rad], exEnc[rad], vel[rad/s], trq[Nm] = ", device_id, t, isEnabled, mode, temp, position, ext_pos, velocity, torque)
    

def read_pid_settings():
    global dev, id_a
    print('\rread_pid_settings of driver ID: ', id_a)
    qCurrentP = dev.read_qcurrent_p(id_a)
    qCurrentI = dev.read_qcurrent_i(id_a)
    qCurrentD = dev.read_qcurrent_d(id_a)
    speedP = dev.read_speed_p(id_a)
    speedI = dev.read_speed_i(id_a)
    speedD = dev.read_speed_d(id_a)
    positionP = dev.read_position_p(id_a)
    positionI = dev.read_position_i(id_a)
    positionD = dev.read_position_d(id_a)
    threshold = dev.read_pos_control_threshold(id_a)
    print('-------')
    print('qCurrent gain P: ',qCurrentP)
    print('qCurrent gain I: ',qCurrentI)
    print('qCurrent gain D: ',qCurrentD)
    print('speed    gain P: ',speedP)
    print('speed    gain I: ',speedI)
    print('speed    gain D: ',speedD)
    print('position gain P: ',positionP)
    print('position gain I: ',positionI)
    print('position gain D: ',positionD)
    print('position PID threshold [rad]: ', threshold)
    print('position PID threshold [deg]: ', utils.rad2deg(threshold))
    print('-------')

# def set_pid_settings():
#     global dev, id_a
#     dev.set_qcurrent_d

def scan_device_id():
    global dev
    for i in range(1,33):
        resp = dev.read_device_id(i)
        found = False
        if resp == i: found = True 
        print("Scan Driver id: ", i, " --> found: ", found)
        sleep(0.05)
    found = False
    resp = dev.read_device_id(255)
    if resp == 255: found = True
    print("Scan Driver id: ", 255, " --> found: ", found)


# Select port connecting to KeiganMotor
dev = uartcontroller.UARTController(select_port())
dev.on_motor_measurement_value_cb = on_motor_measurement_cb
dev.on_motor_log_cb = on_motor_log_cb

scan_device_id()

id_a = select_id()
gear_ratio = -20

# 負荷、電圧など条件により最適化必要
# max_torque は位置決め時間、ハンチングにも影響（大きいほど良好）
# motor_measurement における torque は暫定仕様として、電流値 [A] をそのまま吐き出している（係数1）
# 減速機を取り付けた状態で、測定 torque が 0.1 以上での継続運転は、避けて下さい。出力軸トルクが 5Nm を越えるため、破損につながります。

#dev.set_max_torque(id_a, 0.2)
# dev.set_speed_p(id_a, 0.1)
#dev.set_position_p(id_a, 3)
# verified_id = dev.read_device_id(id_a)
# print("Driver id is ", verified_id)
#dev.enable_action(id_a)

if __name__ == '__main__':
    try:
        while True:
            dev.read_motor_measurement(id_a)
            #dev.read_motor_measurement(id_b)
            sleep(0.02)
            
            if msvcrt.kbhit():
                c = msvcrt.getwch()
                print(c)

                if c == 'd':
                    dev.set_device_id(id_a, 1)
                elif c == 'r':
                    dev.reset_all_registers(id_a)
                elif c == 's':
                    dev.save_all_registers(id_a)
                elif c == 'l':
                    dev.set_led(id_a, 1, 1, 0, 1)
                elif c == 'p':
                    # Read PID parameters
                    read_pid_settings()
                elif c == 'f':
                    dev.set_motor_model(id_a, 'M4018')
                elif c == 'z':
                    # Scan driver id
                    scan_device_id()
                elif c == 't':
                    # test
                    dev.enable_action(id_a)
                    dev.run_at_velocity(id_a, utils.rpm2rad_per_sec(gear_ratio*50))
                    #dev.run_at_velocity(id_a, utils.rpm2rad_per_sec(50))
                    # sleep(10)
                    # dev.run_at_velocity(id_a, utils.rpm2rad_per_sec(-gear_ratio*50))
                    # sleep(10)
                    # dev.disable_action(id_a)
                elif c == 'q':
                     # test
                    dev.enable_action(id_a)  
                    dev.set_speed(id_a, utils.rpm2rad_per_sec(abs(gear_ratio*100)))
                    dev.move_by_dist(id_a, utils.deg2rad(gear_ratio * 90))
                    sleep(3)
                    dev.move_by_dist(id_a, utils.deg2rad(gear_ratio * -90))   
                elif c == 'h':
                    # test
                    dev.enable_action(id_a)  
                    dev.set_speed(id_a, utils.rpm2rad_per_sec(abs(gear_ratio*100)))
                    dev.move_to_pos(id_a, 0)
                    sleep(10)
                    dev.move_to_pos(id_a, 10000)     
                elif c == 'e':
                    dev.disable_action(id_a)
                elif c == 'k':
                    dev.enable_action(id_a)         
                

    except KeyboardInterrupt:
        if dev:
            dev.disable_action(id_a)
        print('Ctrl-C')

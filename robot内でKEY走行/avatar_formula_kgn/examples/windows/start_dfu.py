import msvcrt
from time import sleep, time
import argparse
import sys
import pathlib
import serial
import serial.tools.list_ports
import subprocess
import os

current_dir = pathlib.Path(__file__).resolve().parent
print(current_dir)
sys.path.insert(0, str(current_dir) + '/../../') # give 1st priority to the directory where pykeigan exists

from pykeigan import uartcontroller
from pykeigan import utils

"""
本プログラムは、pykeigan_motor_2pre ディレクトリから実行して下さい
"""


def terminate():
    print('Please enter "y" and "return" key to continue firmware update')
    if input() == 'y':
        print('firmware/pkg.zip へアップデートを開始します')
        return
    else:
        sys.exit("中断しました")



def select_id():
    print('Select the driver ID (Address) to update')
    print('- Enter the number (1~255) as driver ID (default id is 1)')
    id = input()
    id = int(id)
    return id

def scan_device_id():
    global dev
    for i in range(1,16):
        resp = dev.read_device_id(i)
        if resp == i: 
            print("Scan Device id: ", i, " -->  found: True", dev.read_device_info(i))
        else:
            print("Scan Device id: ", i, " -->  found: False")

        sleep(0.05)




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



# Select port connecting to KeiganMotor
port = select_port()
dev = uartcontroller.UARTController(port)

ids = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]

scan_device_id()

id_a = select_id()
info = dev.read_device_info(id_a)
print('Device Information: ', info)
terminate()
sleep(0.5)
dev.enter_device_firmware_update(id_a)
# ids.remove(id_a)
# dev.wait_firmware_update_sync(ids)
dev.disconnect()
# dev.serial.close()
#sleep(2.0)

current_wd = os.getcwd()
print(current_wd)

# Python3.9 の nrfutil パスを代入する。※ python 3.10 以降非対応
python39_nrfutil_path = 'C:\\Users\\avater1\\AppData\\Local\\Programs\\Python\\Python39\\Scripts\\nrfutil.exe'

subprocess.run([python39_nrfutil_path, 'dfu', 'serial', '-pkg', 'firmware/pkg.zip', '-p', port, '-b', '115200', '-fc', '0'])

dev.reset_all_registers(id_a)
dev.save_all_registers(id_a)
dev.reboot(id_a)

sys.exit("アップデートプロセス終了")

if __name__ == '__main__':
    try:
        while True:

            print("Unreachable")


    except KeyboardInterrupt:
        if dev:
            dev.disable_action(id_a)
        print('Ctrl-C')

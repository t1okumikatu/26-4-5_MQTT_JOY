#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 25 2022

@author: Takashi Tokuda (Keigan Inc.)
"""
from lib2to3.pgen2 import driver
from pykeigan import controller as base
import serial, struct, threading, atexit, time
from pykeigan.utils import *


class KeiganMotor():
    def __init__(self, uart_controller, id):
        self.device_id = id
        self.is_enabled = False
        self.mode = 0
        self_drv_fault = 0
        self.temp = 0
        self.position = 0
        self.degree = 0
        self.velocity = 0
        self.rpm = 0
        self.torque = 0
        self.firmware_version = 0



class UARTController(base.Controller):
    def __init__(self, port='/dev/ttyUSB0', debug_mode=False, baud=460800): # 115200, 230400, 250000, 460800, 921600 
        self.DebugMode = debug_mode
        self.serial_buf = b''  # []
        self.setting_values = {}
        self.motor_measurement_value = None
        self.read_serial_polling_time = 0.005
        self.__motor_log_value = None
        self.__motor_event_value = None
        self.__read_motion_value = []
        self.port = port
        #self.serial = serial.Serial(port, baud, 8, 'N', 1, None, False, True, write_timeout=0.1)
        self.serial = serial.Serial(port, baud, write_timeout=0.1, timeout=0.004) # 0.005
        self.on_motor_connection_error_cb = False
        self.on_motor_measurement_value_cb = False
        self.on_motor_log_cb = False
        self.is_check_sum_enabled = True
        self.keigan_motor = {} # KeiganMotor クラス格納辞書　{id:KeiganMotor,...}

        self.start_auto_serial_reading()

        atexit.register(self.my_cleanup)

    def is_connected(self):
        return self.serial.isOpen()

    def connect(self):
        """
        Open the USB port.
        Should be after disconnection.
        """
        self.serial.open()
        #if self.serial.is_open
        #time.sleep(2)
        #self.start_auto_serial_reading()
    
    def disconnect(self, reconnect=False):
        """
        Close the USB port.
        """
        #self.shouldReconnect = reconnect
        self.my_cleanup()
        time.sleep(0.5)
        self.serial.close()

    
    def start_debug(self):
        """
        Start to print command logs.
        """
        self.DebugMode = True

    def finish_debug(self):
        """
        Finish to print command logs.
        """
        self.DebugMode = False


    def start_auto_serial_reading(self):
        self.auto_serial_reading = True
        self.t = threading.Thread(target=self.__serial_schedule_worker)
        self.t.setDaemon(True)
        self.t.start()
        atexit.register(self.__all_done)


    def finish_auto_serial_reading(self):
        self.auto_serial_reading = False


    def __all_done(self):
        try:
            if self.t.isAlive():
                self.t.join(0.01)
                self.serial.close()
        except:
            return


    def _run_command(self, device_id, val):
        try:
            #self.serial.reset_input_buffer()
            crc_buf = calc_crc16_bytes(val)
            info_len = uint8_t2bytes(1+1+len(val)) ## device_id, info_len, val 
            tx_buf = b'\xee\xee\xaa\xaa'+uint8_t2bytes(device_id)+info_len+val+crc_buf
            #tx_buf = uint8_t2bytes(device_id)+val+crc_buf
            #print('tx_buf:', tx_buf)
            #print(list(tx_buf))
            #print(calc_crc16(tx_buf))
            self.serial.reset_input_buffer()
            self.serial.write(tx_buf)
            
            #print("send" ,tx_buf)
            time.sleep(0.01)
            #time.sleep(0.01)
            #self.__read_serial_data()
            
        except serial.SerialException as e:
            #self.reconnect()
            # There is no new data from serial port
            if (callable(self.on_motor_connection_error_cb)):              
                self.on_motor_connection_error_cb(e)
            return e
        except TypeError as e:
            # Disconnect of USB->UART occured
            #self.reconnect()
            if (callable(self.on_motor_connection_error_cb)):
                self.on_motor_connection_error_cb(e)
            return e
        except IOError as e:
            #self.reconnect()
            if (callable(self.on_motor_connection_error_cb)):
                self.on_motor_connection_error_cb(e)
            return e

    def __serial_schedule_worker(self):
        while True:
            time.sleep(self.read_serial_polling_time) # less than minimum motor measurement interval
            e_res = self.__read_serial_data()
            if e_res :  # 例外発生でスレッド停止
                self.auto_serial_reading = False
                break


    def __read_serial_data(self):
        # if not self.auto_serial_reading:
        #     return
        try:
            #print(self.serial.in_waiting, self.serial.inWaiting())
            rd = self.serial.read(self.serial.inWaiting())
        except serial.SerialException as e:
            print('serial.SerialException in __read_serial_data: ', e)
            # There is no new data from serial port
            if (callable(self.on_motor_connection_error_cb)):
                self.on_motor_connection_error_cb(e)
            return e
        except TypeError as e:
            # Disconnect of USB->UART occured
            print('TypeError in __read_serial_data: ', e)
            if (callable(self.on_motor_connection_error_cb)):
                self.on_motor_connection_error_cb(e)
            return e
        except IOError as e:
            print('IOError in __read_serial_data: ', e)
            if (callable(self.on_motor_connection_error_cb)):
                self.on_motor_connection_error_cb(e)
            return e      

        '''
        for bt in rd:
            if type(bt) is str:
                self.serial_buf.append(ord(bt))
            elif type(bt) is int:
                self.serial_buf.append(bt)

            #print bt.encode('hex')
        '''

        self.serial_buf += rd
        # ------------------------------#
        #   プリアンブル検出ロジック　
        # ------------------------------#
        #print('serial_buf', self.serial_buf, len(self.serial_buf))

        bf_len = len(self.serial_buf)
        #is_pre = False  # プリアンブル検出したか
        # if (bf_len < 10):
        #     return

        slice_idx = 0  # 抽出済みとしてバッファーから削除するインデックス
        success = False
        # if bf_len > 0: 
        #     print(bf_len, 'rx', self.serial_buf.hex())
            #print('bf_len', bf_len)

        i = 0
        last_payload_id = bf_len - 3

        while i < last_payload_id:
            #print('iter: ', i)
            # プリアンブル検出
            if self.serial_buf[i:i+4] == b'\x00\x00\xaa\xaa':
                #print('matched', i)
                
                # データ構造
                # | 0x00 | 0x00 | 0xaa | 0xaa | device_id | payload_len | data_type | cmd | value | CRC1 | CRC2 | 

                bf_len = len(self.serial_buf[i:])

                # 必要最小限の長さに満たない場合 break
                if bf_len < 11:
                    break

                #if i + 6 > last_payload_id:
                    #print("return", last_payload_id)
                #    return
                #print(i, self.serial_buf.hex())

                id = self.serial_buf[i + 4]
                cmd = self.serial_buf[i + 7]
                #print("i, id, cmd = ", i, id, cmd)
                payload_len = self.serial_buf[i + 5]

                # payload_len か計算される全体のデータ長さが想定に満たない場合 break
                if bf_len < 4 + payload_len + 2:
                    break

                payload = self.serial_buf[i + 4: i + 4 + payload_len]  # 情報バイト
        
                # if len(payload) < payload_len: 
                #     #print('less')
                #     return
                
                buf_to_validate = self.serial_buf[i + 4: i + 4 + payload_len + 2]
                slice_idx = i + 4 + payload_len + 2

                # if len(buf_to_validate) < payload_len + 2:
                #     #print('less2')
                #     return

                #print('payload', payload.hex())

                if calc_crc16(buf_to_validate) == 0:
                    success = self.__serialdataParse(payload)
                    self.serial_buf = self.serial_buf[slice_idx:]
                    i = 0
                    break
                else:
                    print('')
                    print('Invalid check sum (CRC16)')
                    #print(buf_to_validate.hex())
                    self.serial_buf = self.serial_buf[slice_idx:]
                    #self.serial_buf = self.serial_buf[bf_len:]
                    #is_pre = False
                    print("*******************************************************************")
                    #print(self.serial_buf.hex())
                    #break
                    
                if len(self.serial_buf) < 11:  
                    print('************* BREAK ************')
                    #break

                #break # while を抜ける
            i += 1
                 


    def __serialdataParse(self, payload):
        v_len = len(payload)
        device_id = bytes2uint8_t(payload[0:1])

        if device_id not in self.keigan_motor:
            self.keigan_motor[device_id] = KeiganMotor(self, device_id)

        #print(self.keigan_motor)

        datatype = bytes2uint8_t(payload[2:3])

        if datatype == 0xBE:  # command log (Error or Success information)
            cmd = bytes2uint8_t(payload[3:4])
            err_code = bytes2uint16_t(payload[4:6])
            motor_time = bytes2uint32_t(payload[6:10])
            try:
                cmd_name = self.command_names[cmd]
                #print(cmd_name)
            except KeyError:
                print('[Error info] No such command exists. cmd = ', hex(cmd))
                return True
            try:
                err_desc = self.error_codes[err_code]
                #print(err_code)
            except KeyError:
                print('[Error info] No such error_code exists. error_code = ', err_code)
                return True

            val1 = 0
            """
                0x60:"run_forward",
                0x61:"run_reverse",
                0x62:"run_at_velocity",
                0x63:"move_by_ext_dist",
                0x64:"move_to_ext_pos",
                0x65:"move_to_pos",
                0x66:"move_to_pos",
                0x67:"move_by_dist",
                0x68:"move_by_dist",
            """
            #print(payload)
            label1 = 'value1'
            label2 = 'value2'
            if cmd == 0x60 or cmd == 0x61 or cmd == 0x62 : # 速度制御
                label1 = 'velocity'
                label2 = 'torque'
                val1 = bytes2float(payload[10:14])
                val2 = bytes2float(payload[14:18])
                #val = bytes2float(rest[5:9])
            elif cmd == 0x63 or cmd == 0x64 : # 位置制御（外部エンコーダ）
                label1 = 'ext_position'
                label2 = 'torque'
                val1 = bytes2float(payload[10:14])
                val2 = bytes2float(payload[14:18])
            elif cmd == 0x65 or cmd == 0x66 or cmd == 0x67 or cmd == 0x68: # 位置制御（モーターエンコーダ）
                label1 = 'position'
                label2 = 'torque'
                val1 = bytes2float(payload[10:14])
                val2 = bytes2float(payload[14:18])
            else:
                val1 = bytes2float(payload[10:14])
                val2 = bytes2float(payload[14:18])
                #val = uint32_t2bytes(rest[5:9])
            #self.__motor_log_value={'command_names':cmd,'error_codes':err_code, 'motor_time': motor_time, 'value':val}
            self.__motor_log_value={'device_id':device_id,'command':hex(cmd),'error_codes':err_code, 'motor_time':motor_time , label1:val1, label2:val2}
            if (callable(self.on_motor_log_cb)):
                self.on_motor_log_cb(device_id, self.__motor_log_value)
            if self.DebugMode:
                print(self.__motor_log_value['command_names'],self.__motor_log_value['error_codes'])
            return True
        
        elif datatype == 0xB4:  # モーター時刻+回転情報受信 モーターFW ver 2.62
            motor_time = bytes2uint32_t(payload[3:7])
            isEnabled = payload[7]
            mode = payload[8]
            reserved1 = payload[9]
            drv_fault = payload[10]
            temp = bytes2int16_t(payload[11:13]) * 0.125 # unit is [0.125 deg]
            position = bytes2double(payload[13:21])
            ext_position = bytes2float(payload[21:25])
            velocity = bytes2float(payload[25:29])
            torque = bytes2float(payload[29:33])

            self.keigan_motor[device_id].is_enabled = isEnabled
            self.keigan_motor[device_id].mode = mode
            self.keigan_motor[device_id].drv_fault = drv_fault
            self.keigan_motor[device_id].temp = temp
            self.keigan_motor[device_id].position = position
            self.keigan_motor[device_id].degree = round(rad2deg(position), 1)
            self.keigan_motor[device_id].velocity = velocity
            self.keigan_motor[device_id].rpm = round(rad_per_sec2rpm(position), 1)
            self.keigan_motor[device_id].torque = torque 

            self.motor_measurement_value = {'motor_time': motor_time, 'isEnabled': isEnabled, 'mode': mode, 'temperature': temp, 'drv_fault': drv_fault, 'position': position, 'ext_position' : ext_position, 'velocity': velocity, 'torque': torque,
                                              'received_unix_time': time.time(), }
            if (callable(self.on_motor_measurement_value_cb)):
                self.on_motor_measurement_value_cb(device_id, self.motor_measurement_value)
            return True
       
        elif datatype == 0x40: #Register infomations TODO
            float_value_comms = [0x02, 0x03, 0x07, 0x08, 0x0E, 0x13, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20,
                                 0x21, 0x5B]
            byte_value_comms = [0xC0, 0xC3]
            comm = bytes2uint8_t(payload[3:4])

            if comm in float_value_comms:
                self.setting_values[comm] = bytes2float(payload[4:8]), time.time()
                return True
            elif comm == 0x05:
                self.setting_values[comm] = bytes2uint8_t(payload[4:5]), time.time()
                return True
            elif comm == 0x3A:
                self.setting_values[comm] = (bytes2uint8_t(payload[4:5]), bytes2uint8_t(payload[5:6]), bytes2uint8_t(payload[6:7])), time.time()
                return True                             
            elif comm == 0x46:
                self.setting_values[comm] = payload[4:].decode('utf-8'), time.time()
                return True
            elif comm == 0x47:
                self.setting_values[comm] = payload[3:].decode('utf-8'), time.time()
                return True
            elif comm in byte_value_comms:
                self.setting_values[comm] = payload[4], time.time()
                #print("self.setting_values[comm]", self.setting_values[comm])
            # elif comm == 0x9A:
            #     bits_list = [int(n) for n in bin(bytes2uint8_t(payload[3:4]))[2:].zfill(8)]
            #     self.setting_values[comm] = {"isCheckSumEnabled": bits_list[0], "iMUMeasurement": bits_list[4],
            #                                  "motorMeasurement": bits_list[5], "queue": bits_list[6],
            #                                  "motorEnabled": bits_list[7],
            #                                  "flash_memory_state": self.flash_memory_states[
            #                                      bytes2uint8_t(payload[4:5])],
            #                                  "motor_control_mode": self.motor_control_modes[
            #                                      bytes2uint8_t(payload[5:6])]}, time.time()
            #     return True
            else:
                return False
       
        else:  # Unknown data
            return False

    def _read_setting_value(self, device_id, comm, validation_threshold=0.2):#Register infomation
        float_value_comms = [0x02, 0x03, 0x07, 0x08, 0x0E, 0x13, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x21,
                             0x5B]
        valid_comms = [0x05, 0x3A, 0x46, 0x47, 0x9A, 0xC0, 0xC3]
        valid_comms.extend(float_value_comms)
        if not (comm in valid_comms):
            raise ValueError("Unknown Command")
        self.read_register(device_id, comm)
        time.sleep(0.1)
        # if not self.auto_serial_reading:
        #     raise ValueError("Disabled reading serial data. Try calling start_auto_serial_reading()")
        if comm in self.setting_values.keys():
            val, received_unix_time = self.setting_values[comm]
            if time.time() - received_unix_time < validation_threshold:
                return val
            else:
                #print("No Response within ", validation_threshold, " sec")
                return 'No Response'
                # raise ValueError("No data within ", validation_threshold, " sec")
        else:
            return 'No data'
            #raise ValueError("No data received")
            


    # def read_motor_measurement(self, device_id):
    #     self.read_register(device_id, 0xB4)
    #     time.sleep(0.003)
    #     if not self.auto_serial_reading:
    #         raise ValueError("Disabled reading serial data. Try calling start_auto_serial_reading()")


    #修了イベント　測定値のスレッドを停止する後処理
    def my_cleanup(self):
        self.finish_auto_serial_reading()

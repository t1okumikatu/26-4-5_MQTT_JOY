#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thr Feb 24 2022

@author: tokuda@keigan.co.jp
"""
import serial,struct,threading,atexit,time
from pykeigan.utils import *

class Controller:
    def __init__(self):
        pass

    def _run_command(self,device_id,val,characteristics):
        pass

    def _run_command_blocking(self,device_id,val,characteristics):
        pass

    @property
    def flash_memory_states(self):
        return {0:"FLASH_STATE_READY",1:"FLASH_STATE_TEACHING_PREPARE",2:"FLASH_STATE_TEACHING_DOING",3:"FLASH_STATE_PLAYBACK_PREPARE",4:"FLASH_STATE_PLAYBACK_DOING",5:"FLASH_STATE_PLAYBACK_PAUSING",6:"FLASH_STATE_TASKSET_RECORDING",7:"FLASH_STATE_TASKSET_DOING",8:"FLASH_STATE_TASKSET_PAUSING",20:"FLASH_STATE_IMU"}

    @property
    def motor_control_modes(self):
        return {0:"MOTOR_CONTROL_MODE_NONE",1:"MOTOR_CONTROL_MODE_VELOCITY",2:"MOTOR_CONTROL_MODE_POSITION",3:"MOTOR_CONTROL_MODE_TORQUE",0xFF:"MOTOR_CONTROL_MODE_OTHERS"}
    
    @property
    def baud_rates(self):
        return {0:"115200",1:"230400",2:"250000",3:"460800",4:"921600",5:"1000000"}

    @property
    def error_codes(self):
        return {
                0x00:"KM_SUCCESS",
                0x03:"KM_ERROR_NOT_FOUND",
                0x05:"KM_ERROR_INVALID_COMMAND",
                0x06:"KM_ERROR_INVALID_PARAM",
                0x07:"KM_ERROR_STORAGE_FULL",
                0x08:"KM_ERROR_INVALID_FLASH_STATE", 
                0x09:"KM_ERROR_INVALID_LENGTH",
                0x0A:"KM_ERROR_INVALID_CHECKSUM",
                0x0F:"KM_ERROR_FORBIDDEN",
                0x10:"KM_ERROR_INVALID_ADDR",
                0x14:"KM_ERROR_MOTOR_DISABLED",
                0x46:"KM_ERROR_NRF_DEVICE", 
                0x50:"KM_ERROR_WDT_EVENT",
                0x51:"KM_ERROR_OVER_HEAT",
                0x64:"KM_SUCCESS_ARRIVAL"
                }
    
    @property
    def command_names(self):
        return {
                0x00:"unknown",
                0x02:"set_max_speed",
                0x03:"set_min_speed",
                0x05:"set_curve_type",
                0x07:"set_acc",
                0x08:"set_dec",
                0x13:"set_gear_ratio",
                0x0e:"set_max_torque",
                0x16:"set_teaching_interval",
                0x17:"set_playback_interval",
                0x18:"set_qcurrent_p",
                0x19:"set_qcurrent_i",
                0x1A:"set_qcurrent_d",
                0x1B:"set_speed_p",
                0x1C:"set_speed_i",
                0x1D:"set_speed_d",
                0x1E:"set_position_p",
                0x1F:"set_position_i",
                0x20:"set_position_d",
                0x21:"set_pos_control_threshold",
                0x22:"reset_all_pid",
                0x23:"set_pid_table_value",
                0x24:"select_pid_table",
                0x25:"read_pid_table",
                0x27:"set_low_pass_filter",
                0x2B:"set_notify_pos_arrival_settings",
                0x2C:"set_motor_measurement_interval",
                0x2D:"set_motor_measurement_settings",
                0x2E:"set_interface",
                0x30:"set_response",
                0x31:"set_safe_run_settings",
                0x32:"set_safety_settings",
                0x33:"set_limit_current",
                0x37:"set_linkage_key",
                0x3A:"set_own_color",
                0x3C:"set_imu_measurement_interval",
                0x3D:"set_imu_measurement_settings",
                0x40:"read_register",
                0x41:"save_all_registers",
                0x46:"read_device_name",
                0x47:"read_device_info",
                0x4E:"reset_register",
                0x4F:"reset_all_registers",
                0x50:"disable_action",
                0x51:"enable_action",
                0x58:"set_speed",
                0x5A:"preset_position",
                0x5B:"get_position_offset",
                0x5C:"preset_ext_position",
                0x62:"run_at_velocity",
                0x63:"move_to_ext_pos",
                0x64:"move_by_ext_dist",
                0x65:"move_to_pos",
                0x66:"move_to_pos",
                0x67:"move_by_dist",
                0x68:"move_by_dist",
                0x6A:"enable_action_task",
                0x6B:"disable_action_task",
                0x6C:"free_motor",
                0x6D:"stop_motor",
                0x72:"hold_torque",
                0x81:"start_doing_taskset",
                0x82:"stop_doing_taskset",
                0x85:"start_playback_motion",
                0x86:"prepare_playback_motion",
                0x87:"start_playback_motion_from_prep",
                0x88:"stop_playback_motion",
                0x90:"pause_queue",
                0x91:"resume_queue",
                0x92:"wait_queue",
                0x94:"erase_task",
                0x95:"clear_queue",
                0x96:"wait_queue_until_input",
                0x98:"wait_queue_until_radio_rx_event",
                0x99:"wait_queue_until_radio_tx_event_resp",
                0x9A:"read_status",
                0xA0:"start_recording_taskset",
                0xA2:"stop_recording_taskset",
                0xA3:"erase_taskset",
                0xA4:"erase_all_tasksets",
                0xA5:"set_taskset_name",
                0xA6:"read_taskset_info",
                0xA7:"read_taskset_usage",
                0xA8:"set_trigger_taskset_settings",
                0xA9:"start_teaching_motion",
                0xAA:"prepare_teaching_motion",
                0xAB:"start_teaching_motion_from_prep",
                0xAC:"stop_teaching_motion",
                0xAD:"erase_motion",
                0xAE:"erase_all_motions",
                0xAF:"set_motion_name",
                0xB0:"read_motion_info",
                0xB1:"read_motion_usage",
                0xB2:"set_trigger_motion_settings",
                0xB4:"read_motor_measurement",
                0xB7:"read_motion",
                0xB8:"write_motion_position",
                0xBC:"set_autostart_setting",
                0xBD:"set_button_setting",
                0xBE:"read_error",
                0xC0:"set_device_id",
                0xC3:"set_baud_rate",
                0xE0:"set_led",
                0xE6:"enable_motor_measurement",
                0xE7:"disable_motor_measurement",
                0xEA:"enable_imu_measurement",
                0xEB:"disable_imu_measurement",
                0xF0:"reboot",
                0xF3:"enable_check_sum",
                0xFD:"enter_device_firmware_update"
                }
    
    @property
    def event_types(self):
        return {1:"button", 10:"gpio"}
    
    # Broadcast command
    def run_command_sync(self, device_ids_array, command, values_bytes=None):
        ids_flag = 0

        num = len(device_ids_array)

        for id in device_ids_array:
            if id > 0:
                flag_value = 1 << (id - 1)
                ids_flag |= flag_value

        #print(bin(ids_flag))
        bytes_to_send = command+uint32_t2bytes(ids_flag)
        
        if values_bytes is not None: 
            bytes_to_send = bytes_to_send + values_bytes

        self._run_command(0, bytes_to_send)
        sleep_time = max(0.030, num*0.010)
        #print(sleep_time)
        time.sleep(sleep_time)
        

    def run_command_sync_float(self, device_ids_array, command, float_array):
        if len(device_ids_array) is not len(float_array):
            print("Device ID number and values length is not matched.")
            return
        values_bytes = b''
        for val in float_array:
            values_bytes = values_bytes + float2bytes(val)
        self.run_command_sync(device_ids_array, command, values_bytes)

    def run_command_sync_uint8_t(self, command, device_ids_array, uint8_t_array):
        if len(device_ids_array) is not len(uint8_t_array):
            print("Device ID number and values length is not matched.")
            return
        values_bytes = b''
        for val in uint8_t_array:
            values_bytes += uint8_t2bytes(val)
        self.run_command_sync(device_ids_array, command, values_bytes)

    def run_command_sync_uint32_t(self, device_ids_array, command, uint32_t_array):
        if len(device_ids_array) is not len(uint32_t_array):
            print("Device ID number and values length is not matched.")
            return
        values_bytes = 0
        for val in uint32_t_array:
            values_bytes += uint32_t2bytes(val)
        self.run_command_sync(device_ids_array, command, values_bytes)


    # Settings
    def set_max_speed(self,device_id,max_speed):
        """
        Set the maximum speed of rotation to the 'max_speed' in rad/sec.
        """
        command=b'\x02'
        values=float2bytes(max_speed)
        self._run_command(device_id,command+values)

    def set_min_speed(self,device_id,min_speed):
        """
        Set the minimum speed of rotation to the 'min_speed' in rad/sec.
        """
        command=b'\x03'
        values=float2bytes(min_speed)
        self._run_command(device_id,command+values)


    def set_curve_type(self,device_id,curve_type):
        """
        Set the acceleration or deceleration curve to the 'curve_type'.
        typedef enum curveType =
        {
            CURVE_TYPE_NONE = 0, // Turn off Motion control
            CURVE_TYPE_TRAPEZOID = 1, // Turn on Motion control with trapezoidal curve
            CURVE_TYPE_DIRECT_POS = 10 // Turn off Motion control (Direct position control)
        }
        """
        command=b'\x05'
        values=uint8_t2bytes(curve_type)
        self._run_command(device_id,command+values)

    def set_curve_type_sync(self, device_ids_array, values_array):
        """
        Set the acceleration or deceleration curve to the 'curve_type'.
        typedef enum curveType =
        {
            CURVE_TYPE_NONE = 0, // Turn off Motion control
            CURVE_TYPE_TRAPEZOID = 1, // Turn on Motion control with trapezoidal curve
            CURVE_TYPE_DIRECT_POS = 10 // Turn off Motion control (Direct position control)
        }
        """
        command=b'\x05'
        self.run_command_sync_uint8_t(command,device_ids_array, values_array)


    def set_acc(self,device_id,_acc):
        """
        Set the acceleration of rotation to the positive 'acc' in rad/sec^2.
        """
        command=b'\x07'
        values=float2bytes(_acc)
        self._run_command(device_id,command+values)

    def set_acc_sync(self, device_ids_array, values_array):
        """
        Set the acceleration of rotation to the positive 'acc' in rad/sec^2.
        """
        command=b'\x07'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_dec(self,device_id,_dec):
        """
        Set the deceleration of rotation to the positive 'dec' in rad/sec^2.
        """
        command=b'\x08'
        values=float2bytes(_dec)
        self._run_command(device_id,command+values)

    def set_dec_sync(self, device_ids_array, values_array):
        """
        Set the acceleration of rotation to the positive 'acc' in rad/sec^2.
        """
        command=b'\x08'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_gear_ratio(self,device_id,ratio):
        """
        Set the reducer gear ratio
        If it increase torque double and make speed half, it should be 2.0
        """
        command=b'\x13'
        if ratio == 0:
            raise ValueError("Value out of range")
        values=float2bytes(ratio)
        self._run_command(device_id,command+values)

    def set_gear_ratio_sync(self, device_ids_array, values_array):
        """
        Set the reducer gear ratio
        If it increase torque double and make speed half, it should be 2.0
        """
        command=b'\x13'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_max_torque(self,device_id,max_torque):
        """
        Set the maximum torque to the positive 'max_torque' in N.m.
        """
        command=b'\x0E'
        if max_torque < 0:
            raise ValueError("Value out of range")
        values=float2bytes(max_torque)
        self._run_command(device_id,command+values)

    def set_max_torque_sync(self, device_ids_array, values_array):
        """
        Set the reducer gear ratio
        If it increase torque double and make speed half, it should be 2.0
        """
        command=b'\x0E'
        self.run_command_sync_float(device_ids_array, command, values_array)

    
    def set_qcurrent_p(self,device_id,q_current_p):
        """
        Set the q-axis current PID controller's Proportional gain to the postiive 'q_current_p'.
        """
        command=b'\x18'
        values=float2bytes(q_current_p)
        self._run_command(device_id,command+values)

    def set_qcurrent_p_sync(self, device_ids_array, values_array):
        """
        Set the q-axis current PID controller's Proportional gain to the postiive 'q_current_p'.
        """
        command=b'\x18'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_qcurrent_i(self,device_id,q_current_i):
        """
        Set the q-axis current PID controller's Integral gain to the positive 'q_current_i'.
        """
        command=b'\x19'
        values=float2bytes(q_current_i)
        self._run_command(device_id,command+values)

    def set_qcurrent_i_sync(self, device_ids_array, values_array):
        """
        Set the q-axis current PID controller's Integral gain to the postiive 'q_current_i'.
        """
        command=b'\x19'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_qcurrent_d(self,device_id,q_current_d):
        """
        Set the q-axis current PID controller's Differential gain to the postiive 'q_current_d'.
        """
        command=b'\x1A'
        values=float2bytes(q_current_d)
        self._run_command(device_id,command+values)

    def set_qcurrent_d_sync(self, device_ids_array, values_array):
        """
        Set the q-axis current PID controller's Differential gain to the postiive 'q_current_d'.
        """
        command=b'\x1A'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_speed_p(self,device_id,speed_p):
        """
        Set the speed PID controller's Proportional gain to the positive 'speed_p'.
        """
        command=b'\x1B'
        values=float2bytes(speed_p)
        self._run_command(device_id,command+values)

    def set_speed_p_sync(self, device_ids_array, values_array):
        """
        Set the speed PID controller's Proportional gain to the positive 'speed_p'.
        """
        command=b'\x1B'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_speed_i(self,device_id,speed_i):
        """
        Set the speed PID controller's Integral gain to the positive 'speed_i'.
        """
        command=b'\x1C'
        values=float2bytes(speed_i)
        self._run_command(device_id,command+values)

    def set_speed_i_sync(self, device_ids_array, values_array):
        """
        Set the speed PID controller's Integral gain to the positive 'speed_i'.
        """
        command=b'\x1C'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_speed_d(self,device_id,speed_d):
        """
        Set the speed PID controller's Differential gain to the positive 'speed_d'.
        """
        command=b'\x1D'
        values=float2bytes(speed_d)
        self._run_command(device_id,command+values)

    def set_speed_d_sync(self, device_ids_array, values_array):
        """
        Set the speed PID controller's Differential gain to the positive 'speed_d'.
        """
        command=b'\x1D'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_position_p(self,device_id,position_p):
        """
        Set the position PID controller's Proportional gain to the positive 'position_p'.
        """
        command=b'\x1E'
        values=float2bytes(position_p)
        self._run_command(device_id,command+values)


    def set_position_p_sync(self, device_ids_array, values_array):
        """
        Set the speed PID controller's Proportional gain to the positive 'position_p'.
        """
        command=b'\x1E'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_position_i(self,device_id,position_i):
        """
        Set the position PID controller's Integral gain to the positive 'position_i'.
        """
        command=b'\x1F'
        values=float2bytes(position_i)
        self._run_command(device_id,command+values)

    def set_position_i_sync(self, device_ids_array, values_array):
        """
        Set the position PID controller's Integral gain to the positive 'position_i'.
        """
        command=b'\x1F'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_position_d(self,device_id,position_d):
        """
        Set the position PID controller's Integral gain to the positive 'position_d'.
        """
        command=b'\x20'
        values=float2bytes(position_d)
        self._run_command(device_id,command+values)

    def set_position_d_sync(self, device_ids_array, values_array):
        """
        Set the position PID controller's Integral gain to the positive 'position_d'.
        """
        command=b'\x20'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def set_pos_control_threshold(self,device_id,poscontrol_d):
        """
        Set the threshold of the deviation between the target and current position. While the deviation is more than the threshold, integral and differential gain is set to be zero.
        """
        command=b'\x21'
        values=float2bytes(poscontrol_d)
        self._run_command(device_id,command+values)

    def set_pos_control_threshold_sync(self, device_ids_array, values_array):
        """
        Set the threshold of the deviation between the target and current position. While the deviation is more than the threshold, integral and differential gain is set to be zero.
        """
        command=b'\x21'
        self.run_command_sync_float(device_ids_array, command, values_array)

    def reset_all_pid(self,device_id):
        """
        Reset all the PID parameters to the firmware default settings.
        """
        command=b'\x22'
        self._run_command(device_id,command)


    def reset_all_pid_sync(self,device_ids_array):
        """
        Reset all the PID parameters to the firmware default settings.
        """
        command=b'\x22'
        self.run_command_sync(device_ids_array, command)


    def set_safe_run_settings(self,device_id,isEnabled,timeout,stopAction):
        """set_safe_run_settings

        Set safe run mode to stop motor automatically when it cannot receive next command within a certain period (timeout).

        Args:
            isEnabled (bool): true if setting safe run mode enabled
            timeout (int): stop action will occur after this period
            stopAction (int):
                - 0: free_motor
                - 1: disable_motor_action
                - 2: stop_motor
                - 3: Fix to the current position (move_to)
        """
        command=b'\x31'
        values=uint8_t2bytes(isEnabled)+uint32_t2bytes(timeout)+uint8_t2bytes(stopAction)
        self._run_command(device_id,command+values)

                
    def set_device_id(self,device_id, new_id):
        """
        Set driver Id (RS485 address)
        Should be from 1 to 255
        """
        command=b'\xC0'
        values=uint8_t2bytes(new_id)
        self._run_command(device_id,command+values)

    def set_motor_model(self,device_id, motor_model):
        """
        Set Motor Model
        (WARNING) It causes automatic motor adjustment with 360 deg movement.
        Please remove any payload during adjustment.
        """
        command=b'\xFC'
        values = motor_model.encode('utf-8') # string to bytes
        model_buf = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # 10 bytes
        length = len(values)
        if length <= len(model_buf):
            model_buf[:length] = values
            #model_buf
        footer = b'\x10\x99\x21\x21'
        bt = bytes(model_buf)
        print(bt)
        result = command+bytes(model_buf)+footer
        print(result)
        self._run_command(device_id,command+bytes(model_buf)+footer)


    def set_notify_pos_arrival_settings(self,device_id, isEnabled, tolerance, settleTime):
        """
        Set notification settings when arriving at the target position 
        """
        command=b'\x2B'
        values=uint8_t2bytes(isEnabled)+float2bytes(tolerance)+uint32_t2bytes(settleTime)
        self._run_command(device_id,command+values)


    def read_register(self,device_id,register):
        '''
        Read a specified setting (register).
        '''
        command=b'\x40'
        values=uint8_t2bytes(register)
        self._run_command(device_id,command+values)

    def save_all_registers(self,device_id):
        """
        Save all settings (registers) in flash memory.
        """
        command=b'\x41'
        self._run_command(device_id,command)
        time.sleep(3) # wait for next command to store registers in flash

    def save_all_registers_sync(self,device_ids_array):
        """
        Save all settings (registers) in flash memory.
        """
        command=b'\x41'
        self.run_command_sync(device_ids_array, command)
        time.sleep(3) # wait for next command to store registers in flash

    def reset_register(self,device_id,register):
        """
        Reset a specified register's value to the firmware default setting.
        """
        command=b'\x4E'
        values=uint8_t2bytes(register)
        self._run_command(device_id,command+values)

    def reset_all_registers(self,device_id):
        """
        Reset all registers' values to the firmware default setting.
        """
        command=b'\x4F'
        self._run_command(device_id,command)

    # Motor Action
    def disable_action(self,device_id):
        """
        Disable motor action.
        """
        command=b'\x50'
        self._run_command(device_id,command)

    def disable_action_sync(self,device_ids_array):
        """
        Enable motor action by broadcast.
        """
        command=b'\x50'
        self.run_command_sync(device_ids_array, command)


    def enable_action(self,device_id):
        """
        Enable motor action.
        """
        command=b'\x51'
        self._run_command(device_id,command)

    def enable_action_sync(self,device_ids_array):
        """
        Enable motor action by broadcast.
        """
        command=b'\x51'
        self.run_command_sync(device_ids_array, command)



    def set_speed(self,device_id,speed):
        """
        Set the speed of rotation to the positive 'speed' in rad/sec.
        """
        command=b'\x58'
        values=float2bytes(speed)
        self._run_command(device_id,command+values)

    def set_speed_sync(self,device_ids_array,speed_array):
        """
        Set the speed of rotation to the positive 'speed' in rad/sec.
        """
        command=b'\x58'
        self.run_command_sync_float(device_ids_array, command, speed_array)

    def preset_position(self,device_id,position):
        """
        Preset the current absolute position as the specified 'position' in rad. (Set it to zero when setting origin)
        """
        command=b'\x5A'
        values=float2bytes(position)
        self._run_command(device_id,command+values)

    def preset_position_sync(self,device_ids_array,values_array):
        """
        Preset the current absolute position as the specified 'position' in rad. (Set it to zero when setting origin)
        """
        command=b'\x5A'
        self.run_command_sync_float(device_ids_array, command,values_array)

    def get_position_offset(self,device_id,position):
        """
        Get the offset value of the absolute position.
        """
        command=b'\x5B'
        values=float2bytes(position)
        self._run_command(device_id,command+values)

    def preset_ext_position(self,device_id,position):
        """
        Preset the current absolute position as the specified 'position' in rad. (Set it to zero when setting origin)
        """
        command=b'\x5C'
        values=float2bytes(position)
        self._run_command(device_id,command+values)

    def preset_ext_position_sync(self, device_ids_array,values_array):
        """
        Preset the current absolute position as the specified 'position' in rad. (Set it to zero when setting origin)
        """
        command=b'\x5C'
        self.run_command_sync_float(device_ids_array, command,values_array)

    def run_at_velocity(self,device_id,velocity):
        """
        Rotate the motor at the 'velocity'. The velocity can be positive or negative.
        """
        command=b'\x62'
        values=float2bytes(velocity)
        self._run_command(device_id,command+values)


    def run_at_velocity_sync(self,device_ids_array,values_array):
        """
        Rotate the motor at the 'velocity'. The velocity can be positive or negative.
        """
        command=b'\x62'
        self.run_command_sync_float(device_ids_array, command,values_array)


    def move_to_ext_pos_sync(self, device_ids_array,values_array):
        """
        
        """
        command=b'\x63'
        self.run_command_sync_float(device_ids_array, command,values_array)

    def move_to_ext_pos(self,device_id,position):
        """
        
        """
        command=b'\x63'
        values=float2bytes(position)
        self._run_command(device_id,command+values)
        #self._run_command_blocking(device_id,command+values, 22)

    def move_by_ext_dist_sync(self, device_ids_array,values_array):
        """
        
        """
        command=b'\x64'
        self.run_command_sync_float(device_ids_array, command,values_array)

    def move_by_ext_dist(self,device_id,position):
        """
        
        """
        command=b'\x64'
        values=float2bytes(position)
        self._run_command(device_id,command+values)
        #self._run_command_blocking(device_id,command+values, 22)


    def move_to_pos(self,device_id,position,speed=None):
        """
        Move the motor to the specified absolute 'position' at the 'speed'.
        If the speed is None, move at the speed set by 0x58: set_speed.
        """
        if speed is not None:
            command=b'\x65'
            values=float2bytes(position)+float2bytes(speed)
        else:
            command=b'\x66'
            values=float2bytes(position)
        self._run_command(device_id,command+values)


    def move_to_pos_sync(self,device_ids_array,values_array):
        """
        Move the motor to the specified absolute 'position' at the 'speed'.
        If the speed is None, move at the speed set by 0x58: set_speed.
        """
        command=b'\x66'
        self.run_command_sync_float(device_ids_array, command,values_array)


    def move_by_dist(self,device_id,distance,speed=None):
        """
        Move the motor by the specified relative 'distance' from the current position at the 'speed'.
        If the speed is None, move at the speed set by 0x58: set_speed.
        """
        if speed is not None:
            command=b'\x67'
            values=float2bytes(distance)+float2bytes(speed)
        else:
            command=b'\x68'
            values=float2bytes(distance)
        self._run_command(device_id,command+values)

    def move_by_dist_sync(self,device_ids_array,values_array):
        """
        Move the motor to the specified absolute 'position' at the 'speed'.
        If the speed is None, move at the speed set by 0x58: set_speed.
        """
        command=b'\x68'
        self.run_command_sync_float(device_ids_array, command,values_array)

   

    def free_motor(self,device_id):
        """
        Stop the motor's excitation
        """
        command=b'\x6C'
        self._run_command(device_id,command)

    def free_motor_sync(self,device_ids_array):
        """
        Stop the motor's excitation
        """
        command=b'\x6C'
        self.run_command_sync(device_ids_array, command)

    def stop_motor(self,device_id):
        """
        Decelerate the speed to zero and stop.
        """
        command=b'\x6D'
        self._run_command(device_id,command)

    def stop_motor_sync(self,device_ids_array):
        """
        Decelerate the speed to zero and stop.
        """
        command=b'\x6D'
        self.run_command_sync(device_ids_array, command)

    # System
    def reboot(self,device_id):
        """
        Reboot the system.
        """
        command=b'\xF0'
        self._run_command(device_id,command)

    def reboot_sync(self, device_ids_array):
        """
        Reboot the system.
        """
        command=b'\xF0'
        self.run_command_sync(device_ids_array, command)

    def enable_check_sum(self,device_id,isEnabled):
        command=b'\xF3'
        values=uint8_t2bytes(isEnabled)
        self._run_command(device_id,command+values)

    def enter_device_firmware_update(self,device_id):
        """
        Enter the device firmware update mode or bootloader mode. It goes with reboot.
        """
        command=b'\xFD'
        self._run_command(device_id,command)

    def wait_firmware_update(self,device_id):
        """
        Enter the device firmware update mode or bootloader mode. It goes with reboot.
        """
        command=b'\xF1'
        self._run_command(device_id,command)

    def read_max_speed(self,device_id):
        """
        Read the current maximum speed of rotation 'max_speed' in rad/sec.
        """
        return self._read_setting_value(device_id, 0x02)

    def read_min_speed(self,device_id):
        """
        Read the current minimum speed of rotation 'min_speed' in rad/sec.
        """
        return self._read_setting_value(device_id, 0x03)

    def read_curve_type(self,device_id):
        """
        Read the current acceleration or deceleration curve 'curve_type'.
        typedef enum curveType =
        {
            CURVE_TYPE_NONE = 0, // Turn off Motion control
            CURVE_TYPE_TRAPEZOID = 1, // Turn on Motion control with trapezoidal curve
        }
        """
        return self._read_setting_value(device_id, 0x05)

    def read_acc(self,device_id):
        """
        Read the current acceleration of rotation 'acc' in rad/sec^2.
        """
        return self._read_setting_value(device_id, 0x07)

    def read_dec(self,device_id):
        """
        Read the current deceleration of rotation 'acc' in rad/sec^2.
        """
        return self._read_setting_value(device_id, 0x08)

    def read_max_torque(self,device_id):
        """
        Read the current maximum torque 'max_torque' in N.m.
        """
        return self._read_setting_value(device_id, 0x0E)

    def read_qcurrent_p(self,device_id):
        """
        Read the q-axis current PID controller's Proportional gain 'q_current_p'.
        """
        return self._read_setting_value(device_id, 0x18)

    def read_qcurrent_i(self,device_id):
        """
        Read the q-axis current PID controller's Integral gain 'q_current_i'.
        """
        return self._read_setting_value(device_id, 0x19)

    def read_qcurrent_d(self,device_id):
        """
        Read the q-axis current PID controller's Differential gain 'q_current_d'.
        """
        return self._read_setting_value(device_id, 0x1A)

    def read_speed_p(self,device_id):
        """
        Read the speed PID controller's Proportional gain 'speed_p'.
        """
        return self._read_setting_value(device_id, 0x1B)

    def read_speed_i(self,device_id):
        """
        Read the speed PID controller's Integral gain 'speed_i'.
        """
        return self._read_setting_value(device_id, 0x1C)

    def read_speed_d(self,device_id):
        """
        Read the speed PID controller's Differential gain 'speed_d'.
        """
        return self._read_setting_value(device_id, 0x1D)

    def read_position_p(self,device_id):
        """
        Read the position PID controller's Proportional gain 'position_p'.
        """
        return self._read_setting_value(device_id, 0x1E)

    def read_position_i(self,device_id):
        """
        Read the position PID controller's Integral gain 'position_i'.
        """
        return self._read_setting_value(device_id, 0x1F)

    def read_position_d(self,device_id):
        """
        Read the position PID controller's Differential gain 'position_d'.
        """
        return self._read_setting_value(device_id, 0x20)

    def read_pos_control_threshold(self,device_id):
        """
        Read the threshold of the deviation between the target and current position. While the deviation is more than the threshold, integral and differential gain is set to be zero.
        """
        return self._read_setting_value(device_id, 0x21)

    def read_own_color(self,device_id):
        """
        ToDo
        Read the own LED color. Return (red,green,blue).
        """
        return self._read_setting_value(device_id, 0x3A)

    def read_device_name(self,device_id):
        """
        Read the device name of the motor.
        """
        return self._read_setting_value(device_id, 0x46)

    def read_device_info(self,device_id):
        """
        Get the device information of the motor.
        """
        return self._read_setting_value(device_id, 0x47)

    def read_status(self,device_id):
        """
        Read the motor status: 'isCheckSumEnabled', 'iMUMeasurement', 'motorMeasurement', 'queue', 'motorEnabled', 'flash_memory_state', 'motor_control_mode'.
        """
        return self._read_setting_value(device_id, 0x9A)

    def read_device_id(self,device_id):
        """
        Get the baud rate of UART(USB).
        """
        return self._read_setting_value(device_id, 0xC0)  


    def read_gear_ratio(self,device_id):
        """
        Get the gear ratio of the actuator.
        """
        return self._read_setting_value(device_id, 0x13)     

    def read_baud_rate(self,device_id):
        """
        Get the baud rate of UART(USB).
        """
        return self._read_setting_value(device_id, 0xC3)       

    def read_motor_measurement_interval(self,device_id):
        """
        Get the motor measurement interval.
        """
        return self._read_setting_value(device_id, 0x2C)                


    def read_motor_measurement(self, device_id):
        """
        Read motor measurement values
        """
        command=b'\xB4'
        self._run_command(device_id,command)

    
    def read_motor_measurement_sync(self, device_ids_array):
        """
        Read motor measurement values by broadcast
        """
        command=b'\xB4'
        self.run_command_sync(device_ids_array, command)


    def _read_setting_value(self,device_id, comm):#dummy
        pass

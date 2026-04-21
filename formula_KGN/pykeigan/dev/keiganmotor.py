#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 24 2023

@author: Takashi Tokuda (Keigan Inc.)
"""
from lib2to3.pgen2 import driver
from pykeigan import uartcontroller as base
import serial, struct, threading, atexit, time
from pykeigan import utils

class KeiganMotor():
    def __init__(self, device_id, uartcontroller, gear_ratio=1): # 115200, 230400, 250000, 460800, 921600
        self.device_id = device_id
        #self.motorgroup = motorgroup
        self.ctrl = uartcontroller 
        self.on_motor_log_cb = uartcontroller.on_motor_log_cb
        self.on_motor_measurement_cb = uartcontroller.on_motor_measurement_cb
        self.gear_ratio = 1
        self.is_enabled = False
        self.mode = 0
        self.temp = 0
        self.position = 0
        self.degree = 0
        self.ext_position = 0
        self.ext_degree = 0
        self.velocity = 0
        self.rpm = 0
        self.ext_rpm = 0
        self.torque = 0

    def on_motor_log_cb(self, device_id, log):
        print("[ID:",device_id,'] log {} '.format(log))
        for motor in self.keiganmotors:
            if motor.device_id == device_id:
                # hoge
               pass

            # モーター回転情報callback
    def on_motor_measurement_cb(self, device_id, measurement):
        if device_id == self.device_id:
            t = measurement['motor_time']
            self.is_enabled = measurement['isEnabled']
            self.mode = measurement['mode']
            self.temp = measurement['temperature']
            self.position = measurement['position']
            self.degree = utils.rad2deg(self.position)
            self.ext_position = measurement['ext_position']
            self.ext_degree = utils.rad2deg(self.ext_position)
            self.velocity = measurement['velocity']
            self.rpm = utils.rad_per_sec2rpm(self.velocity)
            self.ext_rpm = self.rpm / self.gear_ratio
            # self.ext_velocity TODO
            self.torque = measurement['torque']
            # print(meas)
            print("id, time, tempC, pos, rad/s, Nm = ", device_id, t, self.self.temp, self.degree, self.ext_degree, self.rpm, self.torque)



class KeiganMotorGroup():
    def __init__(self, device_id_list, uartcontroller): # 115200, 230400, 250000, 460800, 921600
        self.keiganmotors = []
        self.on_measurement_cb = uartcontroller.on_motor_measurement_value_cb
        self.on_log_cb = uartcontroller.on_motor_log_cb

    def on_motor_log_cb(self, device_id, log):
        print("[ID:",device_id,'] log {} '.format(log))
        for motor in self.keiganmotors:
            if motor.device_id == device_id:
                # hoge
               pass

            # モーター回転情報callback
    def on_motor_measurement_cb(self, device_id, measurement):
        global position_1, position_2, position_3, position_4
        global temp_1, temp_2, temp_3, temp_4
        #meas = "\r[",device_id,']{} '.format(measurement)
        #print(meas, end="")
        meas = device_id , '{} '.format(measurement)
        t = measurement['motor_time']
        temp = measurement['temperature']
        position = measurement['position']
        degree = position * 180 / 3.141592
        velocity = measurement['velocity']
        torque = measurement['torque']
        # print(meas)
        print("id, time, tempC, pos, rad/s, Nm = ", device_id, t, temp, position, velocity, torque)

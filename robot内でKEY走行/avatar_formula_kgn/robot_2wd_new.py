from time import sleep
from pykeigan import uartcontroller, utils

class Robot2WD:
    def __init__(self, port_left, port_right):
        print(f'Initialize Robot 2WD ... USB port_left: {port_left}, port_right: {port_right}')
        self.dev_left = uartcontroller.UARTController(port_left)
        self.dev_right = uartcontroller.UARTController(port_right)
        self.id = 1
        self._configure_motors()

        self.dev_left.on_motor_log_cb = self._motor_log_callback
        self.dev_right.on_motor_log_cb = self._motor_log_callback
        self.dev_left.on_motor_measurement_value_cb = self._motor_measurement_callback
        self.dev_right.on_motor_measurement_value_cb = self._motor_measurement_callback

    def _configure_motors(self):
        for dev in [self.dev_left, self.dev_right]:
            dev.set_acc(self.id, 1000) #high for quick Movement, Original 70
            dev.set_dec(self.id, 2000) #high for quick Movement, Original 400
            dev.set_max_torque(self.id, 6)

    def enable(self):
        self.dev_left.enable_action(self.id)
        self.dev_right.enable_action(self.id)

    def disable(self):
        self.dev_left.disable_action(self.id)
        self.dev_right.disable_action(self.id)

    def run(self, left_rpm, right_rpm):
        rps_left = utils.rpm2rad_per_sec(-left_rpm)
        rps_right = utils.rpm2rad_per_sec(right_rpm)
        self.dev_left.run_at_velocity(self.id, rps_left)
        self.dev_right.run_at_velocity(self.id, rps_right)

    def run_straight(self, rpm):
        self.run(rpm, rpm)

    def run_pivot_turn(self, rpm):
        self.run(rpm/2, -rpm/2)

    def run_stop(self):
        self.run(0, 0)

    def _motor_log_callback(self, device_id, log):
        error = log['error_codes']
        if error == 0x14:
            print(f'\n***** Motor {device_id} is Disabled. Please enable_action(). *****\n')
        elif error == 0x06:
            print(f'\n***** Motor {device_id} Invalid parameter *****\n')

    def _motor_measurement_callback(self, device_id, measurement):
        t = measurement['motor_time']
        isEnabled = measurement['isEnabled']
        mode = measurement['mode']
        drv_fault = measurement['drv_fault']
        degree = round(utils.rad2deg(measurement['position']), 1)
        rpm = round(utils.rad_per_sec2rpm(measurement['velocity']), 1)
        torque = round(measurement['torque'], 2)
        print(f"[motor {device_id}] time: {t}, enabled: {isEnabled}, mode: {mode}, "
              f"drv_fault: {drv_fault}, inEnc[degree]: {degree}, vel[rpm]: {rpm}, trq[Nm]: {torque}")

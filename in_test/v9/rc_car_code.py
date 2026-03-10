# v9.0.0 Racing Controller - not tested yet on Raspberry Pi
import pigpio
import pygame
import time


# ==================================================
# =================== CONSTANTS ====================
# ==================================================

FAILSAFE_TIMEOUT = 0.3

RECONNECT_INTERVAL = 0.2
WATCHDOG_TIMEOUT = 1.0

DEADMAN_THRESHOLD = 0.1

STEERING_EXPO = 0.4
STEERING_SMOOTHING = 0.25
MAX_STEERING_STEP = 0.08

THROTTLE_EXPO = 0.5
MAX_ACCEL_STEP = 0.04


# ==================================================
# ================ RACING CONTROLLER ===============
# ==================================================

class RacingController:

    def __init__(self):

        self.pi = pigpio.pi()

        if not self.pi.connected:
            raise RuntimeError("Brak polaczenia z pigpio")

        # ---------- PINS ----------

        self.PWMA = 18
        self.AIN1 = 23
        self.AIN2 = 24

        self.PWMB = 17
        self.BIN1 = 22
        self.BIN2 = 27

        self.STBY = 25
        self.SERVO_PIN = 12

        # ---------- SERVO ----------

        self.SERVO_CENTER = 1500
        self.SERVO_MIN = 1000
        self.SERVO_MAX = 2000
        self.SERVO_DEADZONE = 0.08

        # ---------- PWM ----------

        self.PWM_FREQ = 20000
        self.PWM_RANGE = 1000

        # ---------- STATE ----------

        self.current_power = 0
        self.current_steering = 0

        self._setup_pins()
        self._setup_pwm()

    # ==================================================

    def _setup_pins(self):

        pins = [
            self.PWMA, self.AIN1, self.AIN2,
            self.PWMB, self.BIN1, self.BIN2,
            self.STBY, self.SERVO_PIN
        ]

        for p in pins:
            self.pi.set_mode(p, pigpio.OUTPUT)

    # ==================================================

    def _setup_pwm(self):

        self.pi.set_PWM_frequency(self.PWMA, self.PWM_FREQ)
        self.pi.set_PWM_frequency(self.PWMB, self.PWM_FREQ)

        self.pi.set_PWM_range(self.PWMA, self.PWM_RANGE)
        self.pi.set_PWM_range(self.PWMB, self.PWM_RANGE)

        self.pi.set_PWM_dutycycle(self.PWMA, 0)
        self.pi.set_PWM_dutycycle(self.PWMB, 0)

        self.pi.write(self.STBY, 0)

        self.pi.set_servo_pulsewidth(self.SERVO_PIN, self.SERVO_CENTER)

    # ==================================================
    # ==================== THROTTLE ====================
    # ==================================================

    def set_throttle(self, value):

        value = max(-1.0, min(1.0, value))

        delta = value - self.current_power
        delta = max(-MAX_ACCEL_STEP, min(MAX_ACCEL_STEP, delta))

        self.current_power += delta

        power = self.current_power
        speed = int(abs(power) * self.PWM_RANGE)

        if power > 0:

            self.pi.write(self.AIN1, 1)
            self.pi.write(self.AIN2, 0)

            self.pi.write(self.BIN1, 1)
            self.pi.write(self.BIN2, 0)

        elif power < 0:

            self.pi.write(self.AIN1, 0)
            self.pi.write(self.AIN2, 1)

            self.pi.write(self.BIN1, 0)
            self.pi.write(self.BIN2, 1)

        else:

            self.stop()
            return

        self.pi.set_PWM_dutycycle(self.PWMA, speed)
        self.pi.set_PWM_dutycycle(self.PWMB, speed)

        self.pi.write(self.STBY, 1)

    # ==================================================
    # ==================== STEERING ====================
    # ==================================================

    def set_steering(self, value):

        if abs(value) < self.SERVO_DEADZONE:
            value = 0

        delta = value - self.current_steering
        delta = max(-MAX_STEERING_STEP, min(MAX_STEERING_STEP, delta))

        self.current_steering += delta

        pulse = self.SERVO_CENTER + self.current_steering * (self.SERVO_MAX - self.SERVO_CENTER)

        pulse = max(self.SERVO_MIN, min(self.SERVO_MAX, pulse))

        self.pi.set_servo_pulsewidth(self.SERVO_PIN, pulse)

    # ==================================================

    def stop(self):

        self.current_power = 0

        self.pi.set_PWM_dutycycle(self.PWMA, 0)
        self.pi.set_PWM_dutycycle(self.PWMB, 0)

        self.pi.write(self.AIN1, 0)
        self.pi.write(self.AIN2, 0)

        self.pi.write(self.BIN1, 0)
        self.pi.write(self.BIN2, 0)

        self.pi.write(self.STBY, 0)

    # ==================================================

    def shutdown(self):

        self.stop()

        self.pi.set_servo_pulsewidth(self.SERVO_PIN, 0)

        self.pi.stop()


# ==================================================
# ==================== UTILITIES ===================
# ==================================================

def apply_expo(value, expo):

    return (1 - expo) * value + expo * (value ** 3)


def apply_throttle_curve(value):

    sign = 1 if value >= 0 else -1
    value = abs(value)

    curved = value ** (1 + THROTTLE_EXPO)

    return curved * sign


def reset_joystick():

    pygame.joystick.quit()
    pygame.joystick.init()


def wait_for_controller():

    print("Czekam na kontroler Xbox...")

    while True:

        count = pygame.joystick.get_count()

        if count > 0:

            joy = pygame.joystick.Joystick(0)
            joy.init()

            print("Kontroler podlaczony:", joy.get_name())

            return joy

        time.sleep(RECONNECT_INTERVAL)


# ==================================================
# ======================= MAIN =====================
# ==================================================

def main():

    rc = RacingController()

    pygame.init()
    pygame.joystick.init()

    joy = wait_for_controller()

    last_input_time = time.time()
    last_watchdog = time.time()

    print("RT = deadman + gaz | LT = cofanie | LX = skret")

    try:

        while True:

            try:

                for event in pygame.event.get():

                    if event.type == pygame.JOYDEVICEREMOVED:

                        print("Kontroler odlaczony")

                        rc.stop()

                        reset_joystick()

                        joy = wait_for_controller()

                        continue

                # ---------- WATCHDOG ----------

                if time.time() - last_watchdog > WATCHDOG_TIMEOUT:

                    try:
                        joy.get_axis(0)
                    except pygame.error:

                        print("Watchdog reset joystick")

                        rc.stop()

                        reset_joystick()

                        joy = wait_for_controller()

                    last_watchdog = time.time()

                # ---------- INPUT ----------

                lt = (joy.get_axis(2) + 1) / 2
                rt = (joy.get_axis(5) + 1) / 2

                raw_steering = joy.get_axis(0)

                steering = apply_expo(raw_steering, STEERING_EXPO)

                if rt < DEADMAN_THRESHOLD:

                    rc.stop()

                    time.sleep(0.02)

                    continue

                throttle = apply_throttle_curve(rt - lt)

                rc.set_throttle(throttle)
                rc.set_steering(steering)

                last_input_time = time.time()

                time.sleep(0.02)

            except pygame.error:

                print("Joystick error")

                rc.stop()

                reset_joystick()

                joy = wait_for_controller()

    finally:

        print("STOP")

        rc.shutdown()

        pygame.quit()


# ==================================================
# ====================== START =====================
# ==================================================

if __name__ == "__main__":
    main()
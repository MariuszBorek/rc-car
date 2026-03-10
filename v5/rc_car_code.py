# v5.0.0
import pigpio
import pygame
import time

# ==================================================
# =================== CONSTANTS ====================
# ==================================================

FAILSAFE_TIMEOUT = 0.3
STEERING_EXPO = 0.4
STEERING_SMOOTHING = 0.3

# ==================================================
# ================ RACING CONTROLLER ===============
# ==================================================

class RacingController:

    def __init__(self):

        self.pi = pigpio.pi()

        if not self.pi.connected:
            raise RuntimeError("Brak połączenia z pigpio")

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

        self.current_power += (value - self.current_power) * 0.2

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

        self.current_steering += (value - self.current_steering) * STEERING_SMOOTHING
        value = self.current_steering

        pulse = self.SERVO_CENTER + value * (self.SERVO_MAX - self.SERVO_CENTER)
        pulse = max(self.SERVO_MIN, min(self.SERVO_MAX, pulse))

        self.pi.set_servo_pulsewidth(self.SERVO_PIN, pulse)

    # ==================================================

    def stop(self):

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

# ==================================================

def wait_for_controller():

    print("Czekam na kontroler Xbox...")

    while True:

        pygame.joystick.quit()
        pygame.joystick.init()

        count = pygame.joystick.get_count()

        if count > 0:

            for i in range(count):

                joy = pygame.joystick.Joystick(i)
                joy.init()

                print("Kontroler podlaczony:", joy.get_name())

                return joy

        time.sleep(2)

# ==================================================
# ======================= MAIN =====================
# ==================================================

def main():

    rc = RacingController()

    pygame.init()
    pygame.joystick.init()

    pygame.event.set_allowed([
        pygame.JOYAXISMOTION,
        pygame.JOYBUTTONDOWN,
        pygame.JOYBUTTONUP,
        pygame.JOYDEVICEREMOVED,
        pygame.JOYDEVICEADDED
    ])

    joy = wait_for_controller()

    last_input_time = time.time()

    print("RT = gaz | LT = cofanie | LX = skret | B = hamulec")

    try:

        while True:

            try:

                for event in pygame.event.get():

                    if event.type == pygame.JOYDEVICEREMOVED:

                        print("Kontroler odlaczony")

                        rc.stop()

                        joy = wait_for_controller()

                        last_input_time = time.time()

                        continue


                lt = (joy.get_axis(2) + 1) / 2
                rt = (joy.get_axis(5) + 1) / 2

                throttle = rt - lt

                raw_steering = joy.get_axis(0)
                steering = apply_expo(raw_steering, STEERING_EXPO)

                if abs(throttle) > 0.01 or abs(raw_steering) > 0.01:
                    last_input_time = time.time()

                if time.time() - last_input_time > FAILSAFE_TIMEOUT:

                    print("FAILSAFE: brak sygnalu")

                    rc.stop()

                    time.sleep(0.1)

                    continue

                rc.set_throttle(throttle)
                rc.set_steering(steering)

                if joy.get_button(1):
                    rc.set_throttle(0)

                time.sleep(0.02)

            except pygame.error:

                print("Kontroler utracony")

                rc.stop()

                joy = wait_for_controller()

                last_input_time = time.time()

    finally:

        print("STOP")

        rc.shutdown()

        pygame.quit()

# ==================================================
# ====================== START =====================
# ==================================================

if __name__ == "__main__":
    main()
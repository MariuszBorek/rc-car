# version: 3.0.0 - Not verified yet on Raspberry Pi
import pigpio
import pygame
import time

# ==================================================
# ================ RACING CONTROLLER ===============
# ==================================================

class RacingController:

    def __init__(self):

        # ---------- PIGPIO ----------
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Brak połączenia z pigpio")

        # ---------- KONFIGURACJA ----------
        self.PWMA = 18
        self.AIN1 = 23
        self.AIN2 = 24
        self.PWMB = 17
        self.BIN1 = 22
        self.BIN2 = 27
        self.STBY = 25

        self.SERVO_PIN = 12
        self.SERVO_CENTER = 1500
        self.SERVO_MIN = 1000
        self.SERVO_MAX = 2000
        self.SERVO_DEADZONE = 0.08

        self.PWM_FREQ = 20000
        self.PWM_RANGE = 1000

        self.current_power = 0

        self._setup_pins()
        self._setup_pwm()

    def _setup_pins(self):

        pins = [
            self.PWMA, self.AIN1, self.AIN2,
            self.PWMB, self.BIN1, self.BIN2,
            self.STBY, self.SERVO_PIN
        ]

        for p in pins:
            self.pi.set_mode(p, pigpio.OUTPUT)

    def _setup_pwm(self):

        self.pi.set_PWM_frequency(self.PWMA, self.PWM_FREQ)
        self.pi.set_PWM_frequency(self.PWMB, self.PWM_FREQ)

        self.pi.set_PWM_range(self.PWMA, self.PWM_RANGE)
        self.pi.set_PWM_range(self.PWMB, self.PWM_RANGE)

        self.pi.set_PWM_dutycycle(self.PWMA, 0)
        self.pi.set_PWM_dutycycle(self.PWMB, 0)

        self.pi.write(self.STBY, 0)
        self.pi.set_servo_pulsewidth(self.SERVO_PIN, self.SERVO_CENTER)

    # ---------- NAPĘD ----------
    def set_throttle(self, value):

        value = max(-1.0, min(1.0, value))

        # soft ramp
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

    # ---------- SKRĘT ----------
    def set_steering(self, value):

        if abs(value) < self.SERVO_DEADZONE:
            value = 0

        pulse = self.SERVO_CENTER + value * (self.SERVO_MAX - self.SERVO_CENTER)

        pulse = max(self.SERVO_MIN, min(self.SERVO_MAX, pulse))

        self.pi.set_servo_pulsewidth(self.SERVO_PIN, pulse)

    # ---------- STOP ----------
    def stop(self):

        self.pi.set_PWM_dutycycle(self.PWMA, 0)
        self.pi.set_PWM_dutycycle(self.PWMB, 0)

        self.pi.write(self.AIN1, 0)
        self.pi.write(self.AIN2, 0)

        self.pi.write(self.BIN1, 0)
        self.pi.write(self.BIN2, 0)

        self.pi.write(self.STBY, 0)

    def shutdown(self):

        self.stop()

        self.pi.set_servo_pulsewidth(self.SERVO_PIN, 0)

        self.pi.stop()


# ==================================================
# ================= CONTROLLER WAIT =================
# ==================================================

def wait_for_controller():

    print("Czekam na kontroler Xbox...")

    while True:

        pygame.joystick.quit()
        pygame.joystick.init()

        if pygame.joystick.get_count() > 0:

            joy = pygame.joystick.Joystick(0)
            joy.init()

            print("Kontroler podłączony")

            return joy

        time.sleep(2)


# ==================================================
# ====================== MAIN =======================
# ==================================================

def main():

    rc = RacingController()

    pygame.init()
    pygame.joystick.init()

    joy = wait_for_controller()

    print("RT = gaz | LT = cofanie | LX = skręt | B = hamulec")

    try:

        while True:

            pygame.event.pump()

            # jeśli pad się rozłączy
            if not joy.get_init():

                print("Kontroler odłączony")

                rc.stop()

                joy = wait_for_controller()

                continue

            # --- TRIGGERY ---
            lt = (joy.get_axis(2) + 1) / 2
            rt = (joy.get_axis(5) + 1) / 2

            throttle = rt - lt

            rc.set_throttle(throttle)

            # --- SKRĘT ---
            steering = joy.get_axis(0)

            rc.set_steering(steering)

            # --- HAMULEC ---
            if joy.get_button(1):

                rc.set_throttle(0)

            time.sleep(0.02)

    finally:

        print("STOP")

        rc.shutdown()

        pygame.quit()


# ==================================================
# ====================== START ======================
# ==================================================

if __name__ == "__main__":
    main()
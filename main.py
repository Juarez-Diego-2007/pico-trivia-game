"""
Two-Player Trivia Game System

Embedded Raspberry Pi Pico trivia game using:
- Dual player button inputs
- Four I2C LCD displays
- DC motor score indicator

Each player selects their own language and receives
independent questions. Both players answer simultaneously.
Correct answers move the motor toward the winning player.
After each win, the motor resets the spaceship to center.
"""

from machine import I2C, Pin, PWM
from pico_i2c_lcd import I2cLcd
from picozero import Button, LED
from time import sleep, ticks_ms
import random
import json


# ── I2C SETUP ─────────────────────────────────────────────────────────────────
i2c0 = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
i2c1 = I2C(1, sda=Pin(2), scl=Pin(3), freq=400000)
sleep(0.1)


# ── LCD SETUP ─────────────────────────────────────────────────────────────────
lcd_q1 = I2cLcd(i2c1, 0x27, 4, 20)  # P1 question screen
sleep(0.05)
lcd_q2 = I2cLcd(i2c0, 0x26, 4, 20)  # P2 question screen
sleep(0.05)
lcd_a1 = I2cLcd(i2c1, 0x24, 4, 20)  # P1 answer screen
sleep(0.05)
lcd_a2 = I2cLcd(i2c0, 0x25, 4, 20)  # P2 answer screen
sleep(0.05)


# ── LOAD QUESTIONS ────────────────────────────────────────────────────────────
with open("questions.json", "r") as f:
    questions = json.load(f)


# ── BUTTONS ───────────────────────────────────────────────────────────────────
p1_A = Button(20, pull_up=True)
p1_B = Button(21, pull_up=True)
p1_C = Button(22, pull_up=True)
p1_D = Button(26, pull_up=True)

p2_A = Button(16, pull_up=True)
p2_B = Button(17, pull_up=True)
p2_C = Button(18, pull_up=True)
p2_D = Button(19, pull_up=True)

LETTERS = ["A) ", "B) ", "C) ", "D) "]
P1_BUTTONS = [p1_A, p1_B, p1_C, p1_D]
P2_BUTTONS = [p2_A, p2_B, p2_C, p2_D]
ALL_BUTTONS = P1_BUTTONS + P2_BUTTONS
ANSWER_LETTERS = ["A", "B", "C", "D"]


# ── LED SETUP ─────────────────────────────────────────────────────────────────
red_led    = LED(14)
green_led  = LED(15)
blue_led   = LED(27)
yellow_led = LED(28)

ALL_LEDS = [red_led, green_led, blue_led, yellow_led]


def leds_off():
    for led in ALL_LEDS:
        led.off()


def wrong_flash():
    leds_off()
    for _ in range(3):
        red_led.on()
        sleep(0.12)
        red_led.off()
        sleep(0.12)


def correct_flash():
    leds_off()
    for _ in range(3):
        green_led.on()
        sleep(0.12)
        green_led.off()
        sleep(0.12)


def winner_flash():
    leds_off()
    for _ in range(8):
        for led in ALL_LEDS:
            led.on()
        sleep(0.1)
        for led in ALL_LEDS:
            led.off()
        sleep(0.1)


# ── MOTOR ─────────────────────────────────────────────────────────────────────
AIN1 = Pin(10, Pin.OUT)
AIN2 = Pin(11, Pin.OUT)
PWMA = PWM(Pin(12))
STBY = Pin(13, Pin.OUT)

PWMA.freq(20000)
STBY.value(1)

MOTOR_SPEED = 1.0
MOTOR_TIME  = .25


def motor_stop():
    PWMA.duty_u16(0)
    AIN1.value(0)
    AIN2.value(0)


def motor_player1():
    AIN1.value(1)
    AIN2.value(0)
    PWMA.duty_u16(int(65535 * MOTOR_SPEED))
    sleep(MOTOR_TIME)
    motor_stop()


def motor_player2():
    AIN1.value(0)
    AIN2.value(1)
    PWMA.duty_u16(int(65535 * MOTOR_SPEED))
    sleep(MOTOR_TIME)
    motor_stop()


motor_stop()


# ── GAME CONSTANT ─────────────────────────────────────────────────────────────
WIN_POINTS = 3


# ── MOTOR RESET TO CENTER ─────────────────────────────────────────────────────
def reset_motor_to_center(winner):
    show_both("RESETTING...", "RESETTING...")
    for _ in range(WIN_POINTS):
        if winner == 1:
            motor_player2()
        else:
            motor_player1()
        sleep(0.2)


# ── TEXT HELPERS ──────────────────────────────────────────────────────────────
def word_wrap(text, width=20):
    words = (text or "").split()
    lines = []
    current_line = ""
    for w in words:
        if len(current_line) + len(w) + (1 if current_line else 0) <= width:
            current_line = w if not current_line else current_line + " " + w
        else:
            lines.append(current_line)
            current_line = w
    if current_line:
        lines.append(current_line)
    return lines[:4]


def put_line(lcd, row, text):
    lcd.move_to(0, row)
    text = text[:20]
    text = text + " " * (20 - len(text))
    lcd.putstr(text)


def clear_all():
    for lcd in [lcd_q1, lcd_q2, lcd_a1, lcd_a2]:
        lcd.clear()


def show_lcd(lcd, msg):
    lines = word_wrap(msg)
    for r in range(4):
        put_line(lcd, r, lines[r] if r < len(lines) else "")


def show_both(msg1, msg2):
    show_lcd(lcd_q1, msg1)
    show_lcd(lcd_q2, msg2)


def display_question(lcd_q, lcd_a, q_text, choices):
    show_lcd(lcd_q, q_text)
    for i in range(4):
        put_line(lcd_a, i, LETTERS[i] + (choices[i] if i < len(choices) else ""))


def display_both_questions(q1_text, q1_choices, q2_text, q2_choices):
    """
    Interleave writes to P1 and P2 screens one row at a time.
    Since P1 and P2 are on separate I2C buses, this makes both
    screens appear to update at the same time instead of P2 lagging behind.
    """
    q1_lines = word_wrap(q1_text)
    q2_lines = word_wrap(q2_text)

    # Write question rows interleaved
    for r in range(4):
        put_line(lcd_q1, r, q1_lines[r] if r < len(q1_lines) else "")
        put_line(lcd_q2, r, q2_lines[r] if r < len(q2_lines) else "")

    # Write answer rows interleaved
    for i in range(4):
        put_line(lcd_a1, i, LETTERS[i] + (q1_choices[i] if i < len(q1_choices) else ""))
        put_line(lcd_a2, i, LETTERS[i] + (q2_choices[i] if i < len(q2_choices) else ""))


# ── BUTTON RELEASE WAIT ───────────────────────────────────────────────────────
def wait_all_released():
    """Block until every button is physically released.
    Prevents a held answer button from firing again on the next screen."""
    while any(btn.is_pressed for btn in ALL_BUTTONS):
        sleep(0.01)


# ── COUNTDOWN ─────────────────────────────────────────────────────────────────
def countdown():
    for n in ["3", "2", "1", "GO!"]:
        put_line(lcd_q1, 0, n)
        put_line(lcd_q2, 0, n)
        sleep(0.4)


# ── LANGUAGE SELECTION ────────────────────────────────────────────────────────
def choose_languages():
    clear_all()

    put_line(lcd_q1, 0, "P1: PICK LANG")
    put_line(lcd_a1, 0, "A = ENGLISH")
    put_line(lcd_a1, 1, "B = ESPANOL")

    put_line(lcd_q2, 0, "P2: PICK LANG")
    put_line(lcd_a2, 0, "A = ENGLISH")
    put_line(lcd_a2, 1, "B = ESPANOL")

    lang1 = lang2 = None
    prev_p1A = prev_p1B = prev_p2A = prev_p2B = False

    while True:
        cur_p1A = p1_A.is_pressed
        cur_p1B = p1_B.is_pressed
        cur_p2A = p2_A.is_pressed
        cur_p2B = p2_B.is_pressed

        if lang1 is None:
            if cur_p1A and not prev_p1A:
                lang1 = "en"
                put_line(lcd_q1, 2, "P1: ENGLISH")
                put_line(lcd_q1, 3, "WAITING FOR P2")
            elif cur_p1B and not prev_p1B:
                lang1 = "es"
                put_line(lcd_q1, 2, "P1: ESPANOL")
                put_line(lcd_q1, 3, "WAITING FOR P2")

        if lang2 is None:
            if cur_p2A and not prev_p2A:
                lang2 = "en"
                put_line(lcd_q2, 2, "P2: ENGLISH")
                put_line(lcd_q2, 3, "WAITING FOR P1")
            elif cur_p2B and not prev_p2B:
                lang2 = "es"
                put_line(lcd_q2, 2, "P2: ESPANOL")
                put_line(lcd_q2, 3, "WAITING FOR P1")

        if lang1 is not None and lang2 is not None:
            sleep(0.1)
            break

        prev_p1A, prev_p1B = cur_p1A, cur_p1B
        prev_p2A, prev_p2B = cur_p2A, cur_p2B
        sleep(0.01)

    return lang1, lang2


# ── ANSWER POLLING ────────────────────────────────────────────────────────────
ANSWER_TIMEOUT_MS = 30000


def get_both_answers(correct1, correct2):
    """
    Poll both players until both answer or time runs out.
    LED flashes happen AFTER both have answered so they never
    block the polling loop or leave buttons held going into the next screen.
    """
    p1_ans = p2_ans = None
    p1_result = p2_result = None  # "correct" or "wrong", set when answered
    start = ticks_ms()
    prev_p1 = [False] * 4
    prev_p2 = [False] * 4

    while True:
        elapsed = ticks_ms() - start

        if elapsed >= ANSWER_TIMEOUT_MS:
            if p1_ans is None:
                show_lcd(lcd_q1, "TIME OUT! ANS: " + correct1)
                p1_result = "timeout"
            if p2_ans is None:
                show_lcd(lcd_q2, "TIME OUT! ANS: " + correct2)
                p2_result = "timeout"
            sleep(1.0)
            break

        cur_p1 = [btn.is_pressed for btn in P1_BUTTONS]
        cur_p2 = [btn.is_pressed for btn in P2_BUTTONS]

        if p1_ans is None:
            for i in range(4):
                if cur_p1[i] and not prev_p1[i]:
                    p1_ans = ANSWER_LETTERS[i]
                    if p1_ans == correct1:
                        show_lcd(lcd_q1, "P1: CORRECT!")
                        p1_result = "correct"
                    else:
                        show_lcd(lcd_q1, "P1: WRONG! ANS: " + correct1)
                        p1_result = "wrong"
                    if p2_ans is None:
                        put_line(lcd_q1, 2, "WAITING FOR P2")
                    break

        if p2_ans is None:
            for i in range(4):
                if cur_p2[i] and not prev_p2[i]:
                    p2_ans = ANSWER_LETTERS[i]
                    if p2_ans == correct2:
                        show_lcd(lcd_q2, "P2: CORRECT!")
                        p2_result = "correct"
                    else:
                        show_lcd(lcd_q2, "P2: WRONG! ANS: " + correct2)
                        p2_result = "wrong"
                    if p1_ans is None:
                        put_line(lcd_q2, 2, "WAITING FOR P1")
                    break

        if p1_ans is not None and p2_ans is not None:
            break

        prev_p1 = cur_p1
        prev_p2 = cur_p2
        sleep(0.01)

    # ── All buttons released before flashing ──────────────────────────────────
    # This is what stopped the motor and caused the language screen to re-trigger.
    # We wait here so no held button bleeds into the next polling loop.
    wait_all_released()

    # ── Flash LEDs now that polling is fully done ─────────────────────────────
    if p1_result == "correct" or p2_result == "correct":
        correct_flash()
    elif p1_result == "wrong" or p2_result == "wrong":
        wrong_flash()

    return p1_ans, p2_ans


# ── PLAY AGAIN ────────────────────────────────────────────────────────────────
def ask_play_again():
    clear_all()

    put_line(lcd_q1, 0, "PLAY AGAIN?")
    put_line(lcd_q2, 0, "PLAY AGAIN?")
    put_line(lcd_a1, 0, "A = YES")
    put_line(lcd_a2, 0, "A = YES")
    put_line(lcd_a1, 1, "B = NO")
    put_line(lcd_a2, 1, "B = NO")
    put_line(lcd_q1, 2, "BOTH PRESS A")
    put_line(lcd_q2, 2, "BOTH PRESS A")

    p1_vote = p2_vote = None

    while True:
        if p1_vote is None:
            if p1_A.is_pressed:
                sleep(0.2)
                p1_vote = True
                put_line(lcd_q1, 3, "P1: READY!")
            elif p1_B.is_pressed:
                sleep(0.2)
                return False

        if p2_vote is None:
            if p2_A.is_pressed:
                sleep(0.2)
                p2_vote = True
                put_line(lcd_q2, 3, "P2: READY!")
            elif p2_B.is_pressed:
                sleep(0.2)
                return False

        if p1_vote and p2_vote:
            return True

        sleep(0.01)


# ── MAIN GAME LOOP ────────────────────────────────────────────────────────────
def run_game(lang1, lang2):
    p1_score = 0
    used_indices = []

    def pick_question():
        available = [i for i in range(len(questions)) if i not in used_indices]
        if not available:
            used_indices.clear()
            available = list(range(len(questions)))
        idx = random.choice(available)
        used_indices.append(idx)
        return questions[idx]

    while True:
        q1 = pick_question()
        q2 = pick_question()

        q1_text    = q1["question_en"] if lang1 == "en" else q1["question_es"]
        q1_choices = q1["choices_en"]  if lang1 == "en" else q1["choices_es"]
        q1_correct = q1["answer"]

        q2_text    = q2["question_en"] if lang2 == "en" else q2["question_es"]
        q2_choices = q2["choices_en"]  if lang2 == "en" else q2["choices_es"]
        q2_correct = q2["answer"]

        countdown()
        display_both_questions(q1_text, q1_choices, q2_text, q2_choices)

        p1_ans, p2_ans = get_both_answers(q1_correct, q2_correct)

        # Update scores
        if p1_ans == q1_correct:
            p1_score += 1
        if p2_ans == q2_correct:
            p1_score -= 1

        # Move motor — runs cleanly now because buttons are already released
        if p1_ans == q1_correct and p2_ans != q2_correct:
            motor_player1()
        elif p2_ans == q2_correct and p1_ans != q1_correct:
            motor_player2()
        else:
            sleep(0.3)

        # Clamp score
        p1_score = max(-WIN_POINTS, min(WIN_POINTS, p1_score))

        if p1_score >= WIN_POINTS:
            show_both("PLAYER 1 WINS!", "PLAYER 1 WINS!")
            winner_flash()
            sleep(1.5)
            reset_motor_to_center(winner=1)
            return 1

        if p1_score <= -WIN_POINTS:
            show_both("PLAYER 2 WINS!", "PLAYER 2 WINS!")
            winner_flash()
            sleep(1.5)
            reset_motor_to_center(winner=2)
            return 2


def main():
    while True:
        clear_all()
        leds_off()

        lang1, lang2 = choose_languages()
        run_game(lang1, lang2)

        again = ask_play_again()

        if not again:
            clear_all()
            show_both("THANKS 4 PLAYING", "THANKS 4 PLAYING")
            motor_stop()
            leds_off()
            while True:
                sleep(1)


main()


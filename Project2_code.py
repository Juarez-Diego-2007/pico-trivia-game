"""
Two-Player Trivia Game System

Embedded Raspberry Pi Pico trivia game using:
- Dual player button inputs
- Four I2C LCD displays
- DC motor score indicator

Players compete to answer questions first.
Correct answers move the motor toward the player
until a win condition is reached.
"""

from machine import I2C, Pin, PWM
from pico_i2c_lcd import I2cLcd
from picozero import Button
from time import sleep
import random
import json


#I2C SETUP
i2c0 = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
i2c1 = I2C(1, sda=Pin(2), scl=Pin(3), freq=100000)
sleep(0.1)


#LCD SETUP
lcd_q1 = I2cLcd(i2c0, 0x24, 4, 20)
sleep(0.05)
lcd_q2 = I2cLcd(i2c1, 0x26, 4, 20)
sleep(0.05)

lcd_a1 = I2cLcd(i2c0, 0x27, 4, 20)
sleep(0.05)
lcd_a2 = I2cLcd(i2c1, 0x25, 4, 20)
sleep(0.05)


#LOAD QUESTIONS
with open("questions.json", "r") as f:
    questions = json.load(f)


#BUTTONS
p1_A = Button(16, pull_up=True)
p1_B = Button(17, pull_up=True)
p1_C = Button(18, pull_up=True)
p1_D = Button(19, pull_up=True)

p2_A = Button(20, pull_up=True)
p2_B = Button(21, pull_up=True)
p2_C = Button(22, pull_up=True)
p2_D = Button(26, pull_up=True)

letters = ["A) ", "B) ", "C) ", "D) "]


#MOTOR
AIN1 = Pin(11, Pin.OUT)
AIN2 = Pin(12, Pin.OUT)
PWMA = PWM(Pin(13))
PWMA.freq(20000)

MOTOR_SPEED = 0.75
MOTOR_TIME = 0.5


def motor_stop():
    """
    Stop motor movement by disabling PWM output and direction pins.

    Returns:
        None
    """
    PWMA.duty_u16(0)
    AIN1.value(0)
    AIN2.value(0)


def motor_right():
    """
    Rotate motor right for MOTOR_TIME seconds at MOTOR_SPEED.

    Returns:
        None
    """
    AIN1.value(1)
    AIN2.value(0)
    PWMA.duty_u16(int(65535 * MOTOR_SPEED))
    sleep(MOTOR_TIME)
    motor_stop()


def motor_left():
    """
    Rotate motor left for MOTOR_TIME seconds at MOTOR_SPEED.

    Returns:
        None
    """
    AIN1.value(0)
    AIN2.value(1)
    PWMA.duty_u16(int(65535 * MOTOR_SPEED))
    sleep(MOTOR_TIME)
    motor_stop()


motor_stop()


#TEXT HELPERS
def word_wrap(text, width=20):
    """
    Split text into LCD-sized lines without breaking words.

    Args:
        text (str): Text to format.
        width (int): Max characters per line.

    Returns:
        list[str]: Up to four wrapped LCD lines.
    """
    words = (text or "").split()  # split sentence into words
    lines = []
    current_line = ""

    for w in words:

        if len(current_line) + len(w) + (1 if current_line else 0) <= width:

            if current_line == "":
                current_line = w
            else:
                current_line = current_line + " " + w

        else:
            lines.append(current_line)
            current_line = w

    if current_line:
        lines.append(current_line)

    return lines[:4]


def put_line(lcd, row, text):
    """
    Write padded text to a specific LCD row.

    Args:
        lcd (I2cLcd): Target LCD display.
        row (int): Row index (0–3).
        text (str): Text to display.

    Returns:
        None
    """
    lcd.move_to(0, row)

    text = text[:20]
    padding = 20 - len(text)

    if padding > 0:
        text += " " * padding  # overwrite leftover characters

    lcd.putstr(text)


def clear_all():
    """
    Clear all connected LCD screens.

    Returns:
        None
    """
    for screen in [lcd_q1, lcd_q2, lcd_a1, lcd_a2]:
        screen.clear()


#DISPLAY
def display_question(text):
    """
    Show wrapped question text on both question LCDs.
    """
    lines = word_wrap(text)

    lcd_q1.clear()
    lcd_q2.clear()

    for r in range(4):

        if r < len(lines):
            line = lines[r]
        else:
            line = ""

        put_line(lcd_q1, r, line)
        put_line(lcd_q2, r, line)


def display_answers(answers):
    """
    Display answer choices A–D on both answer LCDs.
    """
    lcd_a1.clear()
    lcd_a2.clear()

    for i in range(4):

        if i < len(answers):
            ans = answers[i]
        else:
            ans = ""

        line = letters[i] + ans

        put_line(lcd_a1, i, line)
        put_line(lcd_a2, i, line)


def show_message(msg, seconds=1.0):
    """
    Display temporary message on question screens.
    """
    lcd_q1.clear()
    lcd_q2.clear()

    lines = word_wrap(msg)

    for r in range(4):

        if r < len(lines):
            line = lines[r]
        else:
            line = ""

        put_line(lcd_q1, r, line)
        put_line(lcd_q2, r, line)

    sleep(seconds)


#INPUT
def get_answer_first_press():
    """
    Wait for first player button press.

    Returns:
        tuple(int, str): (player_number, answer_letter)
    """
    while True:

        if p1_A.is_pressed:
            sleep(0.08)
            return (1, "A")

        if p1_B.is_pressed:
            sleep(0.08)
            return (1, "B")

        if p1_C.is_pressed:
            sleep(0.08)
            return (1, "C")

        if p1_D.is_pressed:
            sleep(0.08)
            return (1, "D")

        if p2_A.is_pressed:
            sleep(0.08)
            return (2, "A")

        if p2_B.is_pressed:
            sleep(0.08)
            return (2, "B")

        if p2_C.is_pressed:
            sleep(0.08)
            return (2, "C")

        if p2_D.is_pressed:
            sleep(0.08)
            return (2, "D")

        sleep(0.01)


def ask_play_again():
    """
    Prompt players to replay the game.

    Returns:
        bool: True if replay selected.
    """
    clear_all()

    put_line(lcd_q1, 0, "PLAY AGAIN?")
    put_line(lcd_q2, 0, "PLAY AGAIN?")
    put_line(lcd_q1, 1, "A = YES")
    put_line(lcd_q2, 1, "A = YES")
    put_line(lcd_q1, 2, "B = NO")
    put_line(lcd_q2, 2, "B = NO")

    while True:

        if p1_A.is_pressed or p2_A.is_pressed:
            sleep(0.2)
            return True

        if p1_B.is_pressed or p2_B.is_pressed:
            sleep(0.2)
            return False

        sleep(0.01)


#GAME
WIN_POINTS = 3


def run_game():
    """
    Run one trivia match until a player reaches WIN_POINTS.

    Returns:
        int: Winning player number.
    """
    p1_score = 0

    while True:

        q = random.choice(questions)

        question = q["question"]
        answers = q["choices"]
        correct = q["answer"]

        display_question(question)
        display_answers(answers)

        player, choice = get_answer_first_press()

        if choice == correct:

            if player == 1:
                p1_score += 1
                show_message("PLAYER 1 CORRECT!", 0.6)
                motor_right()

            else:
                p1_score -= 1
                show_message("PLAYER 2 CORRECT!", 0.6)
                motor_left()

        else:
            show_message(f"P{player} WRONG!", 0.8)

        p1_score = max(-WIN_POINTS, min(WIN_POINTS, p1_score))

        if p1_score >= WIN_POINTS:
            show_message("PLAYER 1 WINS!", 2.0)
            return 1

        if p1_score <= -WIN_POINTS:
            show_message("PLAYER 2 WINS!", 2.0)
            return 2


def main():
    """
    Main control loop handling repeated games and shutdown.
    """
    while True:

        winner = run_game()
        again = ask_play_again()

        if not again:

            clear_all()
            show_message("GAME OVER", 2.0)
            motor_stop()

            while True:
                sleep(1)


main()
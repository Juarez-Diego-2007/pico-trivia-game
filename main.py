
"""
Two-Player Trivia Game System

Embedded Raspberry Pi Pico trivia game using:
- Dual player button inputs
- Four I2C LCD displays
- DC motor score indicator

Each player selects their own language and receives
independent questions. Both players answer simultaneously.
Correct answers move the motor toward the winning player.
"""

from machine import I2C, Pin, PWM
from pico_i2c_lcd import I2cLcd
from picozero import Button
from time import sleep, ticks_ms
import random
import json


# I2C SETUP
i2c0 = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
i2c1 = I2C(1, sda=Pin(2), scl=Pin(3), freq=100000)
sleep(0.1)


# LCD SETUP
# Player 1: lcd_q1 (questions), lcd_a1 (answers)
# Player 2: lcd_q2 (questions), lcd_a2 (answers)
lcd_q1 = I2cLcd(i2c0, 0x27, 4, 20)  # P1 question screen
sleep(0.05)
lcd_q2 = I2cLcd(i2c1, 0x26, 4, 20)  # P2 question screen
sleep(0.05)
lcd_a1 = I2cLcd(i2c0, 0x24, 4, 20)  # P1 answer screen
sleep(0.05)
lcd_a2 = I2cLcd(i2c1, 0x25, 4, 20)  # P2 answer screen
sleep(0.05)


# LOAD QUESTIONS
with open("questions.json", "r") as f:
    questions = json.load(f)


# BUTTONS
p1_A = Button(16, pull_up=True)
p1_B = Button(17, pull_up=True)
p1_C = Button(18, pull_up=True)
p1_D = Button(19, pull_up=True)

p2_A = Button(20, pull_up=True)
p2_B = Button(21, pull_up=True)
p2_C = Button(22, pull_up=True)
p2_D = Button(26, pull_up=True)

letters = ["A) ", "B) ", "C) ", "D) "]

P1_BUTTONS = [p1_A, p1_B, p1_C, p1_D]
P2_BUTTONS = [p2_A, p2_B, p2_C, p2_D]
ANSWER_LETTERS = ["A", "B", "C", "D"]


# MOTOR
AIN1 = Pin(10, Pin.OUT)
AIN2 = Pin(11, Pin.OUT)
PWMA = PWM(Pin(12))
STBY = Pin(13, Pin.OUT)

PWMA.freq(20000)
STBY.value(1)

MOTOR_SPEED = 1.0
MOTOR_TIME = 1.0


def motor_stop():
    PWMA.duty_u16(0)
    AIN1.value(0)
    AIN2.value(0)


def motor_player1():
    # Player 1 moves motor one way
    AIN1.value(1)
    AIN2.value(0)
    PWMA.duty_u16(int(65535 * MOTOR_SPEED))
    sleep(MOTOR_TIME)
    motor_stop()


def motor_player2():
    # Player 2 moves motor the other way
    AIN1.value(0)
    AIN2.value(1)
    PWMA.duty_u16(int(65535 * MOTOR_SPEED))
    sleep(MOTOR_TIME)
    motor_stop()


motor_stop()


# TEXT HELPERS
def word_wrap(text, width=20):
    words = (text or "").split()
    lines = []
    current_line = ""

    for w in words:
        if len(current_line) + len(w) + (1 if current_line else 0) <= width:
            current_line = w if current_line == "" else current_line + " " + w
        else:
            lines.append(current_line)
            current_line = w

    if current_line:
        lines.append(current_line)

    return lines[:4]


def put_line(lcd, row, text):
    lcd.move_to(0, row)
    text = text[:20]
    text += " " * (20 - len(text))
    lcd.putstr(text)


def clear_all():
    for screen in [lcd_q1, lcd_q2, lcd_a1, lcd_a2]:
        screen.clear()


# PER-PLAYER DISPLAY
def display_question_p1(text):
    lines = word_wrap(text)
    lcd_q1.clear()
    for r in range(4):
        put_line(lcd_q1, r, lines[r] if r < len(lines) else "")


def display_question_p2(text):
    lines = word_wrap(text)
    lcd_q2.clear()
    for r in range(4):
        put_line(lcd_q2, r, lines[r] if r < len(lines) else "")


def display_answers_p1(answers):
    lcd_a1.clear()
    for i in range(4):
        put_line(lcd_a1, i, letters[i] + (answers[i] if i < len(answers) else ""))


def display_answers_p2(answers):
    lcd_a2.clear()
    for i in range(4):
        put_line(lcd_a2, i, letters[i] + (answers[i] if i < len(answers) else ""))


def show_message_p1(msg):
    """Show a result message on Player 1's question screen."""
    lines = word_wrap(msg)
    lcd_q1.clear()
    for r in range(4):
        put_line(lcd_q1, r, lines[r] if r < len(lines) else "")


def show_message_p2(msg):
    """Show a result message on Player 2's question screen."""
    lines = word_wrap(msg)
    lcd_q2.clear()
    for r in range(4):
        put_line(lcd_q2, r, lines[r] if r < len(lines) else "")


# LANGUAGE SELECTION
def choose_languages():
    """
    Show language selection on both players' screens simultaneously
    and poll all buttons in a single shared loop.

    Returns:
        tuple(str, str): (lang1, lang2)
    """
    clear_all()

    # Show prompts on both sides at once
    put_line(lcd_q1, 0, "P1: SELECT LANG")
    put_line(lcd_a1, 0, "A = ENGLISH")
    put_line(lcd_a1, 1, "B = ESPANOL")

    put_line(lcd_q2, 0, "P2: SELECT LANG")
    put_line(lcd_a2, 0, "A = ENGLISH")
    put_line(lcd_a2, 1, "B = ESPANOL")

    lang1 = None
    lang2 = None

    prev_p1A = prev_p1B = False
    prev_p2A = prev_p2B = False

    while True:
        cur_p1A = p1_A.is_pressed
        cur_p1B = p1_B.is_pressed
        cur_p2A = p2_A.is_pressed
        cur_p2B = p2_B.is_pressed

        # P1 rising edge detection
        if lang1 is None:
            if cur_p1A and not prev_p1A:
                lang1 = "en"
                put_line(lcd_q1, 2, "P1: ENGLISH")
                put_line(lcd_q1, 3, "WAITING FOR P2...")
            elif cur_p1B and not prev_p1B:
                lang1 = "es"
                put_line(lcd_q1, 2, "P1: ESPANOL")
                put_line(lcd_q1, 3, "WAITING FOR P2...")

        # P2 rising edge detection
        if lang2 is None:
            if cur_p2A and not prev_p2A:
                lang2 = "en"
                put_line(lcd_q2, 2, "P2: ENGLISH")
                put_line(lcd_q2, 3, "WAITING FOR P1...")
            elif cur_p2B and not prev_p2B:
                lang2 = "es"
                put_line(lcd_q2, 2, "P2: ESPANOL")
                put_line(lcd_q2, 3, "WAITING FOR P1...")

        if lang1 is not None and lang2 is not None:
            sleep(0.1)
            break

        prev_p1A = cur_p1A
        prev_p1B = cur_p1B
        prev_p2A = cur_p2A
        prev_p2B = cur_p2B

        sleep(0.01)

    return lang1, lang2


# INPUT — simultaneous polling
ANSWER_TIMEOUT_MS = 15000  # 15 seconds to answer


def get_both_answers(correct1, correct2):
    """
    Poll both players simultaneously. Show correct/wrong feedback
    immediately on each player's screen as soon as they answer.

    Returns:
        tuple(str|None, str|None): (p1_answer, p2_answer)
        None means the player did not answer in time.
    """
    p1_ans = None
    p2_ans = None
    start = ticks_ms()

    prev_p1 = [False] * 4
    prev_p2 = [False] * 4

    while True:
        if ticks_ms() - start >= ANSWER_TIMEOUT_MS:
            if p1_ans is None:
                show_message_p1("P1: TIME OUT!")
            if p2_ans is None:
                show_message_p2("P2: TIME OUT!")
            break

        cur_p1 = [btn.is_pressed for btn in P1_BUTTONS]
        cur_p2 = [btn.is_pressed for btn in P2_BUTTONS]

        if p1_ans is None:
            for i in range(4):
                if cur_p1[i] and not prev_p1[i]:
                    p1_ans = ANSWER_LETTERS[i]
                    if p1_ans == correct1:
                        show_message_p1("P1: CORRECT!")
                    else:
                        show_message_p1("P1: WRONG!")
                    break

        if p2_ans is None:
            for i in range(4):
                if cur_p2[i] and not prev_p2[i]:
                    p2_ans = ANSWER_LETTERS[i]
                    if p2_ans == correct2:
                        show_message_p2("P2: CORRECT!")
                    else:
                        show_message_p2("P2: WRONG!")
                    break

        if p1_ans is not None and p2_ans is not None:
            break

        prev_p1 = cur_p1
        prev_p2 = cur_p2

        sleep(0.01)

    return p1_ans, p2_ans


# PLAY AGAIN
def ask_play_again():
    clear_all()

    put_line(lcd_q1, 0, "P1: PLAY AGAIN?")
    put_line(lcd_q2, 0, "P2: PLAY AGAIN?")
    put_line(lcd_a1, 0, "A = YES")
    put_line(lcd_a2, 0, "A = YES")
    put_line(lcd_a1, 1, "B = NO")
    put_line(lcd_a2, 1, "B = NO")

    # Both players must agree to play again; either pressing B exits
    p1_vote = None
    p2_vote = None

    while True:
        if p1_vote is None:
            if p1_A.is_pressed:
                sleep(0.2)
                p1_vote = True
                put_line(lcd_q1, 2, "P1: READY!")
            elif p1_B.is_pressed:
                sleep(0.2)
                return False

        if p2_vote is None:
            if p2_A.is_pressed:
                sleep(0.2)
                p2_vote = True
                put_line(lcd_q2, 2, "P2: READY!")
            elif p2_B.is_pressed:
                sleep(0.2)
                return False

        if p1_vote and p2_vote:
            return True

        sleep(0.01)


# GAME
WIN_POINTS = 3


def run_game(lang1, lang2):
    """
    Run one trivia match. Each player gets their own question
    drawn from the same pool but displayed in their chosen language.
    Both players answer simultaneously each round.

    Returns:
        int: Winning player number (1 or 2), or 0 if tied at timeout.
    """
    p1_score = 0  # ranges from -WIN_POINTS to +WIN_POINTS
    used_indices = []

    def pick_question():
        """Pick a random unused question; reset pool if exhausted."""
        available = [i for i in range(len(questions)) if i not in used_indices]
        if not available:
            used_indices.clear()
            available = list(range(len(questions)))
        idx = random.choice(available)
        used_indices.append(idx)
        return questions[idx]

    while True:
        # Each player gets their own question this round
        q1 = pick_question()
        q2 = pick_question()

        # Pull text in each player's language
        q1_text    = q1["question_en"] if lang1 == "en" else q1["question_es"]
        q1_choices = q1["choices_en"]  if lang1 == "en" else q1["choices_es"]
        q1_correct = q1["answer"]

        q2_text    = q2["question_en"] if lang2 == "en" else q2["question_es"]
        q2_choices = q2["choices_en"]  if lang2 == "en" else q2["choices_es"]
        q2_correct = q2["answer"]

        # Show questions simultaneously
        display_question_p1(q1_text)
        display_answers_p1(q1_choices)
        display_question_p2(q2_text)
        display_answers_p2(q2_choices)

        # Wait for both players to answer
        p1_ans, p2_ans = get_both_answers(q1_correct, q2_correct)

        # Update scores
        if p1_ans == q1_correct:
            p1_score += 1
        if p2_ans == q2_correct:
            p1_score -= 1

        # Move motor depending on who got it right
        if p1_ans == q1_correct and p2_ans != q2_correct:
            motor_player1()
        elif p2_ans == q2_correct and p1_ans != q1_correct:
            motor_player2()
        else:
            sleep(0.8)  # both right or both wrong

        # Clamp score
        p1_score = max(-WIN_POINTS, min(WIN_POINTS, p1_score))

        # Check win
        if p1_score >= WIN_POINTS:
            show_message_p1("PLAYER 1 WINS!")
            show_message_p2("PLAYER 1 WINS!")
            sleep(2.0)
            return 1

        if p1_score <= -WIN_POINTS:
            show_message_p1("PLAYER 2 WINS!")
            show_message_p2("PLAYER 2 WINS!")
            sleep(2.0)
            return 2


def main():
    while True:
        clear_all()

        # Each player picks their language independently
        lang1, lang2 = choose_languages()

        run_game(lang1, lang2)

        again = ask_play_again()

        if not again:
            clear_all()
            show_message_p1("GAME OVER")
            show_message_p2("GAME OVER")
            motor_stop()
            while True:
                sleep(1)


main()

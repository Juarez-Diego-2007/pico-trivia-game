# Two-Player Trivia Game (Raspberry Pi Pico)

## Overview

This project is an embedded two-player trivia game built using a Raspberry Pi Pico.
Players compete to answer questions first using physical buttons while LCD displays present questions and answers. A DC motor visually represents score progression toward victory.

---

## Features

* Dual-player competitive gameplay
* Four I2C LCD displays
* Button-based answer input
* Motor-driven score indicator
* JSON-based question system
* Replay functionality

---

## Hardware Used

* Raspberry Pi Pico
* 4× 20x4 I2C LCD Displays
* DC Motor + Driver
* Push Buttons
* External Power Supply

---

## System Operation

1. Question displays on both player screens.
2. Players press answer buttons (A–D).
3. First correct answer moves motor toward that player.
4. First player to reach win threshold wins.

---

## File Structure

| File             | Description                |
| ---------------- | -------------------------- |
| `main.py`        | Main game logic            |
| `questions.json` | Trivia question database   |


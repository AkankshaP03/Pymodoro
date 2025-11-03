# PyModoro
Say goodbye to distractions and hello to peak productivity with Pymodoro — the ultimate Pomodoro timer + to-do tracker + lofi vibes all rolled into one sleek Python app(using Pygame)! Whether you’re coding, studying, or powering through your tasks, Pymodoro keeps you laser-focused.

---

## ✨ Features

### ✅ Pomodoro Timer Modes

| Mode | Work Duration | Break Duration | Long Break | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Traditional Mode** | 25 mins | 5 mins | 15 mins | Classic Pomodoro cycle |
| **Custom Mode** | 1–100 mins (user-set) | User-set | Optional | Fully adjustable timing system |

**Custom Timer Highlights:**
* Set any work duration between 1–100 minutes.
* Adjustable short and long breaks.
* Saves your last custom settings.
* **Perfect for:** 50/10 study cycles, deep-work blocks (60–90 mins), light focus (10–20 mins), ADHD-friendly micro-sessions, or any productivity method you prefer.

### 🎮 Productivity Controls

* ✔️ **Auto-start Pomodoro** and **Auto-start Break**
* ⏭️ **Skip** to the next Pomodoro, Short Break, or Long Break
* ⏸️ **Pause / Resume** a session
* ⏰ **Alarm** chime on session end (with optional fade-out for lofi audio)
* 🎵 **Toggle Lofi background audio**
* 🔁 **Automatic long break** after a set number of cycles
* 💾 **Session stats** saved locally

### 📝 To-Do List Integration

* Add tasks and mark them as completed.
* Track the number of **Pomodoros per task**.
* **JSON-based data storage** (no cloud connection).
* Fast, keyboard-friendly task management.

### 🎧 Audio Experience

* Built-in **lofi focus soundtrack** (toggle on/off).
* **Alarm chime** when a session completes.
* Optional audio fade-out when the alarm plays.

---

## 🧠 Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| `Space` | Start / Pause |
| `A` | Toggle Auto-Start (Pomodoro/Break) |
| `N` | Skip to next cycle |
| `P` | Skip to Pomodoro |
| `B` | Skip to Break |
| `S` | Toggle soundtrack |
| `M` | Mute alarm |
| `T` | Add task |

---

## 🎬 Demo (Screenshots/GIFs incoming)

* 📷 Timer UI (Traditional + Custom)
* 🎵 Lofi mode view
* ✅ To-do list sidebar

---

## 📦 Installation

### Requirements

* **Python 3.9+**
* **pip**

### Install Dependencies

Use the following command to install the required libraries, primarily `pygame`:

```bash
pip install pygame

```

### 🚀 Run the App

Execute the main file from your terminal:

```bash
python pomodoro.py
```

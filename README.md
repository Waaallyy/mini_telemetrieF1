# 🏎️ F1 Telemetry Comparator

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![FastF1](https://img.shields.io/badge/FastF1-E10600?style=for-the-badge&logo=formula1&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=for-the-badge&logo=python&logoColor=white)

An interactive web app to compare Formula 1 drivers' telemetry from any Grand Prix, built with real data from the [FastF1](https://docs.fastf1.dev/) library.

Select a season, a Grand Prix and two drivers, then explore their fastest laps side by side — speed, throttle, braking, gears and more — along with a speed-colored track map and a fastest/median/slowest comparison across the whole grid.

## Features

- **Driver comparison** — overlay two drivers' telemetry channels (speed, throttle, brake, RPM, gear) on the same charts to see exactly where each one gains time.
- **Track map** — the circuit drawn from real position data, colored by speed, with official corner numbers placed clearly outside the racing line.
- **Grid envelope** — compare the fastest, a median, and the slowest driver of the session, ranked by lap time.
- **Dynamic selection** — driver menus are filled automatically from the drivers actually present in the chosen session, so no invalid input is possible.

## Demo

<img width="739" height="576" alt="image" src="https://github.com/user-attachments/assets/e8d151c8-2a88-4621-9dd8-332309c3ddb2" />

## Installation

You need Python 3 installed. Then, from the project folder:

```bash
python -m pip install streamlit fastf1 matplotlib
```

## Usage

Launch the app with:

```bash
python -m streamlit run main.py
```

The app opens in your browser (or visit `http://localhost:8501`). Pick a season, Grand Prix and session, choose your drivers and channels, then click **Générer**.

> **Note:** the first time you load a session, FastF1 downloads the data, which can take a few seconds. A local `cache/` folder is created so subsequent runs are fast.

## How it works

The app relies on a few FastF1 concepts worth knowing:

- `get_car_data()` provides what happens *inside* the car (speed, RPM, throttle, brake, gear), while `get_pos_data()` gives *where* the car is on track (X, Y coordinates).
- For the track map, both sources are aligned on a common time base with `merge_channels()` so position and speed share the same number of points.
- Each driver's lap time is read from `LapTime`, used to rank the grid for the fastest/median/slowest comparison.

## Tech stack

- **Python** — core language
- **Streamlit** — turns the Python script into an interactive web app, no HTML/JS needed
- **FastF1** — official-grade F1 timing and telemetry data
- **Matplotlib** — charts and the speed-colored track map


## License

This project is for educational and portfolio purposes. F1 data is provided by FastF1 / the official F1 timing data.

#!/usr/bin/env bash
set -e

# стартуем веб-порт для Render
python web.py &

# стартуем бота
python main.py

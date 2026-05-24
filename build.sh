#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
rm -rf staticfiles/          # ← force delete old cached folder
python manage.py collectstatic --noinput
python manage.py migrate
#!/bin/sh
cd backend
gunicorn -c ../gunicorn.conf.py app:app
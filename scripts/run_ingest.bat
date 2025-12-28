@echo off
echo Starting Rail Ingest Service...
python ingest.py --baudrate 19200 --slave-id 1
pause

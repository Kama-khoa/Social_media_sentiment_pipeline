@echo off
call F:\Anaconda\Scripts\activate.bat F:\Anaconda\envs\etl-py313
python scripts\dbt\dbt_runner.py run

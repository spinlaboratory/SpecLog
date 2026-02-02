@echo off

echo Changing to script directory...
cd /d "%~dp0"

echo Using Python:
where python
python -V
echo.

echo Installing pyLogger...
python -m pip install -e .

echo.
echo Done.
pause
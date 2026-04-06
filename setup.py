import setuptools

with open('README.md','r') as f:
    long_description = f.read()

with open("SpecLog/version.py", "r") as f:
    # Define __version__
    exec(f.read())

setuptools.setup(
    name='SpecLog',
    version=__version__,
    author='Bruker BioSpin EPR Development and Innovation Team',
    author_email='yen-chun.huang@bruker.com',
    description='A Python Package for logging data from instrumentations',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
    ],
    python_requires='>=3.10',
    install_requires=['matplotlib >= 3.7.1', 'numpy >= 1.24.3', 'PySide6 >= 6.9.0', 'pyqtgraph >= 0.13.3', 'spinlab >= 1.1.3', 'pyvisa >= 1.16.1', 'pyserial >= 3.5'],
    entry_points = dict(
        gui_scripts = [
            "SpecMonitor = SpecLog.run_monitor:main_func",
        ],
        console_scripts = [
            "SpecLogger = SpecLog.SpecLogger:main_func",
            "SpecMonitor_debug = SpecLog.run_monitor:main_func",            
            "SpecLogger_running = SpecLog.run_logger:main_func",
        ],
    ),
    package_data={"SpecLog": ["config/command.cfg", "config/config.cfg", "config/serial.cfg", "ui/plotting.ui"]},
)
import setuptools

with open('README.md','r') as f:
    long_description = f.read()

with open("pyB12LOG/version.py", "r") as f:
    # Define __version__
    exec(f.read())

setuptools.setup(
    name='pyB12LOG',
    version=__version__,
    author='Bridge12 Technologies, Inc',
    author_email='yhuang@bridge12.com',
    description='A Python Package for logging data from instrumentations',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='http://www.bridge12.com/',
    project_urls={
        'Source Code':'https://github.com/Bridge12Technologies/pyB12LOG',
        'Documentation':'http://pyb12log.bridge12.com',
        },
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
    ],
    python_requires='>=3.6',
    install_requires=['pyvisa', 'matplotlib'],
    entry_points = dict(
        gui_scripts = [
            "pyB12plotter = pyB12LOG.run_plotter:main_func",
            "pyB12logger_running = pyB12LOG.run_logger:main_func",
        ],
        console_scripts = [
            "pyB12logger = pyB12LOG.pyB12logger:main_func",
            "pyB12plotter_debug = pyB12LOG.run_plotter:main_func",            
            "pyB12logger_debug = pyB12LOG.run_logger:main_func",
        ],
    ),
    package_data={"pyB12LOG": ["config/command.cfg", "config/config.cfg", "config/serial.cfg"]},
    data_files = [('share/application', ['config.cfg'])],
)
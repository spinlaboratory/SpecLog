import os

def main_func():
    os.system("taskkill /im pyB12logger.exe /F")
    print('pyB12logger has been terminated.')


if __name__ == '__main__':
    main_func()
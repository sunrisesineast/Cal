
from setuptools import setup

setup(
    name='cal-tracker',
    version='0.1.0',
    py_modules=['cal'],
    install_requires=[
        'typer[all]',
        'rich',
        'typer-config',
    ],
    entry_points='''
        [console_scripts]
        cal=cal:app
    '''
)

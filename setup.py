from setuptools import setup, find_packages

setup(
    name='copilot-accounting',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'click>=8.1.0',
        'psycopg2-binary>=2.9.0',
        'python-dotenv>=1.0.0',
        'rich>=13.0.0',
    ],
    entry_points={
        'console_scripts': [
            'copilot=copilot.cli:cli',
        ],
    },
)

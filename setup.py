# D:\serp-analyzer\setup.py
from setuptools import setup
from pathlib import Path

long_description = Path("README.md").read_text(encoding="utf-8")

setup(
    name="serp-analyzer",
    version="1.0.0",
    description="SERP Type Analyzer CLI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="David Forer",
    author_email="david.j.forer@gmail.com",
    package_dir={"": "src"},  # treat src as import root
    py_modules=[
        "cli",
        "serper_search",
        "intent_detector",
        "classifier",
        "output_writer",
    ],
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        # add "openai==0.28.1" later when you actually call it
    ],
    entry_points={"console_scripts": ["serp-analyzer=cli:main"]},
)

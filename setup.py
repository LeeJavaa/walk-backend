from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="walk",
    version="0.1.0",
    author="Lawrence Godfrey, Lee Johnson",
    author_email="lawrences.email@gmail.com, leejavaa@gmail.com",
    description="An agentic coding system that generates production-ready code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/leejavaa/walk-backend",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.13",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "walk=src.infrastructure.cli.main:main",
        ],
    },
)
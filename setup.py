"""Setup script for Wizardry agent orchestrator."""

from setuptools import setup, find_packages

with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="wizardry",
    version="0.1.0",
    description="Multi-agent workflow orchestrator using Claude Code sub-agents",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "wizardry=wizardry.cli:cli",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
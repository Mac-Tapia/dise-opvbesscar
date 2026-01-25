"""
Setup configuration for PVBESSCAR package
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pvbesscar",
    version="1.0.0",
    author="Energy Systems Lab",
    description="RL-based building energy management system with PV, BESS, and EV charging",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Mac-Tapia/dise-opvbesscar",
    package_dir={"": "src"},
    packages=find_packages("src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11,<3.12",
    install_requires=[
        "stable-baselines3>=2.0",
        "gymnasium>=0.28",
        "numpy>=1.21",
        "pandas>=1.3",
        "matplotlib>=3.5",
        "scipy>=1.7",
        "citylearn>=1.6",
    ],
)

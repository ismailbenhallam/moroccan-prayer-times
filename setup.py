from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="moroccan_prayer_times",
    version="0.0.10",
    author="Ismail BENHALLAM",
    author_email="ismailben44@gmail.com",
    packages=find_packages(),
    install_requires=requirements,
    description="Moroccan Prayer Times CLI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=["prayer times", "prayer_times", "prayer", "morocco"],
    url="https://github.com/ismailbenhallam/prayer-times-cli/",
    entry_points={
        "console_scripts": [
            "prayertime=src.main:main",
        ],
    },
    classifiers=[
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)

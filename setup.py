from setuptools import setup, find_packages
from moroccan_prayer_times import __version__

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="moroccan_prayer_times",
    version=__version__,
    author="Ismail BENHALLAM",
    author_email="ismailben44@gmail.com",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "moroccan_prayer_times": ["translations/*.yml"],
    },
    install_requires=requirements,
    description="Moroccan Prayer Times CLI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=["prayer times", "prayer_times", "prayer", "morocco"],
    url="https://github.com/ismailbenhallam/moroccan-prayer-times/",
    entry_points={
        "console_scripts": [
            "prayertime=moroccan_prayer_times.main:main",
        ],
    },
    classifiers=[
        "Environment :: Console",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
)

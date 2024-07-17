"""Setup file."""

from setuptools import setup, find_packages

setup(
    name="star_ray_xml",
    version="0.0.3",
    author="Benedict Wilkins",
    author_email="benrjw@gmail.com",
    description="An extension to the [star_ray](https://github.com/dicelab-rhul/star-ray) platform that uses XML as a description language for the state of an environment. Agents may use [xpath](https://www.w3schools.com/xml/xpath_intro.asp) expressions to query (read/write) to the state.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    url="https://github.com/dicelab-rhul/star-ray-xml",
    install_requires=[
        "star_ray>=0.0.4",
        "lxml",
        "pydantic",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3.10",
    ],
)

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="newyorker",
    description="Search by keywords and download cartoons from The New Yorker magazine cartoon gallery",
    version="1.1.0",
    author="Demon of the Second Kind",
    author_email="demonofthe2ndkind@sevanya.com",
    license="Apache Software License",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Demonofthe2ndkind/new-yorker.git",
    packages=setuptools.find_packages(),
    package_data={"tests": ["data/test_data.yaml"]},
    install_requires=[
        "beautifulsoup4>=4.9.1",
        "requests>=2.24.0"
    ],
    tests_require=[
        "pyyaml>=5.3.1",
        "requests>=2.24.0"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": ["newyorker=newyorker.cartoons:main"]
    },
    python_requires=">=3.8"
)

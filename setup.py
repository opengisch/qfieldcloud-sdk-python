import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("VERSION", "r", encoding="utf-8") as fh:
    version = fh.read().strip()

setuptools.setup(
    name="qfieldcloud-sdk",
    version=version,
    author="Ivan Ivanov",
    author_email="ivan@opengis.ch",
    description="The official QFieldCloud SDK and CLI.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/opengisch/qfieldcloud-sdk-python",
    project_urls={
        "Bug Tracker": "https://github.com/opengisch/qfieldcloud-sdk-python/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "click>=8",
        "requests>=2.0",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="liteshort",
    version="1.2.0",
    author="Steven Spangler",
    author_email="132@ikl.sh",
    description="User-friendly, actually lightweight, and configurable URL shortener",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/132ikl/liteshort",
    packages=setuptools.find_packages(),
    package_data={"liteshort": ["templates/*", "static/*", "config.template.yml"]},
    entry_points={
        "console_scripts": [
            "liteshort = liteshort.main:app.run",
            "lshash = liteshort.util:hash_passwd",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    install_requires=["flask~=1.1.2", "bcrypt~=3.1.7", "pyyaml", "appdirs~=1.4.3"],
    python_requires=">=3.7",
)

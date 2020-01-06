import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="persistentSSH-misterpah",
    version="0.1.0",
    author="misterpah",
    author_email="misterpah@gmail.com",
    description="Paramiko + screen = Persistent SSH",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/misterpah/persistent_ssh",
    packages=setuptools.find_packages(),
    install_requires=[
        "paramiko"
    ]
)


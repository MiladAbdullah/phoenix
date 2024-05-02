import setuptools

# with open("README.md", "r") as fh:
#     long_description = fh.read()

setuptools.setup(
    name="graal",
    version="1.0.0",
    author='Milad Abdullah',
    author_email='abdullah@d3s.mff.cuni.cz',
    description='GraalVM Performance Testing Automation Database',
    #long_description=long_description,
    #long_description_content_type="text/markdown",
    #url='https://github.com/smartarch/ml_deeco',
    keywords=[],
    packages=setuptools.find_packages(),
#     classifiers=[
#         "Programming Language :: Python :: 3",
#         "License :: OSI Approved :: MIT License",
#         "Operating System :: OS Independent",
#     ],
    python_requires='>=3.10',
    install_requires=[  ],
)
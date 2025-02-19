import setuptools

setuptools.setup(
    name="simulation",
    version="2.0.0",
    author='Milad Abdullah',
    author_email='abdullah@d3s.mff.cuni.cz',
    description='GraalVM Performance Testing Automation Simulation',
    keywords=[],
    packages=setuptools.find_packages(),
    python_requires='>=3.12',
    install_requires=['requests', 'pandas'],
)
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="frc1678-lime-plotter",
    version="0.6.6",
    author="Wes Hardaker",
    author_email="opensource@hardakers.net",
    description="A matplotlib based plotter for FRC logs and networktables",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/frc1678/lime-plotter",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'lime-plotter = frc1678.limeplotter.main:main',
            'lime-server = frc1678.limeplotter.networktablesserver:main',
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires = '>=3',
    install_requires=[
        'pynetworktables',
        'numpy',
        'pandas',
        'pyyaml',
        'matplotlib',
        'svgpath2mpl',
    ],
    test_suite='nose.collector',
    tests_require=['nose'],
    package_data = { 'frc1678.limeplotter.loader': ['svgs/2021.svg',
                                                    'svgs/2020map.svg',
                                                    'svgs/2020map-rev.svg',
                                                    'svgs/2020map-full.svg',
                                                    'svgs/2019map.svg'] },
)

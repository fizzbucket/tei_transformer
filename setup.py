from setuptools import setup, find_packages

setup(
    # Application name:
    name="tei_transformer",

    # Version number (initial):
    version="0.2.4",

    # Application author details:
    author="Tom McLean",
    author_email="thomasowenmclean@gmail.com",

    # Packages
    packages=["tei_transformer"],

    # Include additional files into the package
    include_package_data=True,
    package_data = {'tei_transformer': ['config.yaml']},

    entry_points={
    	'console_scripts': [
    	'tei_transformer=tei_transformer.tei_transformer_script:main',
    	]
    },

    # Details
    url="https://github.com/thomasowenmclean/tei_transformer",

    #
    license="GPL",
    description="Transform a TEI-encoded critical edition into a print-ready file.",

    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
		'Topic :: Text Processing :: Markup :: LaTeX',
        'Topic :: Text Processing :: Markup :: XML',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
    ],

    keywords='TEI critical edition xml transform scholarly diplomatic latex xml',

    # long_description=open("README.txt").read(),
    # Dependent packages (distributions)
    install_requires=[
        "lxml",
        "latexfixer",
        "path.py",
        "PyYAML"
    ],
)
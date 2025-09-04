from setuptools import setup, find_packages

setup(
    name='Total Leave Days',  # Required: Name of your package
    version='0.1.0',          # Required: Package version
    author='wiz',       # Optional: Author name
    author_email='wisdommapeka@gmail.com',  # Optional: Author email
    description='Total Number Of Leave Days Calculation',  # Optional: Description
    long_description=open('README.md').read(),  # Optional: Long description from README
    long_description_content_type='text/markdown',  # Optional: Format of long description
    url='https://github.com/WisdomMapeka/totalleavdays.git',  # Optional: URL for the project
    packages=find_packages(),  # Automatically find packages in the directory
    classifiers=[  # Optional: Classifiers for PyPI
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',  # Optional: Specify Python version
    install_requires=[  # Optional: List of dependencies
    ],
)
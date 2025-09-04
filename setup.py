from setuptools import setup, find_packages

setup(
    name='totalleavdays',  # Use hyphens instead of spaces
    version='0.1.0',          # Required: Package version
    author='Wiz',             # Optional: Author name (capitalize if desired)
    author_email='wisdommapeka@gmail.com',  # Optional: Author email
    description='Total Number of Leave Days Calculation',  # Optional: Description
    long_description=open('README.md').read(),  # Ensure README.md exists
    long_description_content_type='text/markdown',  # Optional: Format of long description
    url='https://github.com/WisdomMapeka/totalleavdays',  # Ensure the URL is correct
    packages=find_packages(),  # Automatically find packages in the directory
    classifiers=[  # Optional: Classifiers for PyPI
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',  # Optional: Specify Python version
    install_requires=[],  # List of dependencies (add as needed)
)
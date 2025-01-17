from setuptools import setup, find_packages

NAME = 'batch-edits'
DESCRIPTION = ''
VERSION = '1.0.4'

with open("README.md") as f:
    long_description = f.read()
    
with open("requirements.txt") as f:
    requirements = list(filter(None,f.read().split('\n')))

setup(
    name = NAME,
    version = VERSION,
    #url = '',
    author = 'United Nations Dag Hammarskjöld Library',
    author_email = 'library-ny@un.org',
    license = 'http://www.opensource.org/licenses/bsd-license.php',
    packages = find_packages(exclude=['test']),
    test_suite = 'tests',
    install_requires = requirements,
    description = DESCRIPTION,
    long_description = long_description,
    long_description_content_type = "text/markdown",
    python_requires = '>=3.8',
    entry_points = {
        # see https://python-packaging.readthedocs.io/en/latest/command-line-scripts.html#the-console-scripts-entry-point
        'console_scripts': [
            'batch-edit=batch_edits.scripts.batch_edit:run'
        ]
    }
)


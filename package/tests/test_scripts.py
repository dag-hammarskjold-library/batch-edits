import sys
from package.scripts import script

def test_script():
    sys.argv = ['--arg=test']
    script.run()
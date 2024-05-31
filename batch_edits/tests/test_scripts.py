import sys
from batch_edits.scripts import batch_edit

def test_script():
    sys.argv = ['--arg=test']
    batch_edit.run()

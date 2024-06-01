# set up pytest fixtures 
# here https://docs.pytest.org/en/7.1.x/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files

import os, pytest
from dlx import DB
from dlx.marc import Bib

@pytest.fixture
def bibs():
    DB.connect('mongomock://localhost')
    
    for _ in range(0, 10):
        bib = Bib()
        bib.set('089', 'b', 'A01')
        bib.commit()

    for _ in range(0, 10):
        bib = Bib()
        bib.set('089', 'b', 'B22')
        bib.commit()

    for _ in range(0, 10):
        bib = Bib()
        bib.set('089', 'b', 'B23')
        bib.commit()

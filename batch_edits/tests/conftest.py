# set up pytest fixtures 
# here https://docs.pytest.org/en/7.1.x/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files

import pytest

@pytest.fixture
def _():
    return 
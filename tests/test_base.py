import pytest

from job_board.portals.base import BasePortal


def test_abstract_methods():
    with pytest.raises(NotImplementedError):
        BasePortal().make_request()

    with pytest.raises(NotImplementedError):
        BasePortal().get_items(response={})

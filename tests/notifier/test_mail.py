from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from job_board.notifier.mail import EmailProvider


@pytest.fixture
def mock_service():
    with patch(
        "job_board.notifier.mail.build",
        return_value=MagicMock(),
    ) as mock_build:
        yield mock_build.return_value


@pytest.fixture
def email_provider(mock_service):
    with patch(
        "job_board.notifier.mail.service_account.Credentials.from_service_account_file",
        return_value=MagicMock(),
    ):
        yield EmailProvider()


def test_send_email_success(email_provider, mock_service):
    assert email_provider is not None

    with patch.object(
        mock_service.users().messages().send(),
        "execute",
        return_value={"id": "12345"},
    ) as mock_send:
        response = email_provider.send_email(
            sender="test@example.com",
            receivers=["someone@example.com", "someone-else@example.com"],
            subject="Test Email",
            body="<p>Hello, this is a test.</p>",
        )

    assert response == {"id": "12345"}
    mock_send.assert_called_once()

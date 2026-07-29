from app.tools.email_sender import send_email


def test_send_email_returns_confirmation():
    result = send_email(to="a@example.com", subject="Hi", body="Hello there")
    assert result == "Mock email sent to a@example.com (subject: 'Hi')"


def test_send_email_logs_instead_of_sending(caplog):
    with caplog.at_level("INFO"):
        send_email(to="a@example.com", subject="Hi", body="Hello there")
    assert "a@example.com" in caplog.text
    assert "Hello there" in caplog.text

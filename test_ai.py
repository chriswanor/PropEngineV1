from unittest.mock import Mock
from src.underwriter.ai import report_generator


def test_generate_ai_report_uses_client_and_returns_content():
    # Arrange
    fake_client = Mock()
    fake_response = Mock()
    fake_choice = Mock()
    fake_message = Mock()
    fake_message.content = "Sample AI report content"
    fake_choice.message = fake_message
    fake_response.choices = [fake_choice]
    fake_client.chat.completions.create.return_value = fake_response

    metrics = {"levered_irr": 0.18}
    sensitivity = {"rent": "+10% -> IRR +2%"}

    # Act
    report = report_generator.generate_ai_report(metrics, sensitivity, client=fake_client)

    # Assert
    assert "Sample AI report content" in report
    fake_client.chat.completions.create.assert_called_once()


def test_generate_ai_report_env_api_key(monkeypatch):
    # Arrange
    class DummyClient:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.chat = Mock()
            self.chat.completions = Mock()
            self.chat.completions.create = Mock(return_value=Mock(choices=[Mock(message=Mock(content="ok"))]))

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Patch the OpenAI constructor inside report_generator
    original_cls = report_generator.OpenAI
    report_generator.OpenAI = DummyClient  # type: ignore

    try:
        out = report_generator.generate_ai_report({}, {})
        assert out == "ok"
    finally:
        report_generator.OpenAI = original_cls  # restore


def test_generate_ai_report_missing_key_raises(monkeypatch):
    # Arrange
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Act / Assert
    try:
        report_generator.generate_ai_report({}, {})
        assert False, "Expected ValueError when API key is missing"
    except ValueError as e:
        assert "Missing OpenAI API key" in str(e)
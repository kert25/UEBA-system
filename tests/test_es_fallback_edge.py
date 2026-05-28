"""Tests for ES fallback edge cases."""

from unittest.mock import MagicMock, patch

from shared.es_health import is_es_available


def test_is_es_available_returns_false_when_not_connected() -> None:
    """Test that is_es_available returns False when ES is not reachable."""
    result = is_es_available()
    assert result is False


def test_is_es_available_ping_error() -> None:
    """Test that ping failure returns False."""
    mock_client = MagicMock()
    mock_client.ping.side_effect = Exception("Ping failed")

    with patch("shared.es_health.get_es_client", return_value=mock_client):
        result = is_es_available()
        assert result is False


def test_is_es_available_ping_success() -> None:
    """Test that successful ping returns True."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch("shared.es_health.get_es_client", return_value=mock_client):
        result = is_es_available()
        assert result is True


def test_is_es_available_client_error() -> None:
    """Test that client creation failure returns False."""
    with patch("shared.es_health.get_es_client", side_effect=ConnectionError("No connection")):
        result = is_es_available()
        assert result is False

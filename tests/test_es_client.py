"""Tests for ES client and index management."""

from unittest.mock import MagicMock, patch

from shared.es_client import MAPPINGS, ensure_indices


class TestEnsureIndices:
    """Tests for ensure_indices function."""

    def test_ensure_indices_creates_missing(self) -> None:
        """Test that missing indices are created."""
        mock_client = MagicMock()
        mock_client.indices.exists.return_value = False

        ensure_indices(mock_client)

        calls = mock_client.indices.create.call_args_list
        assert len(calls) == len(MAPPINGS)
        mock_client.indices.create.assert_called()

    def test_ensure_indices_skips_existing(self) -> None:
        """Test that existing indices are skipped."""
        mock_client = MagicMock()
        mock_client.indices.exists.return_value = True

        ensure_indices(mock_client)

        mock_client.indices.create.assert_not_called()

    def test_ensure_indices_handles_creation_error(self) -> None:
        """Test graceful handling of creation errors."""
        mock_client = MagicMock()
        mock_client.indices.exists.return_value = False
        mock_client.indices.create.side_effect = Exception("Creation failed")

        ensure_indices(mock_client)

        mock_client.indices.create.assert_called()

    def test_ensure_indices_default_client(self) -> None:
        """Test that default client is created when None."""
        with patch("shared.es_client.get_es_client") as mock_get:
            mock_client = MagicMock()
            mock_client.indices.exists.return_value = True
            mock_get.return_value = mock_client

            ensure_indices()

            mock_get.assert_called_once()

    def test_mappings_full_coverage(self) -> None:
        """Test that all expected indices have mappings."""
        expected = {"events", "features", "profiles", "anomalies", "incidents"}
        assert set(MAPPINGS.keys()) == expected

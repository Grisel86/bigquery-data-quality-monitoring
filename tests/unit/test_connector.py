"""Unit tests for src/connector.py.

We mock the BigQuery client entirely — these tests verify that the connector
constructs the right queries, validates inputs, and handles responses
correctly. NOT that BigQuery itself works (integration tests cover that).
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.connector import BigQueryConnector, _validate_identifier


class TestBigQueryConnector:
    """Tests for the BigQueryConnector class."""

    def test_query_to_dataframe_returns_expected_data(self, mock_bq_client):
        connector = BigQueryConnector(
            project_id="test-project", client=mock_bq_client
        )
        df = connector.query_to_dataframe("SELECT 1")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        mock_bq_client.query.assert_called_once_with("SELECT 1")

    def test_fetch_table_builds_correct_sql(self, mock_bq_client):
        connector = BigQueryConnector(
            project_id="test-project", client=mock_bq_client
        )
        connector.fetch_table("my_dataset", "my_table")
        call_args = mock_bq_client.query.call_args[0][0]
        assert "FROM `test-project.my_dataset.my_table`" in call_args
        assert "SELECT *" in call_args

    def test_fetch_table_with_specific_columns(self, mock_bq_client):
        connector = BigQueryConnector(
            project_id="test-project", client=mock_bq_client
        )
        connector.fetch_table(
            "my_dataset", "my_table", columns=["customer_id", "email"]
        )
        sql = mock_bq_client.query.call_args[0][0]
        assert "SELECT customer_id, email" in sql

    def test_fetch_table_with_limit(self, mock_bq_client):
        connector = BigQueryConnector(
            project_id="test-project", client=mock_bq_client
        )
        connector.fetch_table("my_dataset", "my_table", limit=100)
        sql = mock_bq_client.query.call_args[0][0]
        assert "LIMIT 100" in sql

    def test_limit_is_integer_coerced(self, mock_bq_client):
        """Guard against SQL injection — limit is always int-cast."""
        connector = BigQueryConnector(
            project_id="test-project", client=mock_bq_client
        )
        connector.fetch_table("ds", "t", limit=50)
        sql = mock_bq_client.query.call_args[0][0]
        assert "LIMIT 50" in sql


class TestValidateIdentifier:
    """Tests for _validate_identifier — security-critical input validation."""

    # ===== Happy path =====
    def test_accepts_simple_identifier(self):
        assert _validate_identifier("customer_id", "column") == "customer_id"

    def test_accepts_identifier_with_underscores_and_digits(self):
        assert _validate_identifier("col_123_abc", "column") == "col_123_abc"

    def test_accepts_identifier_starting_with_underscore(self):
        assert _validate_identifier("_private", "column") == "_private"

    # ===== Rejection of injection attempts =====
    @pytest.mark.parametrize(
        "malicious_input",
        [
            "users; DROP TABLE customers;--",
            "col' OR '1'='1",
            "col`backtick",
            "col with spaces",
            "col-with-dashes",
            "col.with.dots",
            "col,comma",
            "col(parens)",
            "col\"quotes",
            "col\nnewline",
            "col\ttab",
        ],
    )
    def test_rejects_injection_attempts(self, malicious_input):
        with pytest.raises(ValueError, match="Invalid"):
            _validate_identifier(malicious_input, "column")

    # ===== Edge cases =====
    def test_rejects_empty_string(self):
        with pytest.raises(ValueError):
            _validate_identifier("", "column")

    def test_rejects_starting_with_digit(self):
        with pytest.raises(ValueError):
            _validate_identifier("1column", "column")

    def test_error_message_includes_kind(self):
        with pytest.raises(ValueError, match="column"):
            _validate_identifier("bad name", "column")
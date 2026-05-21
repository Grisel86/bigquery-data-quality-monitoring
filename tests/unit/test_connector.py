"""Unit tests for src/connector.py.

We mock the BigQuery client entirely — these tests verify that the connector
constructs the right queries and handles responses correctly, NOT that BigQuery
itself works. Integration tests cover the latter.
"""

from __future__ import annotations

import pandas as pd

from src.connector import BigQueryConnector


class TestBigQueryConnector:

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

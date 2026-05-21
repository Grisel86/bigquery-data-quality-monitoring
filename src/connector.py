import re

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(name: str, kind: str = "identifier") -> str:
    """Reject anything that isn't a plain SQL identifier."""
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {kind} name: {name!r}")
    return name


class BigQueryConnector:
    # ... __init__ and query_to_dataframe unchanged ...

    def fetch_table(
            self,
            dataset: str,
            table: str,
            columns: list[str] | None = None,
            limit: int | None = None,
    ) -> pd.DataFrame:
        """Pull a table (or column subset) into a DataFrame."""
        _validate_identifier(dataset, "dataset")
        _validate_identifier(table, "table")
        if columns:
            for col in columns:
                _validate_identifier(col, "column")
            col_expr = ", ".join(columns)
        else:
            col_expr = "*"

        limit_clause = f"LIMIT {int(limit)}" if limit else ""

        # B608: identifiers are validated above; LIMIT is int-coerced.
        # BigQuery cannot parameterize identifiers, so f-string SQL is
        # unavoidable here.
        sql = (
            f"SELECT {col_expr} "  # nosec B608
            f"FROM `{self.project_id}.{dataset}.{table}` "
            f"{limit_clause}"
        )
        return self.query_to_dataframe(sql)
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import pyodbc

from mapper.utils.routes import DATABASE_ASSETS_MAPPING_PATH


@dataclass(frozen=True)
class DatabaseConnection:
    """Immutable database connection configuration."""

    connection_string: str


class AssetsMapper:
    """Extract all queries and tables from AssetsMapping.accdb into DataFrames.

    Singleton pattern: ensures only one instance is created and data is cached
    to avoid repeated database connections and queries.
    """

    _instance: "AssetsMapper" = None
    _materialized: bool = False

    def __new__(cls, db_path: str | Path = DATABASE_ASSETS_MAPPING_PATH):
        """Implement singleton pattern - return existing instance if available."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(db_path)
        return cls._instance

    def _initialize(self, db_path: str | Path) -> None:
        """Initialize extractor with database path (called only once)."""
        self.db_path = Path(db_path) / "AssetsMapping.accdb"
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        self.connection: DatabaseConnection | None = None
        self.conn: pyodbc.Connection | None = None
        self.queries: dict[str, pd.DataFrame] = {}
        self.tables: dict[str, pd.DataFrame] = {}

    def materialize(self) -> dict[str, dict[str, pd.DataFrame]]:
        """Load all queries and tables from database and return as DataFrames.

        Returns cached data on subsequent calls (singleton pattern).
        """
        # Return cached data if already materialized
        if self.__class__._materialized and self.queries and self.tables:
            return {"queries": self.queries, "tables": self.tables}

        # Load data on first call
        self._connect()
        self._extract_queries()
        self._extract_tables()
        self._disconnect()

        # Mark as materialized
        self.__class__._materialized = True

        self.assets_data = {"queries": self.queries, "tables": self.tables}

        return self.assets_data

    def _connect(self) -> None:
        """Establish connection to Access database."""
        connection_string = (
            f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};"
            f"DBQ={self.db_path};"
        )
        try:
            self.conn = pyodbc.connect(connection_string)
            self.connection = DatabaseConnection(connection_string=connection_string)
        except pyodbc.Error as e:
            raise ConnectionError(f"Failed to connect to database: {e}")

    def _extract_queries(self) -> None:
        """Extract all queries from database."""
        if not self.conn:
            raise RuntimeError("Not connected to database")

        try:
            cursor = self.conn.cursor()
            query_names = self._get_query_names(cursor)

            for query_name in query_names:
                try:
                    df = pd.read_sql(f"SELECT * FROM [{query_name}]", self.conn)
                    df.columns = [
                        self._lowercase_first_letter(str(col)) for col in df.columns
                    ]
                    self.queries[query_name] = df
                except Exception as e:
                    print(f"Warning: Failed to extract query '{query_name}': {e}")

        except pyodbc.Error as e:
            raise RuntimeError(f"Error extracting queries: {e}")

    def _extract_tables(self) -> None:
        """Extract all tables from database."""
        if not self.conn:
            raise RuntimeError("Not connected to database")

        try:
            cursor = self.conn.cursor()
            table_names = self._get_table_names(cursor)

            for table_name in table_names:
                try:
                    df = pd.read_sql(f"SELECT * FROM [{table_name}]", self.conn)
                    df.columns = [
                        self._lowercase_first_letter(str(col)) for col in df.columns
                    ]
                    self.tables[table_name] = df
                except Exception as e:
                    print(f"Warning: Failed to extract table '{table_name}': {e}")

        except pyodbc.Error as e:
            raise RuntimeError(f"Error extracting tables: {e}")

    def _get_query_names(self, cursor: pyodbc.Cursor) -> list[str]:
        """Retrieve all query names from Access database."""
        query_names = []

        for row in cursor.tables():
            name = row.table_name
            table_type = row.table_type
            if not name.startswith("MSys") and table_type == "VIEW":
                query_names.append(name)

        return query_names

    def _get_table_names(self, cursor: pyodbc.Cursor) -> list[str]:
        """Retrieve all table names from Access database, including linked tables."""
        table_names = []

        for row in cursor.tables():
            name = row.table_name
            table_type = row.table_type
            # Include regular tables and linked tables (SYNONYM)
            if not name.startswith("MSys") and (
                table_type == "TABLE" or table_type == "SYNONYM"
            ):
                table_names.append(name)

        return table_names

    def _disconnect(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
        self.connection = None

    def get_query(self, query_name: str) -> pd.DataFrame | None:
        """Retrieve a specific query DataFrame."""
        return self.queries.get(query_name)

    @staticmethod
    def _lowercase_first_letter(text: str) -> str:
        """Convert first letter to lowercase, keep rest as-is."""
        text = str(text).strip()

        if not text or text == "nan":
            return text

        return text[0].lower() + text[1:]


if __name__ == "__main__":
    extractor = AssetsMapper()
    result = extractor.materialize()
    all_queries = result["queries"]
    all_tables = result["tables"]

    print(f"Extracted {len(all_queries)} queries:")
    for name, df in all_queries.items():
        print(f"  - {name}: {len(df)} rows × {len(df.columns)} columns")
        print(f"    Columns: {list(df.columns)}")

    print(f"\nExtracted {len(all_tables)} tables:")
    for name, df in all_tables.items():
        print(f"  - {name}: {len(df)} rows × {len(df.columns)} columns")
        print(f"    Columns: {list(df.columns)}")

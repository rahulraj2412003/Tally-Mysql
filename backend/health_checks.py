"""Executable connectivity checks shared by future API health endpoints."""

from backend.services.connection_service import check_mysql_connection, check_tally_connection


def main() -> None:
    ledger_count = check_tally_connection()
    print(f"Tally connection successful; {ledger_count} ledgers parsed.")
    check_mysql_connection()
    print("MySQL connection successful.")


if __name__ == "__main__":
    main()

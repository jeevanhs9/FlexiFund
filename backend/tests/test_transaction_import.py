"""Regression tests for Phase 8 CSV statement ingestion."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from app.database import create_tables, get_engine, session_scope
from app.models import ImportedTransaction, User


STANDARD_CSV = b"""date,description,debit,credit,balance,reference_id,payment_mode
2026-11-20,HP PETROL PUMP,300,0,9500,TXN001,UPI
2026-11-20,SWIGGY,250,0,9250,TXN002,UPI
2026-11-20,CLIENT PAYMENT,0,1800,11050,TXN003,UPI
"""


class TransactionImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "imports-test.db"
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "transaction-import-test-secret-0123456789abcdef",
                "SESSION_COOKIE_SECURE": False,
                "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
                "FRONTEND_URL": "http://localhost:5173",
                "MAX_BANK_CSV_ROWS": 20,
            }
        )
        create_tables(self.app)
        with self.app.app_context(), session_scope() as session:
            self.user_a = User(
                name="Import A",
                email="import-a@example.test",
                password_hash=generate_password_hash("Import-A-password-123!", method="scrypt"),
            )
            self.user_b = User(
                name="Import B",
                email="import-b@example.test",
                password_hash=generate_password_hash("Import-B-password-123!", method="scrypt"),
            )
            session.add_all([self.user_a, self.user_b])
            session.flush()
            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id
        self.client = self.app.test_client()
        self.headers = self.login(self.client, "import-a@example.test", "Import-A-password-123!")

    def tearDown(self):
        get_engine(self.app).dispose()
        self.temporary_directory.cleanup()

    def login(self, client, email, password):
        response = client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.get_json())
        return {"X-CSRF-Token": response.get_json()["data"]["csrf_token"]}

    def post_file(self, endpoint, content=STANDARD_CSV, filename="statement.csv", *, client=None, headers=None):
        return (client or self.client).post(
            endpoint,
            data={"file": (BytesIO(content), filename)},
            headers=headers or self.headers,
            content_type="multipart/form-data",
        )

    def test_preview_maps_common_headers_and_classifies_without_persisting(self):
        response = self.post_file("/api/transactions/preview")
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()["data"]
        self.assertEqual(data["total_rows"], 3)
        self.assertEqual(data["valid_rows"], 3)
        self.assertEqual(data["mapping"]["transaction_date"], "date")
        self.assertEqual(data["transactions"][0]["category"], "Transportation")
        self.assertEqual(data["transactions"][0]["subcategory"], "Fuel")
        self.assertTrue(data["transactions"][0]["needs_review"])
        self.assertEqual(data["transactions"][1]["category"], "Food")
        self.assertEqual(data["transactions"][2]["transaction_type"], "Income")
        with self.app.app_context(), session_scope() as session:
            self.assertEqual(session.query(ImportedTransaction).count(), 0)

    def test_import_updates_existing_income_expense_pipeline_and_skips_overlaps(self):
        first = self.post_file("/api/transactions/import")
        self.assertEqual(first.status_code, 201, first.get_json())
        batch = first.get_json()["data"]
        self.assertEqual(batch["imported_rows"], 3)
        self.assertEqual(batch["duplicate_rows"], 0)
        self.assertEqual(batch["review_rows"], 1)

        dashboard = self.client.get("/api/dashboard?month=11&year=2026")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.get_json()["data"]["total_income"], 1800)
        self.assertEqual(dashboard.get_json()["data"]["total_expenses"], 550)

        overlapping = self.post_file("/api/transactions/import")
        self.assertEqual(overlapping.status_code, 201, overlapping.get_json())
        overlap_data = overlapping.get_json()["data"]
        self.assertEqual(overlap_data["imported_rows"], 0)
        self.assertEqual(overlap_data["duplicate_rows"], 3)

        records = self.client.get(f"/api/transactions/imports/{batch['id']}/transactions")
        self.assertEqual(records.status_code, 200)
        self.assertEqual(len(records.get_json()["data"]), 3)

    def test_alternative_bank_headers_and_missing_date_validation(self):
        alternative = b"""Txn Date,Narration,Withdrawal,Deposit,Closing Balance,Ref No,Payment Mode
20/11/2026,UBER TRIP,220,0,8780,ALT001,UPI
"""
        response = self.post_file("/api/transactions/preview", alternative)
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()["data"]
        self.assertEqual(data["mapping"]["transaction_date"], "Txn Date")
        self.assertEqual(data["mapping"]["debit"], "Withdrawal")
        self.assertEqual(data["transactions"][0]["category"], "Transportation")

        malformed = b"""Narration,Debit,Credit
SWIGGY,250,0
"""
        bad = self.post_file("/api/transactions/preview", malformed)
        self.assertEqual(bad.status_code, 400)
        self.assertIn("date column", bad.get_json()["message"])

    def test_fallback_fingerprint_protects_repeat_upload_without_reference_id(self):
        no_reference = b"""Date,Description,Debit,Credit,Balance
2026-11-21,Electricity Bill,850,0,8650
"""
        self.assertEqual(self.post_file("/api/transactions/import", no_reference).status_code, 201)
        repeated = self.post_file("/api/transactions/import", no_reference)
        self.assertEqual(repeated.status_code, 201)
        self.assertEqual(repeated.get_json()["data"]["duplicate_rows"], 1)

    def test_transfer_unknown_and_user_correction_flow_into_analysis(self):
        statement = b"""Date,Description,Debit,Credit,Balance,Reference No
2026-11-22,Own Account Transfer,400,0,8250,TR001
2026-11-22,CREDIT INTEREST,0,30,8280,IN001
"""
        created = self.post_file("/api/transactions/import", statement)
        self.assertEqual(created.status_code, 201, created.get_json())
        batch_id = created.get_json()["data"]["id"]
        rows = self.client.get(f"/api/transactions/imports/{batch_id}/transactions").get_json()["data"]
        transfer = next(row for row in rows if row["description"] == "Own Account Transfer")
        unknown = next(row for row in rows if row["description"] == "CREDIT INTEREST")
        self.assertEqual(transfer["transaction_type"], "Transfer")
        self.assertEqual(unknown["transaction_type"], "Unknown")

        corrected = self.client.patch(
            f"/api/transactions/imported/{unknown['id']}",
            json={"transaction_type": "Income"},
            headers=self.headers,
        )
        self.assertEqual(corrected.status_code, 200, corrected.get_json())
        self.assertEqual(corrected.get_json()["data"]["review_status"], "corrected")
        self.assertEqual(corrected.get_json()["data"]["transaction_type"], "Income")
        dashboard = self.client.get("/api/dashboard?month=11&year=2026").get_json()["data"]
        self.assertEqual(dashboard["total_income"], 30)

    def test_import_batches_and_rows_are_isolated_by_authenticated_user(self):
        created = self.post_file("/api/transactions/import")
        batch_id = created.get_json()["data"]["id"]
        other_client = self.app.test_client()
        other_headers = self.login(other_client, "import-b@example.test", "Import-B-password-123!")
        self.assertEqual(other_client.get(f"/api/transactions/imports/{batch_id}").status_code, 404)
        rows = self.client.get(f"/api/transactions/imports/{batch_id}/transactions").get_json()["data"]
        other_patch = other_client.patch(
            f"/api/transactions/imported/{rows[0]['id']}",
            json={"category": "Food"},
            headers=other_headers,
        )
        self.assertEqual(other_patch.status_code, 404)

    def test_file_validation_requires_csv_and_authentication(self):
        wrong_extension = self.post_file("/api/transactions/preview", filename="statement.txt")
        self.assertEqual(wrong_extension.status_code, 400)
        anonymous = self.app.test_client().post(
            "/api/transactions/preview",
            data={"file": (BytesIO(STANDARD_CSV), "statement.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(anonymous.status_code, 401)


if __name__ == "__main__":
    unittest.main()

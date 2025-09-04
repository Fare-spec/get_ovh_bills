import os
import dotenv
import ovh
import fetcher as ft
import datetime
from urllib.request import urlretrieve

dotenv.load_dotenv()
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
CONSUMER_KEY = os.getenv("CONSUMER_KEY")


def get_ids() -> list[str]:
    try:
        ids = ft.fetch_api(
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            consumer_key=CONSUMER_KEY,
        )
        return ids
    except ovh.exceptions.APIError as e:
        raise RuntimeError(f"Échec récupération IDs factures: {e}") from e


def get_bill(bill_id: str) -> dict:
    try:
        return ft.fetch_invoice_content(
            bill_id,
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            consumer_key=CONSUMER_KEY,
        )
    except ovh.exceptions.APIError as e:
        raise RuntimeError(f"Échec récupération facture {bill_id}: {e}") from e


def get_pdf(bill: dict):
    url = bill["pdfUrl"]
    date = f"{datetime.datetime.fromisoformat(bill['date']).date()}.pdf"
    urlretrieve(url, date)


if __name__ == "__main__":
    ids = get_ids()
    print(ids)
    if ids:
        bill = get_bill(ids[0])
        get_pdf(bill)

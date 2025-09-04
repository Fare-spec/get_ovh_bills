import os
from datetime import datetime
import dotenv
import ovh
import fetcher as ft
from urllib.request import urlretrieve

dotenv.load_dotenv()
APP_KEY = os.environ["APP_KEY"]
APP_SECRET = os.environ["APP_SECRET"]
CONSUMER_KEY = os.environ["CONSUMER_KEY"]
PATH_OVH = os.environ["OVH_PATH"]
YEAR = datetime.now().year


def indexer(ids: list[str]) -> list[str]:
    ids_already_in = os.listdir(f"{PATH_OVH}/{YEAR}")
    missing = [x for x in ids if f"{x}.pdf" not in ids_already_in]
    result = []
    for x in missing:
        date_str = ft.fetch_invoice_content(
            x,
            app_secret=APP_SECRET,
            app_key=APP_KEY,
            consumer_key=CONSUMER_KEY,
        )["date"]
        if datetime.fromisoformat(date_str).year >= int(YEAR):
            result.append(x)
    return result


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


def save_pdf(bill: dict):
    date = datetime.fromisoformat(bill["date"]).date()
    path = f"{PATH_OVH}/{date.year}"

    if not os.path.isdir(path):
        os.mkdir(path)
    url = bill["pdfUrl"]
    urlretrieve(url, f"{PATH_OVH}{bill['billId']}.pdf")


if __name__ == "__main__":
    if not os.path.isdir(PATH_OVH):
        os.mkdir(PATH_OVH)
    ids = indexer(get_ids())
    if ids:
        for id in ids:
            save_pdf(get_bill(id))

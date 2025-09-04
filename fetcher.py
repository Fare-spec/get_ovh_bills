import json
from re import error
import ovh


def fetch_api(app_key: str, app_secret: str, consumer_key: str) -> list[str]:
    client = ovh.Client(
        endpoint="ovh-eu",
        application_key=app_key,
        application_secret=app_secret,
        consumer_key=consumer_key,
    )
    bills = client.get("/me/bill/")
    return bills


def fetch_invoice_content(
    id: str, app_key: str, app_secret: str, consumer_key: str
) -> dict:
    client = ovh.Client(
        endpoint="ovh-eu",
        application_key=app_key,
        application_secret=app_secret,
        consumer_key=consumer_key,
    )
    bill = client.get(f"/me/bill/{id}")
    return bill

from typing import Any, cast
import ovh


def fetch_api(app_key: str, app_secret: str, consumer_key: str) -> list[str]:
    client = ovh.Client(
        endpoint="ovh-eu",
        application_key=app_key,
        application_secret=app_secret,
        consumer_key=consumer_key,
    )
    data: Any = client.get("/me/bill/")

    if data is None:
        return []

    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise TypeError("Réponse OVH inattendue pour /me/bill/: liste de str requise")

    bills: list[str] = cast(list[str], data)
    return bills


def fetch_invoice_content(
    id: str, app_key: str, app_secret: str, consumer_key: str
) -> dict[str, Any]:
    client = ovh.Client(
        endpoint="ovh-eu",
        application_key=app_key,
        application_secret=app_secret,
        consumer_key=consumer_key,
    )
    bill = client.get(f"/me/bill/{id}")
    if bill is None:
        raise RuntimeError(f"Facture {id} introuvable")
    return bill

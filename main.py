import os
from datetime import datetime
import dotenv
import ovh
import fetcher as ft
from urllib.request import urlretrieve
import logging
from logging.handlers import RotatingFileHandler

# --- Configuration du logging ---
logging.addLevelName(logging.DEBUG, "DÉBOGAGE")
logging.addLevelName(logging.INFO, "INFO")
logging.addLevelName(logging.WARNING, "AVERTISSEMENT")
logging.addLevelName(logging.ERROR, "ERREUR")
logging.addLevelName(logging.CRITICAL, "CRITIQUE")

logger = logging.getLogger("ovh_factures")
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Console
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)
# Fichier
fh = RotatingFileHandler(
    "ovh_factures.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
)
fh.setFormatter(formatter)
logger.addHandler(fh)

# Chargement des variables d'environnement (.env)
dotenv.load_dotenv()
APP_KEY = os.environ["APP_KEY"]
APP_SECRET = os.environ["APP_SECRET"]
CONSUMER_KEY = os.environ["CONSUMER_KEY"]
PATH_OVH = os.environ["OVH_PATH"]
YEAR = datetime.now().year  # Année courante (int)


def indexer(ids: list[str]) -> list[str]:
    """
    Parcourt le répertoire de l'année courante et compare les factures déjà présentes
    avec la liste d'IDs renvoyée par OVH. Ne conserve que les factures absentes
    ET datées de l'année courante.
    """
    logger.info("Indexation des factures pour l'année %s", YEAR)
    target_dir = f"{PATH_OVH}{YEAR}"
    try:
        ids_already_in = os.listdir(target_dir)
    except FileNotFoundError:
        logger.warning("Dossier %s inexistant, aucune facture locale", target_dir)
        ids_already_in = []

    missing = [x for x in ids if f"{x}.pdf" not in ids_already_in]
    logger.info("%d factures absentes détectées", len(missing))

    result: list[str] = []
    for bill_id in missing:
        try:
            meta = ft.fetch_invoice_content(
                bill_id,
                app_key=APP_KEY,
                app_secret=APP_SECRET,
                consumer_key=CONSUMER_KEY,
            )
        except Exception as e:
            logger.error("Impossible de récupérer la méta pour %s : %s", bill_id, e)
            continue
        bill_year = datetime.fromisoformat(meta["date"]).year
        if bill_year == YEAR:
            result.append(bill_id)

    logger.info("%d factures retenues pour téléchargement", len(result))
    return result


def get_ids() -> list[str]:
    """
    Interroge l’API OVH et renvoie la liste des IDs de toutes les factures.
    """
    logger.info("Récupération de la liste des factures via API OVH")
    try:
        return ft.fetch_api(
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            consumer_key=CONSUMER_KEY,
        )
    except ovh.exceptions.APIError as e:
        logger.error("Échec récupération des IDs de factures : %s", e)
        raise RuntimeError(f"Échec de la récupération des IDs de factures : {e}") from e


def get_bill(bill_id: str) -> dict:
    """
    Récupère, via l’API OVH, les informations détaillées d’une facture (JSON).
    """
    logger.debug("Récupération de la facture %s", bill_id)
    try:
        return ft.fetch_invoice_content(
            bill_id,
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            consumer_key=CONSUMER_KEY,
        )
    except ovh.exceptions.APIError as e:
        logger.error("Échec récupération de la facture %s : %s", bill_id, e)
        raise RuntimeError(
            f"Échec de la récupération de la facture {bill_id} : {e}"
        ) from e


def save_pdf(bill: dict) -> None:
    """
    Télécharge le PDF d’une facture dans un sous-dossier par année.
    Noms de fichiers : <billId>.pdf
    """
    date = datetime.fromisoformat(bill["date"]).date()
    path = f"{PATH_OVH}{date.year}/"

    os.makedirs(path, exist_ok=True)

    url = bill["pdfUrl"]
    dest = f"{path}{bill['billId']}.pdf"
    try:
        urlretrieve(url, dest)
        logger.info("Facture %s sauvegardée dans %s", bill["billId"], dest)
    except Exception as e:
        logger.error("Impossible de télécharger la facture %s : %s", bill["billId"], e)
        raise


if __name__ == "__main__":
    logger.info("Démarrage du traitement des factures OVH pour %s", YEAR)
    os.makedirs(f"{PATH_OVH}{YEAR}", exist_ok=True)

    ids_candidats = indexer(get_ids())

    for bill_id in ids_candidats:
        save_pdf(get_bill(bill_id))

    logger.info("Traitement terminé : %d factures téléchargées", len(ids_candidats))

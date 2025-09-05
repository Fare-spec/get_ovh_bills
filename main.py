import os
from datetime import datetime
import dotenv
import ovh
import fetcher as ft
from urllib.request import urlretrieve
import logging
from logging.handlers import RotatingFileHandler
import sqlite3

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
DB_PATH = os.environ["DB_PATH"]
YEAR = datetime.now().year  # Année courante (int)


def get_conn():
    """
    Ouvre une connexion SQLite vers DB_PATH, crée la table 'bills' si nécessaire, puis retourne la connexion.
    """
    try:
        logger.debug("Ouverture de la connexion SQLite vers %s", DB_PATH)
        conn = sqlite3.connect(DB_PATH)
        logger.debug("Connexion établie, vérification/creation de la table 'bills'")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            bill_id TEXT PRIMARY KEY,
            bill_year INT
        )""")
        conn.commit()
        logger.info("Base SQLite initialisée et table 'bills' disponible")
        return conn
    except Exception as e:
        logger.exception("Erreur lors de l'initialisation de la base SQLite: %s", e)
        raise


def add_entries_to_db(entries: list[tuple[str, int]], conn):
    """
    Insère en lot des paires (bill_id, bill_year) dans la table 'bills' avec gestion de conflit sur bill_id.
    """
    try:
        logger.debug("Insertion batch dans 'bills': %d entrées", len(entries))
        conn.executemany(
            """
            INSERT INTO bills (bill_id, bill_year)
            VALUES (?, ?)
            ON CONFLICT(bill_id) DO NOTHING
            """,
            entries,
        )
        conn.commit()
        logger.info("Insertion batch dans 'bills' validée")
    except Exception as e:
        logger.exception("Échec d'insertion batch dans 'bills': %s", e)
        raise


def get_entries_from_db(conn) -> set[str]:
    """
    Récupère l'ensemble des bill_id présents dans la table 'bills' et les retourne sous forme de set[str].
    """
    try:
        logger.debug("Sélection des bill_id depuis 'bills'")
        cursor = conn.execute("SELECT bill_id FROM bills")
        rows = cursor.fetchall()
        logger.info("Sélection terminée: %d bill_id récupérés", len(rows))
        return {row[0] for row in rows}
    except Exception as e:
        logger.exception("Échec de lecture des bill_id depuis 'bills': %s", e)
        raise


def compare_db_to_data(db_data: set[str], data: list[str]) -> list[str]:
    """
    Compare une collection d'identifiants 'data' à l'ensemble 'db_data' et retourne la liste des éléments absents de 'db_data'.
    """
    missings_current_year = list()
    for bill_id in data:
        if bill_id not in db_data:
            missings_current_year.append(bill_id)
    return missings_current_year


def indexer(ids: list[str]) -> list[str]:
    """
    Parcourt le répertoire de l'année courante, filtre les factures déjà présentes localement, conserve les factures absentes datées de l'année courante, et enregistre en base celles qui appartiennent à une autre année.
    """
    conn = get_conn()
    logger.info("Indexation des factures pour l'année %s", YEAR)
    target_dir = f"{PATH_OVH}{YEAR}"
    try:
        ids_already_in = os.listdir(target_dir)
    except FileNotFoundError:
        logger.warning("Dossier %s inexistant, aucune facture locale", target_dir)
        ids_already_in = []

    missing = compare_db_to_data(
        get_entries_from_db(conn), [x for x in ids if f"{x}.pdf" not in ids_already_in]
    )
    logger.info("%d factures absentes détectées", len(missing))

    result: list[str] = []
    not_valid_year: list[tuple[str, int]] = list()
    for bill_id in missing:
        try:
            meta = ft.fetch_invoice_content(
                bill_id,
                app_key=APP_KEY,
                app_secret=APP_SECRET,
                consumer_key=CONSUMER_KEY,
            )
        except Exception as e:
            logger.error("Impossible de récupérer le json pour %s : %s", bill_id, e)
            continue
        bill_year = datetime.fromisoformat(meta["date"]).year
        if bill_year == YEAR:
            result.append(bill_id)
        else:
            not_valid_year.append((bill_id, bill_year))

    add_entries_to_db(not_valid_year, conn)
    logger.info(f"Ajouter {len(not_valid_year)} entrées a la base de donnée")
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

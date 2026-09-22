"""
Vinted ETB Bot — Surveillance d'annonces Pokémon
Tourne en local sur macOS, envoie des alertes Discord via webhook.
"""

import time
import json
import sqlite3
import logging
import random
import requests
from vinted_scraper import VintedWrapper
from datetime import datetime, timezone
from pathlib import Path

# ─── Configuration du logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),   # sauvegarde dans un fichier
        logging.StreamHandler()            # affiche aussi dans le terminal
    ]
)
log = logging.getLogger(__name__)

# ─── Constantes ─────────────────────────────────────────────────────────────
CONFIG_FILE  = Path("config.json")
DB_FILE      = Path("seen.db")
SCAN_INTERVAL = 67  # secondes entre chaque scan

# Mots à exclure dans le titre (langue / type de produit)
EXCLUDED_WORDS = [
    # Langues étrangères
    "jap", "japonais", "japonaise", "japanese",
    "english", "anglais", "eng",
    "ingles", "lote", "promocional", "espanol", "italiano",
    "thai", "korean",
    # Mauvais produits
    "figurine", "peluche", "poster", "manga", "funko", "diorama",
    "sleeve", "classeur", "binder", "display", "bulk",
]

# Pays autorisés (codes Vinted)
ALLOWED_COUNTRIES = ["FR", "BE"]

# Vinted a migré son site vers une nouvelle architecture (Next.js) en 09/2026 :
# l'ancien endpoint "www.vinted.fr/api/v2/catalog/items" a été supprimé et
# remplacé par "api.vinted.fr/svc-catalogue/items" (nouveaux headers/cookies
# requis). On délègue tout ça à la lib vinted_scraper, maintenue à jour.
VINTED_BASE_URL = "https://www.vinted.fr"

# ─── Base de données SQLite ─────────────────────────────────────────────────
def init_db():
    """Crée la table des annonces déjà vues si elle n'existe pas."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_items (
            item_id   TEXT PRIMARY KEY,
            seen_at   TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def is_already_seen(item_id: str) -> bool:
    """Retourne True si l'annonce a déjà été envoyée."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute("SELECT 1 FROM seen_items WHERE item_id = ?", (str(item_id),))
    result = cur.fetchone() is not None
    conn.close()
    return result

def mark_as_seen(item_id: str):
    """Enregistre l'annonce pour ne plus la renvoyer."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT OR IGNORE INTO seen_items (item_id, seen_at) VALUES (?, ?)",
        (str(item_id), datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()

# ─── Chargement de la config ────────────────────────────────────────────────
def load_config() -> dict:
    """Charge et valide config.json."""
    if not CONFIG_FILE.exists():
        log.error("config.json introuvable ! Crée-le d'abord.")
        raise SystemExit(1)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)

# ─── Récupération des cookies Vinted ────────────────────────────────────────
def debug_item_structure(item: dict):
    """Affiche la structure pays d'une annonce pour débugger (désactiver après)."""
    user = item.get("user", {})
    log.info(f"      [DEBUG pays] user.country_iso_code={user.get('country_iso_code')} | user.country={user.get('country')} | item.country_iso_code={item.get('country_iso_code')}")

def get_vinted_wrapper() -> VintedWrapper:
    """
    Crée un wrapper vinted_scraper : gère cookies, CSRF token, anon_id et
    renouvellement de session automatiquement (voir VINTED_BASE_URL).
    """
    wrapper = VintedWrapper(VINTED_BASE_URL)
    log.info("   ✅ Session Vinted créée (vinted_scraper)")
    return wrapper

# ─── Appel à l'API Vinted ───────────────────────────────────────────────────
def fetch_items(wrapper: VintedWrapper, keyword: str, min_price: float, max_price: float) -> list:
    """Interroge l'API Vinted et retourne la liste brute des annonces."""
    params = {
        "search_text": keyword,
        "price_from":  min_price,
        "price_to":    max_price,
        "order":       "newest_first",
        "per_page":    "50",
    }
    try:
        data = wrapper.search(params)
        return data.get("items", [])
    except Exception as e:
        log.warning(f"Erreur réseau Vinted ({keyword}) : {e}")
        return []

# ─── Extraction du prix ─────────────────────────────────────────────────────
def extract_price(item: dict) -> float:
    """
    Vinted retourne le prix sous forme de dict : {"amount": "65.00", "currency_code": "EUR"}
    Cette fonction extrait toujours un float, quelle que soit la structure.
    """
    raw = item.get("price", 0)
    if isinstance(raw, dict):
        return float(raw.get("amount", 0))
    return float(raw)

# ─── Filtres ────────────────────────────────────────────────────────────────
def passes_filters(item: dict, min_price: float, max_price: float, required_keywords: list = None) -> bool:
    """
    Applique tous les filtres sur une annonce.
    Retourne True uniquement si l'annonce passe TOUS les filtres.
    """
    title   = item.get("title", "").lower()
    price   = extract_price(item)
    log.info(f"   🔎 {price:.2f}€ — {title}")

    # 1. "ETB" doit être dans le titre
    if "etb" not in title:
        log.info(f"      ❌ Rejeté : ETB absent du titre")
        return False

    # 2. Fourchette de prix
    if not (min_price <= price <= max_price):
        log.info(f"      ❌ Rejeté : prix {price:.2f}€ hors fourchette [{min_price}€-{max_price}€]")
        return False

    # 3. Au moins un mot-clé obligatoire doit être dans le titre
    if required_keywords:
        if not any(kw.lower() in title for kw in required_keywords):
            log.info(f"      ❌ Rejeté : aucun mot-clé obligatoire trouvé {required_keywords}")
            return False

    # 4. Aucun mot exclu dans le titre (langue étrangère / mauvais produit)
    for word in EXCLUDED_WORDS:
        if word in title:
            log.info(f"      ❌ Rejeté : mot exclu '{word}'")
            return False

    log.info(f"      ✅ Passe tous les filtres !")
    return True

# ─── Envoi Discord ──────────────────────────────────────────────────────────
def send_discord_alert(item: dict, webhook_url: str):
    """Envoie un embed Discord pour l'annonce."""
    title    = item.get("title", "Sans titre")
    price    = extract_price(item)
    url      = item.get("url", "")
    photo    = (item.get("photos") or [{}])[0].get("url", "")
    user     = item.get("user", {})
    username = user.get("login", "Inconnu")
    user_url = f"https://www.vinted.fr/member/{user.get('id', '')}"
    city     = item.get("city") or "Localisation inconnue"

    # Couleur de l'embed selon le prix
    color = 0x2ECC71 if price <= 55 else 0xE67E22  # vert ou orange

    embed = {
        "title":       f"🎴 {title}",
        "url":         url,
        "color":       color,
        "fields": [
            {"name": "💰 Prix",       "value": f"**{price:.2f} €**",          "inline": True},
            {"name": "📍 Ville",      "value": city,                           "inline": True},
            {"name": "👤 Vendeur",    "value": f"[{username}]({user_url})",   "inline": True},
        ],
        "footer":      {"text": "Vinted ETB Bot"},
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }

    # Ajout de l'image si disponible
    if photo:
        embed["image"] = {"url": photo}

    payload = {"embeds": [embed]}

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        log.info(f"✅ Alerte envoyée : {title} — {price:.2f} €")
    except Exception as e:
        log.error(f"Erreur webhook Discord : {e}")

# ─── Boucle principale --------------------------------------------
def main():
    log.info("=== Vinted ETB Bot démarré ===")
    init_db()
    config  = load_config()
    wrapper = get_vinted_wrapper()
    searches = config.get("searches", [])

    if not searches:
        log.error("Aucune recherche définie dans config.json !")
        return

    session_counter = 0

    while True:
        # Renouvelle la session toutes les 5 minutes (5 cycles) pour éviter les 401/403
        if session_counter % 5 == 0 and session_counter > 0:
            wrapper.refresh_session()
            log.info("🔄 Session Vinted renouvelée")
        session_counter += 1

        for search in searches:
            keyword     = search.get("keyword", "")
            min_price   = float(search.get("min_price", 30))
            max_price   = float(search.get("max_price", 85))
            webhook_url       = search.get("webhook_url", "")
            required_keywords = search.get("required_keywords", [])

            if not webhook_url or "..." in webhook_url:
                log.warning(f"Webhook manquant ou non configuré pour : {keyword}")
                continue

            log.info(f"🔍 Scan : {keyword} ({min_price}€ – {max_price}€)")
            items = fetch_items(wrapper, keyword, min_price, max_price)

            new_count = 0
            for item in items:
                item_id = str(item.get("id", ""))
                if not item_id or is_already_seen(item_id):
                    continue

                mark_as_seen(item_id)  # on marque avant d'envoyer pour éviter les doublons

                if passes_filters(item, min_price, max_price, required_keywords):
                    send_discord_alert(item, webhook_url)
                    new_count += 1
                    time.sleep(1)  # petit délai entre les envois

            log.info(f"   → {len(items)} annonces récupérées, {new_count} alertes envoyées")
            time.sleep(random.uniform(3, 8))  # délai aléatoire entre chaque recherche

        jitter = random.uniform(-15, 15)
        pause = max(30, SCAN_INTERVAL + jitter)
        log.info(f"⏳ Pause de {pause:.0f}s...\n")
        time.sleep(pause)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Bot arrêté manuellement.")

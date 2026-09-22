"""
Script de diagnostic — affiche la structure complète d'une annonce Vinted.
Lance avec : python3 debug_vinted.py
"""
import requests
import json

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://www.vinted.fr/",
}

session = requests.Session()
session.headers.update(HEADERS)
session.get("https://www.vinted.fr", timeout=10)

resp = session.get(
    "https://www.vinted.fr/api/v2/catalog/items",
    params={"search_text": "ETB", "price_from": 30, "price_to": 85, "per_page": "3"},
    timeout=15
)

items = resp.json().get("items", [])
for item in items[:2]:
    print("=== ANNONCE ===")
    print(f"Titre : {item.get('title')}")
    print(f"Prix  : {item.get('price')}")
    print(f"\n--- Champs pays dans item ---")
    print(f"item.country_iso_code : {item.get('country_iso_code')}")
    print(f"item.country          : {item.get('country')}")
    print(f"\n--- Champs pays dans user ---")
    user = item.get("user", {})
    print(f"user.country_iso_code : {user.get('country_iso_code')}")
    print(f"user.country          : {user.get('country')}")
    print(f"user.country_title    : {user.get('country_title')}")
    print()

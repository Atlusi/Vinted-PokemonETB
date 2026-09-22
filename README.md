# Vinted ETB Bot

Surveille Vinted pour des annonces de coffrets Pokémon (ETB) selon des mots-clés,
fourchettes de prix et filtres définis dans `config.json`, et envoie une alerte
Discord (webhook) pour chaque nouvelle annonce correspondante.

## Prérequis

- Python 3.11+
- Un webhook Discord par recherche que tu veux suivre

## Installation

```bash
git clone <url-du-repo> vinted-bot
cd vinted-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copie le fichier d'exemple puis édite-le :

```bash
cp config.example.json config.json
```

`config.json` contient une liste `searches`, chaque entrée définit :

| Champ                | Description                                                        |
|-----------------------|---------------------------------------------------------------------|
| `keyword`             | Texte de recherche envoyé à Vinted                                  |
| `required_keywords`   | Liste de mots-clés dont au moins un doit apparaître dans le titre   |
| `min_price` / `max_price` | Fourchette de prix en euros                                     |
| `webhook_url`          | URL du webhook Discord qui recevra les alertes                     |

`config.json` est ignoré par git (`.gitignore`) car il contient des URLs de
webhook réelles — ne le commite jamais.

## Lancer le bot

### Manuellement

```bash
source venv/bin/activate
python3 bot.py
```

Arrêt : `Ctrl+C`.

### En arrière-plan (macOS, launchd)

1. Ouvre `com.vintedbot.app.plist` et remplace toutes les occurrences de
   `TON_NOM_UTILISATEUR` par ton nom d'utilisateur macOS (`whoami`).
2. Copie le fichier et active le service :

```bash
cp com.vintedbot.app.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.vintedbot.app.plist
```

Le bot redémarre automatiquement s'il plante et au reboot du Mac.

Pour l'arrêter :

```bash
launchctl unload ~/Library/LaunchAgents/com.vintedbot.app.plist
```

Après une modification de `config.json`, redémarre le service (unload puis load).

## Logs

```bash
tail -f bot.log        # logs normaux
tail -f bot_error.log  # erreurs
```

## Personnaliser

| Ce que tu veux changer                  | Où                                      |
|-------------------------------------------|-------------------------------------------|
| Recherches, prix, mots-clés, webhooks     | `config.json`                             |
| Mots exclus des titres (langue, produit)  | `EXCLUDED_WORDS` dans `bot.py`            |
| Intervalle entre deux scans               | `SCAN_INTERVAL` dans `bot.py` (secondes)  |

## Questions fréquentes

**Erreur `ModuleNotFoundError: No module named 'vinted_scraper'`**
Le venv n'est pas activé, ou les dépendances ne sont pas installées :
`source venv/bin/activate && pip install -r requirements.txt`.

**`config.json introuvable ! Crée-le d'abord.`**
Copie `config.example.json` vers `config.json` et remplis tes webhooks
(voir Configuration ci-dessus).

**Toutes les recherches renvoient une erreur HTTP 404**
Vinted a changé son API publique. Le bot passe par la librairie
`vinted_scraper`, qui suit ces changements ; vérifie qu'une nouvelle
version est disponible (`pip install -U vinted-scraper`) avant de rouvrir
un correctif.

**Erreurs HTTP 401 / 403 répétées**
La session Vinted a expiré ou une protection anti-bot bloque temporairement
les requêtes. Le bot renouvelle sa session automatiquement toutes les 5
itérations ; si le blocage persiste, attends quelques minutes avant de relancer.

**Aucune alerte n'arrive sur Discord alors que le bot tourne**
Vérifie dans `config.json` que `webhook_url` est bien rempli (pas de `...`
dedans) et que l'URL est valide. Regarde `bot_error.log` pour un message
`Erreur webhook Discord`.

**Le bot tourne mais aucune annonce ne passe les filtres**
Regarde `bot.log` : chaque annonce scannée est loguée avec la raison de son
rejet (`ETB absent du titre`, `prix hors fourchette`, `mot exclu`, `aucun
mot-clé obligatoire trouvé`). Ajuste `config.json` en conséquence.

**Le bot s'arrête quand je ferme le Terminal**
Utilise la version en arrière-plan (launchd), voir plus haut — sinon le
processus se termine avec la session du Terminal.

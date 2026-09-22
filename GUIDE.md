# 📦 Guide d'installation — Vinted ETB Bot (macOS)

## Ce dont tu as besoin
- Ton Mac Mini M4
- Une connexion internet
- 15 minutes

---

## Étape 1 — Ouvrir le Terminal

1. Appuie sur **Cmd + Espace**
2. Tape **Terminal**
3. Appuie sur **Entrée**

> Le Terminal est l'outil qui permet de taper des commandes sur ton Mac.
> Tu n'as pas besoin de comprendre ce que tu tapes — copie-colle exactement.

---

## Étape 2 — Installer Python (si pas déjà fait)

Tape dans le Terminal :
```bash
python3 --version
```

Si tu vois quelque chose comme `Python 3.11.x` → passe à l'étape 3.
Si tu vois une erreur → va sur https://www.python.org/downloads/ et télécharge Python.

---

## Étape 3 — Créer le dossier du bot

Copie-colle ces commandes une par une dans le Terminal :

```bash
cd ~
mkdir vinted-bot
cd vinted-bot
```

> `cd ~` → va dans ton dossier personnel
> `mkdir vinted-bot` → crée un dossier nommé vinted-bot
> `cd vinted-bot` → entre dans ce dossier

---

## Étape 4 — Copier les fichiers

Place ces 4 fichiers dans le dossier `vinted-bot` :
- `bot.py`
- `requirements.txt`
- `config.json`
- `com.vintedbot.app.plist`

Tu peux ouvrir le dossier avec Finder :
```bash
open .
```

---

## Étape 5 — Créer un environnement virtuel Python

```bash
python3 -m venv venv
source venv/bin/activate
```

> Un "environnement virtuel" c'est un espace isolé pour installer les dépendances
> du bot sans mélanger avec le reste de ton Mac.
> Tu verras `(venv)` apparaître au début de ta ligne de commande.

---

## Étape 6 — Installer les dépendances

```bash
pip install -r requirements.txt
```

> Ça installe la librairie `requests` qui permet au bot de faire des appels internet.

---

## Étape 7 — Configurer config.json

Ouvre `config.json` avec TextEdit ou VS Code et remplace :
- `TON_WEBHOOK_ICI` par l'URL de ton webhook Discord

### Comment créer un webhook Discord ?
1. Ouvre ton serveur Discord
2. Clique droit sur le channel qui recevra les alertes
3. Paramètres du salon → Intégrations → Webhooks
4. Crée un webhook → copie l'URL
5. Colle-la dans `config.json`

---

## Étape 8 — Tester le bot manuellement

```bash
source venv/bin/activate
python3 bot.py
```

Tu devrais voir dans le Terminal :
```
=== Vinted ETB Bot démarré ===
🔍 Scan : ETB Évolutions Prismatiques (30€ – 85€)
   → 50 annonces récupérées, X alertes envoyées
⏳ Pause de 30s...
```

Pour arrêter le test : **Ctrl + C**

---

## Étape 9 — Lancer le bot en arrière-plan (overnight)

### 9a — Modifier le fichier .plist

Ouvre `com.vintedbot.app.plist` et remplace toutes les occurrences de
`TON_NOM_UTILISATEUR` par ton vrai nom d'utilisateur macOS.

Pour connaître ton nom d'utilisateur :
```bash
whoami
```

### 9b — Copier le fichier dans le bon dossier

```bash
cp ~/vinted-bot/com.vintedbot.app.plist ~/Library/LaunchAgents/
```

### 9c — Activer le service

```bash
launchctl load ~/Library/LaunchAgents/com.vintedbot.app.plist
```

Le bot tourne maintenant en arrière-plan.
Il redémarre automatiquement s'il plante.
Il redémarre au reboot du Mac.

---

## Commandes utiles

### Voir les logs en direct
```bash
tail -f ~/vinted-bot/bot.log
```
> Ctrl+C pour arrêter l'affichage

### Arrêter le bot
```bash
launchctl unload ~/Library/LaunchAgents/com.vintedbot.app.plist
```

### Redémarrer le bot (après une modif de config.json)
```bash
launchctl unload ~/Library/LaunchAgents/com.vintedbot.app.plist
launchctl load ~/Library/LaunchAgents/com.vintedbot.app.plist
```

### Ajouter une nouvelle extension à surveiller
1. Ouvre `config.json`
2. Ajoute un bloc dans `"searches"` avec le nouveau mot-clé et webhook
3. Redémarre le bot avec les commandes ci-dessus

---

## Structure des fichiers

```
vinted-bot/
├── bot.py                    # Le code principal du bot
├── config.json               # Tes recherches et webhooks
├── requirements.txt          # Les librairies Python nécessaires
├── com.vintedbot.app.plist  # Service macOS (lancement automatique)
├── seen.db                   # Base de données des annonces déjà vues (auto-créé)
├── bot.log                   # Logs normaux (auto-créé)
└── bot_error.log             # Logs d'erreurs (auto-créé)
```

---

## Problèmes fréquents

**Le bot ne reçoit rien sur Discord**
→ Vérifie que l'URL du webhook est correcte dans config.json
→ Vérifie que des annonces correspondant à tes critères existent sur Vinted

**Erreur "Module not found"**
→ Tu as oublié d'activer le venv : `source venv/bin/activate`

**Les alertes s'arrêtent**
→ Vérifie les logs : `tail -f ~/vinted-bot/bot.log`
→ Vinted a peut-être temporairement bloqué les requêtes (rare)

---

## Pour modifier les filtres

Tout est dans `bot.py`, lignes 30–40 :
- `EXCLUDED_WORDS` → mots à bannir dans les titres
- `ALLOWED_COUNTRIES` → pays autorisés (`"FR"`, `"BE"`, `"LU"`...)
- `SCAN_INTERVAL` → délai entre les scans (en secondes)

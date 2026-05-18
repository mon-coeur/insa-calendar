# Setup INSA calendar proxy (sans terminal)

Tout se fait sur github.com via le navigateur.

## 1. Compte GitHub
Va sur github.com → Sign up si pas de compte.

## 2. Créer le repo
- Bouton **+** en haut à droite → **New repository**
- Name : `insa-cal`
- **Public** (obligatoire pour raw.githubusercontent.com sans auth)
- Coche **Add a README**
- **Create repository**

## 3. Uploader les fichiers
Dans le repo créé :
- **Add file → Upload files**
- Glisse-dépose : `transform.py`, `mappings.json`
- En bas : **Commit changes**

Pour le workflow GitHub Actions :
- **Add file → Create new file**
- Nom : `.github/workflows/refresh.yml` (tape exactement ce chemin, les `/` créent les dossiers)
- Colle le contenu de `refresh.yml`
- **Commit changes**

## 4. Lancer une première fois
- Onglet **Actions** du repo
- Clique sur **Refresh INSA calendar** dans la liste
- Bouton **Run workflow** → **Run workflow**
- Attends ~30 sec, refresh la page : tu dois voir un run vert

Si le run a réussi, retourne à la racine du repo : tu dois voir `calendar.ics`.

## 5. URL à utiliser dans ICSx5
```
https://raw.githubusercontent.com/<TON_USER_GITHUB>/insa-cal/main/calendar.ics
```
Remplace `<TON_USER_GITHUB>` par ton pseudo GitHub.

Dans ICSx5 sur ton tel :
- Supprime l'ancien abonnement INSA
- Ajoute un nouvel abonnement avec l'URL ci-dessus
- Sync

## 6. Ajuster les mappings
Quand tu vois un code inconnu (genre `? - Sport - ?`) :
- Ouvre `mappings.json` sur GitHub
- Clique l'icône crayon (Edit)
- Ajoute le mapping (ex: `"EPS": "Sport"`)
- **Commit changes**
- Onglet Actions → Run workflow pour rafraichir tout de suite

## Refresh auto
Le workflow tourne toutes les 30 min via cron GitHub. Note : GitHub peut retarder les crons sur les comptes free (jusqu'à 15-30 min d'écart). Si tu veux du temps réel, lance manuellement via Actions.

## Format actuel
`TYPE - Matière - Salle` → ex: `CM - Math - Curie`
- TYPE extrait de la 6e position du SUMMARY (CM/TD/TP/EV/DS/CC)
- Matière extraite de la 5e position (code 2-4 lettres) puis traduite via `mappings.json`
- Salle extraite du LOCATION en retirant `(1070101)` et le préfixe `Amphi`/`Salle`

Si un code n'est pas mappé il sortira tel quel (ex: `CM - MA - Curie`). Pas grave, ajoute-le au JSON.

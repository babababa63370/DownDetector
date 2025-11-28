# Comment compiler votre app en APK

## Option 1: Localement sur votre ordinateur (le plus simple)

### Sur Windows/Mac/Linux :

1. **Installez les dépendances :**
```bash
pip install buildozer cython
```

2. **Sur Linux (Ubuntu/Debian) :**
```bash
sudo apt-get install -y python3-dev python3-pip openjdk-17-jdk zlib1g-dev libssl-dev
```

3. **Compilez l'APK :**
```bash
buildozer android debug
```

4. **L'APK sera créé dans :** `bin/mapp-0.1-debug.apk`

5. **Installez sur votre téléphone :**
- Transférez le fichier APK sur votre téléphone Android
- Ouvrez le fichier APK depuis votre gestionnaire de fichiers
- Appuyez sur "Installer"

---

## Option 2: GitHub Actions (automatisé)

1. **Créez un repo GitHub** avec votre code
2. **Créez le fichier:** `.github/workflows/build.yml` avec ce contenu:

```yaml
name: Build APK

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - run: |
          pip install buildozer cython
          sudo apt-get install -y python3-dev openjdk-17-jdk zlib1g-dev libssl-dev
          buildozer android debug
      - uses: actions/upload-artifact@v2
        with:
          name: apk
          path: bin/*.apk
```

3. **Poussez le code :** `git push`
4. **Récupérez l'APK:** Dans GitHub Actions → téléchargez l'artefact

---

## Notre recommandation
**Option 1 (localement)** - Plus rapide et contrôlé

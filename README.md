# rtperfui

Application web en Python (FastAPI) servant de frontend pour lancer des tests de performances temps réel sur la machine hôte.

## Fonctionnalités actuelles

- Interface web moderne (Tailwind, Chart.js).
- Onglet **cyclictest** :
  - Formulaire pour lancer un `cyclictest` avec paramètres :
    - **Durée** (secondes, défaut : 60 s).
    - **Intervalle** (µs, défaut : 200 µs).
    - **Priorité temps réel** (SCHED_FIFO, défaut : 90).
    - **Politique** temps réel (FIFO ou RR).
    - **Affinité CPU** (liste de CPUs, défaut : CPUs isolés détectés).
  - Détection automatique des CPUs isolés via `/sys/devices/system/cpu/isolated` (fallback sur les CPUs en ligne hors CPU0).
  - Lancement de `cyclictest` sur l'hôte et parsing de la sortie.
  - Affichage d'un graphe des latences (valeurs Max successives) + résumé min/avg/max.

> Remarque : cette première version lance `cyclictest` de manière synchrone (la page attend la fin du test). On pourra ensuite faire évoluer vers du streaming temps réel.

## Prérequis

- Python 3.10+ recommandé.
- `cyclictest` installé sur la machine (paquet `rt-tests` sur la plupart des distributions Linux).
- Accès suffisant pour lancer des tâches temps réel (souvent via `root` ou capacités RT).

## Installation

```bash
cd rtperfui
python -m venv .venv
source .venv/bin/activate  # sous Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement de l'application

Depuis la racine du projet :

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Puis ouvrir le navigateur sur `http://localhost:8000`.

## Utilisation de l'onglet cyclictest

1. Ouvrir la page principale.
2. Vérifier les paramètres proposés par défaut :
   - Durée : 60 s
   - Intervalle : 200 µs
   - Priorité : 90 (SCHED_FIFO)
   - Affinité CPU : laissée vide → les CPUs isolés détectés sont utilisés (ou fallback).
3. Cliquer sur **Lancer le test**.
4. À la fin du test :
   - Un graphe des latences max par échantillon est affiché.
   - Un résumé min / avg / max est affiché au-dessus du graphe.

Si `cyclictest` n'est pas trouvé ou retourne une erreur, un message explicite s'affiche en bas du formulaire.

## Roadmap possible

- Support de plusieurs onglets (autres tests RT).
- Exécution et streaming temps réel des mesures (WebSocket ou SSE).
- Export des résultats (JSON/CSV).
- Gestion plus fine des options `cyclictest` (multi-threads, histogrammes détaillés, etc.).


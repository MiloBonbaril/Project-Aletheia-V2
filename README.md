# Project Aletheia V2

English (EN)
-----------------

## Overview
Project Aletheia V2 is a unified Python project with separate optional dependencies for front (a Discord bot with voice) and back (a FastAPI-based API and local model client). It targets Python 3.12 and uses `setuptools` with a `src/` layout.

## Features
- FastAPI backend with optional local model client (Ollama)
- Discord bot using Pycord with voice support
- Simple, optional extras to install only what you need
- Pytest-based testing setup

## Requirements
- Python >= 3.12
- Optional: `uvicorn`, `fastapi`, `ollama` for backend; `py-cord[voice]`, `PyNaCl` for front

## Quickstart
```bash
# Create and activate a virtual environment
scripts/setup_venv.sh      # on macOS/Linux
scripts\setup_venv.bat    # on Windows

# Install base dependencies
pip install .

# Or install with extras
pip install .[back]
pip install .[front]
pip install .[dev]
```

## Project Structure
```
src/                # Project source (packages discovered by setuptools)
tests/              # Tests (pytest)
scripts/            # Dev helpers (venv setup)
config.py           # Project configuration helper
pyproject.toml      # Build and project metadata
```

## Development
- Use the provided scripts in `scripts/` to set up a venv.
- Run tests with `pytest`.
- Keep code and docs bilingual (EN/FR), with English prioritized.

## Configuration
- Environment variables can be managed via `.env` using `python-dotenv`.
- See `config.py` for simple configuration helpers.

## License
Unless otherwise agreed in writing, this project is licensed under a Proprietary License (see `LICENSE`). All rights reserved.

---

Français (FR)
-----------------

## Vue d’ensemble
Project Aletheia V2 est un projet Python unifié avec des dépendances optionnelles distinctes pour le front (un bot Discord avec voix) et le back (une API basée sur FastAPI et un client de modèle local). Il cible Python 3.12 et utilise `setuptools` avec une structure `src/`.

## Fonctionnalités
- Backend FastAPI avec client de modèle local (Ollama) en option
- Bot Discord utilisant Pycord avec support vocal
- Extras optionnels pour installer uniquement ce dont vous avez besoin
- Configuration de tests basée sur Pytest

## Pré-requis
- Python >= 3.12
- Optionnel : `uvicorn`, `fastapi`, `ollama` pour le backend ; `py-cord[voice]`, `PyNaCl` pour le front

## Démarrage rapide
```bash
# Créer et activer un environnement virtuel
scripts/setup_venv.sh      # macOS/Linux
scripts\setup_venv.bat    # Windows

# Installer les dépendances de base
pip install .

# Ou installer avec des extras
pip install .[back]
pip install .[front]
pip install .[dev]
```

## Structure du projet
```
src/                # Code source du projet (packages détectés par setuptools)
tests/              # Tests (pytest)
scripts/            # Outils de dev (configuration de l’environnement virtuel)
config.py           # Aide à la configuration du projet
pyproject.toml      # Métadonnées du build et du projet
```

## Développement
- Utilisez les scripts dans `scripts/` pour configurer un venv.
- Lancez les tests avec `pytest`.
- Gardez le code et la documentation bilingues (EN/FR), avec l’anglais prioritaire.

## Configuration
- Les variables d’environnement peuvent être gérées via `.env` avec `python-dotenv`.
- Consultez `config.py` pour des aides de configuration simples.

## Licence
Sauf accord écrit contraire, ce projet est sous licence propriétaire (voir `LICENSE`). Tous droits réservés.


# Contributing / Contribuer

English (EN)
-----------------

## Code of Conduct
By participating, you agree to abide by our Code of Conduct (see `CODE_OF_CONDUCT.md`).

## Getting Started
- Use Python 3.12.
- Create a virtual environment using the scripts in `scripts/`.
- Install dependencies: `pip install .[dev]` and the relevant extras `[back]` or `[front]` as needed.

## Development Workflow
- Branch from `main` with a descriptive name (e.g., `feat/x`, `fix/y`).
- Keep changes focused and small.
- Run tests with `pytest` locally before opening a PR.
- Update documentation (README, examples) for user-facing changes.

## Commit Messages
- Use clear, imperative subject lines (e.g., "Add FastAPI health route").
- Reference issues when relevant (e.g., `Fixes #123`).

## Pull Requests
- Describe the problem, the solution, and alternatives considered.
- Include screenshots or logs if they help reviewers.
- Ensure CI (if configured) passes before requesting review.

## Style & Quality
- Follow existing code style and structure; prefer simplicity.
- Add tests when fixing bugs or adding features.

## Security & Secrets
- Never commit secrets (API keys, tokens). Use environment variables and `.env` for local dev.
- Report security concerns privately to the maintainers.

---

Français (FR)
-----------------

## Code de conduite
En participant, vous acceptez de respecter notre Code de Conduite (voir `CODE_OF_CONDUCT.md`).

## Bien démarrer
- Utiliser Python 3.12.
- Créer un environnement virtuel avec les scripts dans `scripts/`.
- Installer les dépendances : `pip install .[dev]` et les extras nécessaires `[back]` ou `[front]`.

## Flux de développement
- Créez une branche depuis `main` avec un nom descriptif (ex. `feat/x`, `fix/y`).
- Gardez des changements ciblés et limités.
- Exécutez les tests localement avec `pytest` avant d’ouvrir une PR.
- Mettez à jour la documentation (README, exemples) pour les changements visibles par l’utilisateur.

## Messages de commit
- Utilisez des sujets clairs et à l’impératif (ex. « Ajouter la route de santé FastAPI »).
- Référencez les issues si pertinent (ex. `Fixes #123`).

## Pull Requests
- Décrivez le problème, la solution et les alternatives considérées.
- Incluez des captures d’écran ou journaux si cela aide la revue.
- Assurez-vous que la CI (si configurée) passe avant de demander une revue.

## Style & Qualité
- Suivez le style et la structure existants ; privilégiez la simplicité.
- Ajoutez des tests lors de corrections de bugs ou d’ajouts de fonctionnalités.

## Sécurité & Secrets
- Ne commettez jamais de secrets (clés API, tokens). Utilisez des variables d’environnement et `.env` en local.
- Signalez les problèmes de sécurité en privé aux mainteneurs.


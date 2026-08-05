# CadrIA — guide des agents

Ce dépôt implémente **CadrIA**, un copilote de brief construit avec Django, Celery, PostgreSQL et Redis.
L'interface et la documentation utilisateur sont en français ; les noms de code restent en anglais.

## Avant de modifier

1. Lire `.claude/skills/projet-django-ia/SKILL.md` pour le cahier des charges et les critères éliminatoires.
2. Lire le code concerné et ses tests avant de proposer une architecture différente.
3. Pour toute interface, lire `design-system/cadria/MASTER.md` puis appliquer le skill
   `.claude/skills/ui-ux-pro-max/`.

## Architecture à préserver

- Les vues Django orchestrent HTTP, formulaires et permissions ; elles n'appellent jamais un fournisseur IA.
- `briefs/services/` contient les fournisseurs et la validation des réponses IA.
- `briefs/tasks.py` porte l'orchestration longue Celery et persiste les transitions d'état.
- PostgreSQL est la source de vérité ; Redis ne contient que le broker/backend Celery.
- Toute lecture d'un brief doit vérifier son propriétaire.
- Les appels distants sont entièrement simulés dans les tests.

## Commandes de référence

```bash
uv sync --locked
uv run python manage.py check
uv run ruff check .
uv run black --check .
uv run coverage run manage.py test
uv run coverage report
docker compose config
docker compose up --build
```

## Sécurité et qualité

- Ne jamais écrire de secret, token, mot de passe réel ou contenu complet d'un prompt dans les logs.
- Toute configuration sensible vient de l'environnement ; `.env` reste ignoré.
- Valider les entrées côté serveur, conserver CSRF et échapper le contenu utilisateur.
- Ajouter une migration pour tout changement de modèle et des tests pour tout comportement modifié.
- Garder les composants accessibles : labels visibles, focus, contraste, cibles de 44 px et mouvement réduit.
- Ne pas modifier les données tierces de `.claude/skills/ui-ux-pro-max/` sauf mise à jour volontaire de cette dépendance.

## Définition de terminé

Le changement est terminé seulement si les checks Django, Ruff, Black et les tests passent, si Compose reste valide,
et si la documentation/configuration d'exemple reflète le nouveau comportement.

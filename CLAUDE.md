# Instructions Claude Code — CadrIA

Travaille en français avec l'équipe. Le produit est CadrIA, un assistant qui transforme une idée de projet brute en
brief structuré. La priorité est un socle explicable par des étudiants, sécurisé et réellement déployable.

## Contexte obligatoire

- Commence par lire `AGENTS.md` et `.claude/skills/projet-django-ia/SKILL.md`.
- Charge uniquement les skills de cours utiles au changement en cours.
- Pour une création ou revue d'interface, utilise `ui-ux-pro-max`, puis `web-design-guidelines` en audit final.
- Le design persistant se trouve dans `design-system/cadria/MASTER.md`.

## Agents spécialisés

Tu peux déléguer des sous-tâches bornées aux agents de `.claude/agents/` :

- `django-architect` pour modèles, formulaires, vues, permissions et migrations ;
- `ai-pipeline-engineer` pour fournisseurs, prompts, validation, Celery et gestion d'erreurs ;
- `ui-ux-reviewer` pour templates, tokens, responsive et accessibilité ;
- `devops-qa` pour Docker, CI, tests et observabilité.

Ne fais pas travailler deux agents sur le même fichier. Chaque agent doit rapporter ses hypothèses et les commandes
de validation exécutées.

## Garde-fous

- Aucun appel IA dans une vue Django.
- Aucun appel réseau réel dans la suite de tests.
- Aucun secret dans Git ni dans les logs.
- Le mode `demo` est une aide locale clairement étiquetée ; la production évaluée doit configurer un vrai modèle.
- N'invente jamais les noms des membres ni l'URL de production : conserve les marqueurs explicites à compléter.

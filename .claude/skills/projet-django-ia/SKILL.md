---
name: projet-django-ia
description: Cahier des charges et grille de contrôle du projet CadrIA (Django, IA, Celery, PostgreSQL, Redis, Docker, UI/UX et cloud).
---

# Projet Django & Intelligence Artificielle — CadrIA

Source d'évaluation : https://modules.apti.space/projets/django-ia

## Produit retenu

CadrIA transforme une idée de projet brute en brief exploitable : synthèse, objectifs, livrables, risques et prochaines
étapes. Un utilisateur authentifié conserve l'historique de ses analyses. Le fournisseur LLM est interchangeable ;
Mistral/OpenAI-compatible est la cible réelle et un mode `demo`, explicitement non-IA, facilite le développement local.

## Critères éliminatoires

Avant une livraison finale, tous doivent être vrais :

- le README commence par les noms et prénoms réels des membres ;
- l'URL HTTPS de production est renseignée et accessible ;
- un vrai modèle IA traite effectivement une demande ;
- aucune clé, aucun mot de passe et aucun secret n'est présent dans Git ;
- le guide `docker compose up --build` est reproductible.

Ne remplace jamais un nom ou une URL manquants par une invention. Laisse un marqueur visible et signale le blocage.

## Architecture obligatoire

- Django et son système `User`, avec profil utilisateur.
- ORM pour la demande, le résultat structuré et le journal d'appel.
- Client IA séparé des vues et réponses validées avant persistance.
- Celery + Redis pour les requêtes longues ; l'interface ne bloque pas.
- PostgreSQL comme base principale.
- Docker Compose : `web`, `worker`, `db`, `cache`, volumes et healthchecks.
- Gunicorn, image Python slim, processus non-root, migrations et `collectstatic` contrôlés.
- Variables d'environnement et `.env.example` exhaustif.

## États et erreurs

La machine d'état minimale est `pending -> processing -> succeeded|failed`. L'utilisateur reçoit immédiatement une page
d'attente, puis l'état est actualisé sans bloquer la navigation. Distinguer au minimum : quota, authentification du
fournisseur, délai/réseau, réponse invalide et panne générique. Les logs gardent les métadonnées utiles, jamais le secret
ni le prompt complet.

## UI/UX

- tokens sémantiques pour couleurs, typo, espaces, rayons, ombres et mouvement ;
- thèmes clair/sombre, responsive mobile-first et aucun CDN requis au runtime ;
- skeleton/progression contextualisés pendant l'inférence ;
- erreurs actionnables et état vide utile ;
- contraste WCAG, labels, clavier, `aria-live`, cibles tactiles de 44 px et mouvement réduit.

Consulter `design-system/cadria/MASTER.md` et le skill `ui-ux-pro-max` pour toute page.

## Tests et CI

- modèles, formulaires, permissions, vues, service IA et tâche Celery ;
- `unittest.mock` autour de tous les appels distants ;
- aucune consommation de token dans les tests ;
- Ruff + Black + checks Django + migrations + statiques + tests dans GitHub Actions.

## README attendu

Le rapport contient : membres, URL live, cas d'usage, lancement Docker, configuration du fournisseur, schéma du flux,
ERD, choix UI/UX, stratégie de latence, sécurité, coûts/quotas, performances, difficultés et post-mortem.

## Définition de terminé

Une fonctionnalité est terminée quand son chemin heureux et ses échecs sont testés, les contrôles qualité passent, le
Compose reste valide, l'interface est accessible et la documentation/configuration d'exemple est à jour.

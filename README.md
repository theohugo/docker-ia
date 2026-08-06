# CadrIA — copilote de brief propulsé par Django & IA

> **Membres du groupe : Hugo Raguin · Amine Taleb · Rizlene Berrag**<br>
> **Production : À COMPLÉTER — https://… (critère éliminatoire)**<br>
> État : `docker compose up --build` démarre un vrai modèle IA prêt à l'emploi (Ollama, sans clé) ; ajouter sa clé Groq
> dans `.env` active le fournisseur nominal (meilleures réponses, plus rapide) — voir « Intégrer sa clé API ».
> Déploiement public encore à renseigner.

CadrIA transforme une idée de projet encore floue en un brief actionnable : synthèse, objectifs, livrables, risques et
prochaines étapes. Chaque analyse est liée au compte qui l'a créée, exécutée hors de la requête HTTP par Celery, puis
conservée dans l'historique Django.

Le projet suit l'énoncé [Plateforme Web Django & Intelligence Artificielle](https://modules.apti.space/projets/django-ia)
et reprend les bonnes conventions d'architecture, de Docker et d'outillage du dépôt
[theohugo/Projet-carte](https://github.com/theohugo/Projet-carte), sans reprendre sa logique métier Pokémon.

## Ce qui fonctionne déjà

- inscription, connexion, profil automatique et historique privé par utilisateur ;
- création et validation serveur d'un brief ;
- traitement asynchrone Celery via Redis ;
- fournisseurs Mistral, Groq, OpenAI-compatible et Ollama local isolés derrière une interface ;
- Groq (`openai/gpt-oss-20b`) en fournisseur nominal dès qu'une clé est renseignée — validé en conditions réelles :
  brief `completed`, ~900 ms, 728 tokens ;
- Ollama (`qwen2.5:0.5b`) en fournisseur de secours actif par défaut, même sans clé Groq : `docker compose up --build`
  télécharge son modèle automatiquement si besoin et l'utilise réellement — validé de bout en bout, y compris à froid
  sur un volume vide et en tant que repli automatique quand Groq échoue ou n'est pas configuré ;
- réponse JSON validée avant persistance dans PostgreSQL ;
- mode `demo`, déterministe et sans réseau, conservé comme repli d'onboarding en changeant `AI_PROVIDER` ;
- progression par polling, skeleton contextualisé et erreurs quota/authentification/réseau explicites ;
- thèmes clair/sombre, responsive, navigation clavier et mouvement réduit ;
- image Docker Python 3.13 slim, non-root, Gunicorn, PostgreSQL, Redis, worker, volumes et healthchecks ;
- tests Django avec appels IA simulés, Ruff, Black, couverture et GitHub Actions ;
- instructions partagées pour Codex (`AGENTS.md`) et Claude Code (`CLAUDE.md`, agents et skills locaux).

> [!IMPORTANT]
> `.env.example` a `AI_PROVIDER=groq` (nominal) et `AI_FALLBACK_PROVIDER=ollama` (secours) par défaut. Sans clé Groq,
> chaque brief bascule automatiquement sur Ollama, local et sans clé : `cp .env.example .env` suivi de
> `docker compose up --build` suffit donc à obtenir un vrai modèle IA fonctionnel, avec ou sans clé. Ajouter une clé
> Groq (voir « Intégrer sa clé API ») donne de meilleures réponses, plus vite. Le fournisseur `demo` reste disponible
> (changer `AI_PROVIDER` dans `.env`) pour un onboarding encore plus léger, mais seul ne satisfait pas le critère
> éliminatoire « intégration IA fonctionnelle ». Il reste à reproduire une configuration IA réelle sur l'URL publique
> une fois déployée, puis à remplacer le marqueur « À COMPLÉTER » placé en tête de ce README.

## Démarrage rapide avec Docker

Prérequis : Docker Engine avec le plugin Compose.

```bash
cp .env.example .env
docker compose up --build
```

L'interface est ensuite disponible sur <http://localhost:8000>. Le service `web` applique les migrations et collecte les
statiques ; `worker` traite les briefs ; `db` et `cache` conservent respectivement les données et la file de tâches ;
`ollama` sert le vrai modèle IA (voir « Brancher un vrai modèle IA » ci-dessous).
Si le port 8000 est déjà occupé, modifier `CADRIA_PORT` dans `.env` avant le démarrage.

> [!NOTE]
> Au tout premier lancement, `docker compose up --build` télécharge l'image Ollama et le modèle `qwen2.5:0.5b`
> (environ 3,5 Go au total) : compter quelques minutes selon la connexion. Les démarrages suivants réutilisent le
> volume `ollama_data` et sont immédiats. Pour suivre la progression du téléchargement du modèle, ouvrir un second
> terminal et lancer `docker compose logs -f ollama`.
L'override de développement monte le code et utilise `runserver`. Pour valider exactement la commande Gunicorn de
production, sans charger cet override automatique :

```bash
docker compose -f docker-compose.yml up --build
```

Pour créer un administrateur :

```bash
docker compose exec web python manage.py createsuperuser
```

Pour arrêter sans perdre les volumes :

```bash
docker compose down
```

Ne pas ajouter `--volumes` sauf si la suppression de la base locale et de Redis est réellement souhaitée.

## Brancher un vrai modèle IA

CadrIA distingue un **fournisseur nominal** (celui qui traite les briefs en priorité) et un **fournisseur de secours**,
essayé automatiquement sur la même requête si le nominal échoue — indisponibilité, dépassement de temps, quota, clé
manquante ou réponse invalide. Par défaut, `.env.example` configure :

- **Nominal : Groq** (`openai/gpt-oss-20b`) — réponses plus riches et nettement plus rapides (~1 s vs ~30 s en local),
  mais nécessite une clé API personnelle ;
- **Secours : Ollama** (`qwen2.5:0.5b`), en local, sans clé — prend automatiquement le relais si Groq échoue ou si
  aucune clé n'est encore renseignée. C'est ce qui garantit qu'un clone tout juste récupéré, sans aucune clé
  configurée, reste immédiatement fonctionnel et satisfait à lui seul le critère « un vrai modèle IA traite
  effectivement une demande ».

Mistral ou toute API compatible OpenAI peuvent aussi remplacer Groq comme fournisseur nominal. Dans tous les cas, le
worker est le seul service qui appelle le modèle.

### Intégrer sa clé API (fournisseur nominal Groq)

Chaque personne (toi, un camarade, le prof) utilise **sa propre clé**, jamais partagée via Git — une clé API
authentifie un compte, pas le dépôt. Sans clé, le projet fonctionne quand même : chaque brief bascule automatiquement
sur le secours Ollama (voir plus bas), simplement avec des réponses plus modestes et plus lentes.

Étapes, après avoir cloné le dépôt :

1. Créer une clé dans la [console Groq](https://console.groq.com/keys) (compte gratuit).
2. Créer son `.env` s'il n'existe pas encore :
   ```bash
   cp .env.example .env
   ```
3. Ouvrir `.env` (jamais `.env.example`) et renseigner uniquement :
   ```dotenv
   AI_API_KEY=votre-cle-groq-locale
   ```
   `AI_PROVIDER=groq` et `AI_FALLBACK_PROVIDER=ollama` sont déjà positionnés par défaut — c'est la seule ligne à
   toucher.
4. Démarrer (ou recharger) la pile :
   ```bash
   docker compose up --build
   ```
   Si la pile tournait déjà sans clé, `docker compose up -d` suffit et recrée uniquement `worker` : une variable
   d'environnement n'est lue qu'à la création du conteneur, pas par un process déjà démarré.

Rien d'autre à faire : Groq devient actif dès le brief suivant, sans redémarrage applicatif ni action utilisateur.
`brief.provider`/`brief.model` et le pied de page de l'analyse reflètent toujours le fournisseur qui a réellement
répondu ; le journal (`GenerationEvent`) conserve `fallback_used`, `primary_provider` et `primary_error_code` pour
l'audit.

Au 5 août 2026, Groq documente un **Free Plan** et inclut `openai/gpt-oss-20b` dans ses
[limites gratuites](https://console.groq.com/docs/rate-limits). Ce quota est soumis à des limites de requêtes et de
tokens et peut évoluer : ce n'est ni une gratuité permanente ni une garantie de capacité. Une réponse HTTP 429 est
restituée comme un quota atteint, sans exposer la réponse brute à l'utilisateur.

> [!NOTE]
> Comportement validé de bout en bout dans les deux sens. **Sans clé** : le worker tente Groq, échoue proprement
> (`configuration_error`, clé manquante), puis bascule sur Ollama qui traite le brief avec succès (`completed`,
> `fallback_used=True`, `primary_provider=groq`) — aucun blocage. **Avec une vraie clé Groq** : le même scénario produit
> un aller-retour réseau réel et réussi, sans passer par le secours (`fallback_used=False`) — brief `completed`,
> `provider=groq`, `model=openai/gpt-oss-20b`, 728 tokens annoncés, ~0,9 s. Une coupure volontaire d'Ollama pendant
> qu'il était nominal a aussi été testée : bascule vers Groq réussie, 698 tokens, ~9,7 s.

### Fournisseur de secours : Ollama, local et sans clé

`.env.example` active `AI_FALLBACK_PROVIDER=ollama` et `COMPOSE_PROFILES=ollama` : le profil Compose `ollama` démarre
donc automatiquement, sans avoir besoin de passer `--profile ollama` — que Groq soit configuré ou non. Le modèle
utilisé est [`qwen2.5:0.5b`](https://ollama.com/library/qwen2.5) : son fichier quantifié fait environ 398 Mo, comprend
le français et sait produire du JSON. Cette taille privilégie la compatibilité avec un petit ordinateur ; la qualité
sera moins régulière qu'avec Groq.

Le conteneur `ollama` démarre son serveur puis **télécharge automatiquement `OLLAMA_MODEL` s'il est absent** avant de
répondre aux requêtes ; aucune commande manuelle n'est nécessaire. Son healthcheck ne passe au vert que lorsque le
modèle est réellement présent, et le `worker` attend cette même santé avant de traiter le premier brief — il n'y a
donc pas de risque de tomber sur un brief en échec parce que le téléchargement est encore en cours. Prévoir plusieurs
gigaoctets d'espace disque pour l'image Docker Ollama elle-même, en plus du modèle. Le port Ollama est publié
uniquement sur `127.0.0.1` afin de ne pas exposer sans authentification son API au réseau local.

Sans aucune clé configurée, il suffit donc de :

```bash
cp .env.example .env
docker compose up --build
```

pour obtenir un vrai modèle IA fonctionnel — Ollama traite alors tous les briefs en tant que secours. Les variables
`OLLAMA_*` de `.env.example` constituent les valeurs prudentes par défaut ; les changer dans `.env` si besoin :

```dotenv
AI_FALLBACK_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:0.5b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_NUM_CTX=4096
OLLAMA_KEEP_ALIVE=1m
OLLAMA_MEMORY_LIMIT=2g
OLLAMA_CPU_LIMIT=2.0
```

Le service est limité à un modèle chargé, une inférence à la fois, 2 CPU et 2 Go de mémoire. Le contexte de 4 096
tokens et `keep_alive=1m` réduisent aussi la pression mémoire. Ces limites protègent l'hôte contre un emballement du
conteneur, mais Docker, PostgreSQL, Redis et le système consomment encore de la mémoire : fermer les applications
lourdes et surveiller `docker stats` lors du premier essai. Si le port 11434 est déjà pris, changer `OLLAMA_PORT` ; seul
`OLLAMA_BASE_URL` est utilisé entre les conteneurs.

L'API native Ollama est appelée sans streaming avec un schéma JSON, conformément à la documentation des
[sorties structurées Ollama](https://docs.ollama.com/capabilities/structured-outputs). `AI_PROVIDER=ollama` fonctionne
aussi comme fournisseur nominal à part entière (au lieu de Groq), sans rien changer d'autre.

> [!NOTE]
> Ce chemin a été validé deux fois de bout en bout, y compris à froid (volume `ollama_data` vide, comme après un
> `git clone`) : `docker compose up --build` a téléchargé le modèle automatiquement, puis un brief réel a été mis en
> file, traité par `worker` et persisté avec le statut `completed` — 313 tokens annoncés, ~31 s de traitement sur un
> poste sans GPU dédié.

Pour désactiver Ollama entièrement (par exemple pour ne garder que Groq, sans filet), retirer ou vider
`COMPOSE_PROFILES` dans `.env` et `AI_FALLBACK_PROVIDER` : le `worker` démarre alors sans l'attendre. Pour arrêter
sans supprimer le modèle déjà téléchargé :

```bash
docker compose down
```

### Autre fournisseur nominal : Mistral ou API compatible OpenAI

Mistral peut remplacer Groq comme fournisseur nominal. Modifier uniquement le fichier local `.env` :

```dotenv
AI_PROVIDER=mistral
AI_API_KEY=votre-cle-locale
AI_BASE_URL=https://api.mistral.ai/v1
AI_MODEL=mistral-small-latest
AI_TIMEOUT_SECONDS=60
```

Puis reconstruire/redémarrer le web et le worker :

```bash
docker compose up --build
```

`AI_PROVIDER=openai_compatible` permet d'utiliser un autre service exposant `/chat/completions`, en adaptant
`AI_BASE_URL` et `AI_MODEL`. La clé ne doit jamais être ajoutée à `.env.example`, au Compose, au JavaScript, aux logs ou
à l'historique Git. En production, ces variables doivent être enregistrées dans le gestionnaire de secrets du cloud.

## Architecture technique et pipeline IA

```mermaid
flowchart LR
    U[Utilisateur] -->|HTTPS / session / CSRF| W[Django + Gunicorn]
    W -->|brief + état| P[(PostgreSQL)]
    W -->|tâche UUID| R[(Redis)]
    R --> C[Worker Celery]
    C -->|prompt borné| L[API LLM]
    L -->|JSON| C
    C -->|validation + résultat + journal| P
    U -->|polling état| W
    W -->|résultat du propriétaire| U
```

La vue ne contacte jamais le modèle. Elle valide le formulaire, crée le brief dans une transaction, publie son UUID et
rend immédiatement la page de progression. Le worker charge l'objet, le verrouille, passe son état à `processing`,
appelle le service IA, valide le schéma puis écrit le résultat. L'interface interroge un endpoint JSON à intervalle
croissant et recharge la restitution lorsqu'elle devient disponible.

Le résultat est volontairement restitué d'un bloc plutôt qu'en streaming de tokens : CadrIA exige un objet JSON complet
et validé. Le polling maintient l'interface réactive sans exposer une structure partielle ni retenir une connexion HTTP
longue.

### Modèle ORM

```mermaid
erDiagram
    USER ||--|| PROFILE : possede
    USER ||--o{ PROJECT_BRIEF : cree
    PROJECT_BRIEF ||--o| ANALYSIS_RESULT : produit
    PROJECT_BRIEF ||--o{ GENERATION_EVENT : journalise

    PROFILE {
        bigint id PK
        bigint user_id FK
        string display_name
        string company
        datetime created_at
    }
    PROJECT_BRIEF {
        uuid id PK
        bigint user_id FK
        string title
        text raw_idea
        text audience
        text constraints
        string status
        string provider
        string model
        string prompt_version
        string error_code
        datetime created_at
    }
    ANALYSIS_RESULT {
        bigint id PK
        uuid brief_id FK
        text summary
        json objectives
        json deliverables
        json risks
        json next_steps
        json raw_response
        int tokens_used
        int duration_ms
    }
    GENERATION_EVENT {
        bigint id PK
        uuid brief_id FK
        string event_type
        string provider
        string model
        json metadata
        datetime created_at
    }
```

### Cycle d'une analyse

```mermaid
stateDiagram-v2
    [*] --> Brouillon
    Brouillon --> En_attente: validation + publication Celery
    En_attente --> En_cours: prise en charge du worker
    En_cours --> Terminee: reponse valide persistee
    En_cours --> Echec: quota / auth / reseau / format
    Terminee --> [*]
    Echec --> [*]
```

## Design System et gestion de la latence

Le référentiel généré avec le skill `ui-ux-pro-max` est conservé dans `design-system/cadria/MASTER.md`. Les tokens
sémantiques de `static/css/tokens.css` pilotent couleurs, surfaces, contraste, espaces, rayons, ombres, typographie et
durées pour les deux thèmes. Le JavaScript et les styles applicatifs sont locaux ; Inter est chargée depuis Google Fonts
avec une pile de polices système en repli si la ressource distante est indisponible.

Pendant l'inférence, l'écran montre trois phases compréhensibles — préparation, analyse et restitution — accompagnées
d'un skeleton dont la géométrie annonce le futur résultat. Un `aria-live` informe les technologies d'assistance. Une
perte réseau déclenche des tentatives espacées et un bouton manuel ; une erreur du modèle explique si l'action attendue
est de patienter ou de contacter l'équipe. `prefers-reduced-motion` neutralise les animations non essentielles.

## Sécurité et confidentialité

- CSRF Django, sessions, mots de passe validés et échappement automatique des templates ;
- requêtes de détail et d'état filtrées par propriétaire pour empêcher les accès par UUID deviné ;
- clé IA lue uniquement côté serveur depuis l'environnement ;
- clé IA injectée dans le worker uniquement, pas dans le processus web ;
- taille d'entrée bornée avant l'appel externe et contenu utilisateur délimité comme donnée dans le prompt système ;
- erreurs publiques normalisées, sans clé, trace interne ou réponse brute ;
- métadonnées d'appel journalisées sans recopier le prompt dans les logs ;
- conteneur applicatif exécuté par un utilisateur système non-root.

Les entrées et réponses sont persistées parce qu'elles constituent le service d'historique demandé. La politique de
conservation et la suppression depuis l'interface font partie de la prochaine itération avant une mise en production
contenant des données réelles.

## Développement sans Docker

Prérequis : Python 3.13, [`uv`](https://docs.astral.sh/uv/) et, pour Celery non eager, un Redis local.

```bash
export DATABASE_URL="sqlite:////$(pwd)/db.sqlite3"
export REDIS_URL="redis://127.0.0.1:6379/0"
uv sync --locked
uv run python manage.py migrate
uv run python manage.py runserver
```

Dans un second terminal :

```bash
uv run celery -A config worker --loglevel=INFO
```

Ces exports remplacent les noms réseau `db` et `cache` du `.env` Docker pour une exécution directe sur l'hôte. Sans
`DATABASE_URL` ni `.env`, Django se replie également sur SQLite. L'environnement Docker et la cible de production
utilisent PostgreSQL.

## Tests, qualité et CI

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run black --check .
uv run coverage run manage.py test
uv run coverage report
docker compose config
```

Les tests du service remplacent le transport HTTP ou le fournisseur par `unittest.mock` : aucune clé ni aucun token ne
sont consommés. `.github/workflows/ci.yml` rejoue les vérifications avec PostgreSQL et Redis à chaque push sur `main` et
à chaque pull request.

## Structure du dépôt

```text
accounts/                 profils, inscription et signaux
briefs/                   ORM, formulaires, vues, tâches et services IA
config/                   réglages Django, URLs et configuration Celery
templates/                pages Django et états de l'expérience IA
static/                   tokens, composants, scripts et favicon locaux
.claude/agents/           rôles Claude Code spécialisés
.claude/skills/           cahier des charges, cours et skill UI/UX
.agents/skills/           skills agents interopérables
design-system/cadria/     source de vérité visuelle persistée
.github/workflows/        intégration continue
```

## Déploiement cloud — à finaliser

La première mise en ligne devra créer quatre briques : service web Gunicorn, worker Celery construit depuis la même
image, PostgreSQL géré et Redis géré. Les variables de `.env.example` seront saisies dans le cloud, `DJANGO_DEBUG=False`,
les domaines/origines HTTPS seront explicitement autorisés, puis
`DJANGO_SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`,
`SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True` et `SECURE_HSTS_PRELOAD=True` seront activés.
Après déploiement :

1. appliquer les migrations et vérifier `/health/` ;
2. créer un compte via l'interface ;
3. lancer un brief avec le vrai fournisseur ;
4. vérifier le worker, l'historique, les statiques et les erreurs publiques ;
5. inscrire l'URL HTTPS et les noms réels tout en haut de ce README.

## Rapport d'ingénierie et post-mortem initial

### Qualité du modèle

Le prompt impose cinq clés JSON, une température basse et sépare explicitement les données utilisateur des
instructions. Ce format rend la sortie testable et directement affichable. Les deux fournisseurs par défaut ont été
comparés sur le même brief : Groq (`openai/gpt-oss-20b`) produit des listes plus riches et détaillées quasi
instantanément, tandis qu'Ollama (`qwen2.5:0.5b`) reste cohérent mais avec des listes plus courtes — attendu pour un
modèle de 0,5 milliard de paramètres tournant sans GPU. C'est précisément pourquoi Groq est le nominal et Ollama le
secours : la qualité par défaut est la meilleure disponible sans clé partagée, tout en gardant un filet local. Il
faudra constituer un petit jeu de briefs représentatifs et noter la pertinence, la précision, le caractère actionnable
et le taux de réponses invalides avant de choisir définitivement le modèle de production.

### Coûts et quotas

Chaque résultat conserve le nombre total de tokens annoncé par le fournisseur et la durée, ce qui permettra d'estimer
le coût moyen. Sur le même brief, Groq a annoncé 728 tokens en ~0,9 s contre 327 tokens en ~32 s pour Ollama sur un
poste sans GPU dédié. Ollama n'a pas de coût par token mais consomme du temps CPU du worker ; Groq est soumis au quota
gratuit de la console (voir « Intégrer sa clé API »). Les garde-fous actuels sont la taille d'entrée, un modèle
configurable et la température faible. Restent à ajouter avant ouverture publique : quota par utilisateur, limite de
débit, budget mensuel avec alerte et politique de nouvelle tentative plafonnée.

### Difficultés traitées dans ce socle

- découpler une interaction lente de la requête web grâce à Celery ;
- présenter une progression honnête sans inventer un pourcentage d'inférence ;
- accepter plusieurs APIs compatibles sans propager leurs détails dans les vues ;
- garder un démarrage reproductible tout en proposant un mode sans clé aux contributeurs ;
- préserver un Compose autonome, contrairement au réseau Traefik externe du dépôt d'inspiration.

### Prochaines étapes

- [x] renseigner les noms complets de l'équipe ;
- [x] valider les deux fournisseurs par défaut de bout en bout (Groq nominal avec clé, Ollama en secours sans clé,
      bascule automatique testée dans les deux sens) ;
- [ ] documenter une évaluation comparative sur un jeu de briefs représentatif (Groq vs Ollama vs Mistral) avant
      remise ;
- [ ] ajouter relance contrôlée, suppression/export et quota par utilisateur ;
- [ ] choisir le stockage objet si des pièces jointes sont ajoutées ;
- [ ] déployer web, worker, PostgreSQL et Redis avec HTTPS ;
- [ ] renseigner l'URL publique, y reproduire la configuration IA réelle et compléter ce post-mortem avec des mesures
      issues de la production.

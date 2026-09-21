# Architecture — django-query-optimizer

> Généré à partir des fichiers du dépôt (manifests, README, source). En cas de divergence
> entre la documentation et les manifests, les manifests font foi (voir notes).

## Purpose

Plateforme d'analyse et d'optimisation de l'ORM Django. La bibliothèque collecte les requêtes
SQL exécutées, puis détecte les requêtes N+1, les requêtes dupliquées, les requêtes lentes et
les répétitions de lookups sur clés étrangères. Les résultats sont exposés dans Django Admin,
la suite de tests (plugin pytest), et via une sortie SARIF (VS Code / CI). Statut : pré-alpha.

## Stack

- Langage : Python 3.14 (classifier `Programming Language :: Python :: 3.14`).
- Framework : Django. Dépendance runtime `django>=6.0.7` (voir Note 1).
- Extras optionnels : `postgres` (psycopg2-binary), `drf` (djangorestframework),
  `realtime` (channels, daphne).
- Outillage dev : pytest, pytest-cov, pytest-django, ruff, mypy, django-stubs,
  djangorestframework-stubs, factory-boy.
- Build : setuptools>=70 + wheel (`setuptools.build_meta`).
- Conteneurisation : Docker + docker-compose (services `lint`, `test`).

## Layout

```
src/django_query_optimizer/
├── __init__.py                # API publique
├── py.typed                   # marqueur PEP 561
├── apps.py                    # AppConfig Django
├── store.py                   # QueryStore + RequestRecord (historique en mémoire)
├── _internal/                 # bootstrap (enregistrement idempotent) + version
├── collectors/                # QueryCollector (capture SQL, context-manager)
├── middleware/                # QueryOptimizerMiddleware (collecteur par requête)
├── analyzers/                 # QueryAnalyzer (requêtes lentes & dupliquées)
├── detectors/                 # base + N+1, select_related, drf_serializer
├── recommendations/           # ORMRecommendation + Severity
├── scoring/                   # QueryScorer (score 0-100 + note A-F)
├── regression/                # RegressionDetector (comparaison baseline, persistance JSON)
├── reporting/                 # SARIFReporter (SARIF 2.1)
├── admin/                     # dashboard Django Admin
├── migrations/                # 0001_initial
└── testing/                   # pytest_plugin (flag --query-analysis + fixture)
```

Autres répertoires : `tests/` (unit + integration, settings pytest-django), `examples/demo/`
(app Django de démonstration), `scripts/` (gen_context_files.py, quality_gate.py),
`docs/`, `standards/`, `.github/`.

## Entrypoints

- API publique : `django_query_optimizer/__init__.py` (dont `install()` via `_internal.bootstrap`).
- Middleware HTTP : `QueryOptimizerMiddleware` (middleware/query_collector_middleware.py).
- Plugin pytest : entry-point `pytest11` → `django_query_optimizer.testing.pytest_plugin`
  (ajoute le flag `--query-analysis`).
- Django Admin : dashboard sous `admin/`.
- N/A — pas de CLI console_scripts ni de point d'entrée serveur applicatif propre.

## Data / External deps

- Dépendance externe principale : Django (ORM `execute_wrapper` pour capturer les requêtes).
- Persistance : `store.py` conserve un historique de requêtes en mémoire ; `regression/`
  persiste une baseline en JSON. Une migration `0001_initial` est présente.
- Bases de données : PostgreSQL supporté via l'extra `postgres` (psycopg2-binary).
- Intégrations optionnelles : Django REST Framework (extra `drf`), channels/daphne
  (extra `realtime`).
- Sortie SARIF 2.1 pour VS Code / CI (`reporting/sarif.py`).

## Build & test

Cibles réelles (Makefile ; lint/typecheck/test s'exécutent via Docker) :

```bash
make install-dev     # installe le paquet + dépendances dev (local)
make lint            # ruff check (Docker)
make format          # ruff format (Docker)
make format-check    # vérifie le formatage sans modifier (Docker)
make typecheck       # mypy (Docker)
make test            # tests avec couverture (Docker)
make test-fast       # tests sans couverture (Docker)
make docker-test     # build + tests via Docker (cible CI)
make build           # build des images Docker (no cache)
make ci              # lint + typecheck + test
make clean           # nettoyage des artefacts et caches
```

Compose : services `lint` et `test` (`docker-compose.yml`), le service test expose
`coverage.xml` sur l'hôte pour SonarCloud.

## Notes (divergences doc vs manifests)

- Note 1 : `pyproject.toml` exige `django>=6.0.7`, alors que le README (badge « django 4.2+ »)
  et les classifiers (`Django :: 4.2 / 5.0 / 5.1`) indiquent des versions plus anciennes.
  Le manifest fait foi : Django >= 6.0.7 est requis à l'exécution.

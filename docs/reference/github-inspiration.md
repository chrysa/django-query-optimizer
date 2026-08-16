# Deep-dive — `django-query-optimizer`

**Repo local :** `/home/anthony/Documents/perso/projects/chrysa/django-query-optimizer`
**But (1 phrase) :** Plateforme d'analyse ORM Django qui capture les requêtes SQL au runtime (via `connection.execute_wrappers`) et détecte N+1, requêtes dupliquées/lentes, index manquants et FK non-`select_related`, avec restitution dans Django Admin, la suite de tests (pytest + SARIF) et VS Code.

**Stack :** Python 3.14+, Django 6.0+, setuptools, licence MIT. Architecture propre par couches (`collectors/`, `analyzers/`, `detectors/`, `scoring/`, `regression/`, `reporting/`, `middleware/`, `admin/`). Entry-point pytest11 = `django_query_optimizer.testing.pytest_plugin`. Phases 1-3 faites, phase 4 (VS Code SARIF) en cours, phase 5 (FastAPI/SQLAlchemy/Prisma) planifiée.

Le projet est un outil de profiling ORM avec plusieurs équivalents OSS matures et directement pertinents — pas d'outil interne sans référence. 5 sources retenues, toutes permissives (copiables sous attribution).

---

## 1. jazzband/django-debug-toolbar — panneau SQL

- **owner/repo :** jazzband/django-debug-toolbar
- **stars :** ~8.4k
- **activité :** actif (v7.1.1, support Django ≥5.2, ~2 986 commits)
- **langage :** Python
- **licence :** **BSD-3-Clause** → PERMISSIVE, copiable (conserver copyright + clause). Aucun copyleft.
- **module/pattern précis :** `debug_toolbar/panels/sql/tracking.py` — instrumentation des curseurs DB ; `panels/sql/panel.py` — agrégation, dédup, détection "similar/duplicate queries".
- **mécanisme réel :** wrappe l'exécution des curseurs via `connection.execute_wrapper` (même hook que ce projet utilise déjà dans `QueryCollector`) ; capture SQL + durée + stacktrace ; regroupe les requêtes identiques ("N similar queries") et signale les doublons exacts par hash du SQL normalisé. C'est exactement le modèle de `analyzers/query_analyzer.py` (slow + duplicate) de ce repo.
- **snippet portable (~12 lignes) — normalisation/hash pour dédup :**
  ```python
  import hashlib
  def _normalize(sql: str) -> str:
      # aligne sur DDT: strip params répétables pour regrouper "similar"
      return " ".join(sql.split())
  def duplicate_groups(captured):
      buckets: dict[str, list] = {}
      for q in captured:
          key = hashlib.md5(_normalize(q.sql).encode()).hexdigest()
          buckets.setdefault(key, []).append(q)
      return {k: v for k, v in buckets.items() if len(v) > 1}
  ```
- **intégration ici :** valider/affiner `QueryAnalyzer` duplicate detector contre l'approche DDT ; réutiliser leur heuristique "similar vs duplicate" (similar = même pattern params-strippés, duplicate = SQL identique littéral) pour enrichir la sévérité. Le panel HTML de DDT peut inspirer le dashboard `admin/`.
- **gotchas :** DDT s'appuie aussi sur `CursorWrapper` custom pour Python-side timing ; attention au double comptage si middleware + panel actifs. BSD-3 impose de garder l'avis de copyright si on copie du code littéral — préférer réimplémenter l'idée (trivial ici).

---

## 2. jmcarp/nplusone — détection N+1 par lazy-load

- **owner/repo :** jmcarp/nplusone
- **stars :** ~1.1k
- **activité :** faible/mature (~117 commits, peu de commits récents — projet stable mais quasi-dormant)
- **langage :** Python
- **licence :** **MIT** → PERMISSIVE, copiable.
- **module/pattern précis :** `nplusone/core/listeners.py` (LazyLoadListener / EagerLoadListener) + intégrations `nplusone/ext/django.py`.
- **mécanisme réel :** approche complémentaire à ce repo. Au lieu d'analyser a posteriori le flux SQL, nplusone **s'accroche aux signaux ORM** : il patche l'accès aux relations (descriptors `related`) pour détecter les lazy-loads déclenchés dans une boucle, et détecte aussi les eager-loads inutiles (`select_related`/`prefetch_related` chargés mais jamais consommés). Notification: "Potential n+1 query detected on `<model>.<field>`".
- **snippet portable (~10 lignes) — idée du "eager load inutile" (pas présent dans ce repo) :**
  ```python
  # Traquer les prefetch consommés vs déclarés pour flagguer l'over-fetch
  class PrefetchUsageTracker:
      def __init__(self): self.declared, self.accessed = set(), set()
      def note_prefetch(self, model, field): self.declared.add((model, field))
      def note_access(self, model, field): self.accessed.add((model, field))
      def unused(self): return self.declared - self.accessed
  ```
- **intégration ici :** ajouter un `EagerLoadDetector` (angle mort actuel du repo : il ne détecte que le sous-fetch, pas le sur-fetch). Le nom résolu `model.field` de nplusone est plus riche que le `python_file:line` actuel — envisager de résoudre le champ de relation pour de meilleures recommandations `select_related('author')`.
- **gotchas :** le monkey-patching des descriptors ORM est fragile entre versions Django et intrusif (nplusone n'a pas suivi les Django récents) — d'où le choix de ce repo (execute_wrapper) qui est plus robuste. Ne pas reprendre le patching ; reprendre seulement le concept eager-load-unused. MIT = copiable tel quel avec l'avis de licence.

---

## 3. jazzband/django-silk — profiling requête + EXPLAIN

- **owner/repo :** jazzband/django-silk
- **stars :** ~5.0k
- **activité :** actif (maintenu par Jazzband, CI récente, ~1 015 commits)
- **langage :** Python
- **licence :** **MIT** → PERMISSIVE, copiable.
- **module/pattern précis :** `silk/sql.py` (wrapping execution), `silk/model_factory.py` (persistance SQLQuery), option `SILKY_ANALYZE_QUERIES` + `SILKY_EXPLAIN_FLAGS`.
- **mécanisme réel :** intercepte chaque requête d'une requête HTTP, stocke tables impliquées / nb de joins / temps d'exécution + stacktrace ; optionnellement exécute `EXPLAIN [ANALYZE]` (PostgreSQL) pour un plan réel — c'est le chaînon manquant pour la détection "missing index" mentionnée dans le README de ce repo mais non encore implémentée sérieusement.
- **snippet portable (~12 lignes) — EXPLAIN sécurisé pour détecter Seq Scan / index manquant :**
  ```python
  def explain(connection, sql, params):
      with connection.cursor() as cur:
          cur.execute(f"EXPLAIN (FORMAT JSON) {sql}", params)
          plan = cur.fetchone()[0][0]["Plan"]
      return plan  # inspecter plan["Node Type"] == "Seq Scan" + "Rows"
  def flags_seq_scan(plan) -> bool:
      if plan.get("Node Type") == "Seq Scan" and plan.get("Plan Rows", 0) > 1000:
          return True
      return any(flags_seq_scan(c) for c in plan.get("Plans", []))
  ```
- **intégration ici :** brancher un détecteur `MissingIndexDetector` optionnel (extra `postgres` déjà déclaré dans pyproject) qui, sur les requêtes lentes, lance EXPLAIN et flag les `Seq Scan` sur gros volumes. Gate derrière un flag config comme `SILKY_ANALYZE_QUERIES` (jamais en prod par défaut).
- **gotchas :** EXPLAIN ANALYZE **exécute réellement** la requête (writes inclus !) — n'utiliser que `EXPLAIN` (sans ANALYZE) ou envelopper dans une transaction rollback. Coût perf non négligeable → opt-in strict. MIT ok.

---

## 4. adamchainz/django-perf-rec — régression par enregistrement

- **owner/repo :** adamchainz/django-perf-rec
- **stars :** ~356
- **activité :** actif (mainteneur adamchainz très actif, ~770 commits)
- **langage :** Python
- **licence :** **MIT** → PERMISSIVE, copiable.
- **module/pattern précis :** `django_perf_rec/api.py` (`record()` context manager), `django_perf_rec/orm.py` (fingerprinting SQL), fichiers `*.perf.yml` de référence.
- **mécanisme réel :** context manager `record()` qui capture toutes les requêtes DB + ops cache, **fingerprint** le SQL (remplace valeurs variables par `#`/`...`), sérialise en YAML à côté du test, et compare au run suivant → assertion si diff. Directement pertinent pour le `RegressionDetector` de ce repo (qui fait baseline compare + JSON persist) : perf-rec est la référence canonique du pattern, mais en YAML lisible par humain et versionné.
- **snippet portable (~10 lignes) — fingerprinting stable pour baseline :**
  ```python
  import re
  def fingerprint(sql: str) -> str:
      sql = re.sub(r"'[^']*'", "#", sql)            # strings
      sql = re.sub(r"\b\d+\b", "#", sql)            # nombres
      sql = re.sub(r"\bIN\s*\([^)]+\)", "IN (...)", sql, flags=re.I)  # IN lists variables
      return " ".join(sql.split())
  ```
- **intégration ici :** aligner `regression/detector.py` sur ce fingerprinting (le repo a déjà `_LITERAL_RE` dans `n_plus_one.py` — factoriser en un module `fingerprint` partagé). Envisager un mode YAML versionné (en plus du JSON) pour diffs revue PR lisibles. Reprendre l'idée "IN (...)" que le regex actuel du repo ne couvre pas.
- **gotchas :** le fingerprinting doit être déterministe entre backends DB (les guillemets d'identifiants diffèrent Postgres/MySQL/SQLite) — normaliser avant hash. Fichiers de référence à committer, sinon 1er run = toujours vert. MIT ok.

---

## 5. microsoft/sarif-tutorials — format SARIF 2.1 (reporting)

- **owner/repo :** microsoft/sarif-tutorials (réf. normative pour `reporting/sarif.py`)
- **stars :** ~359
- **activité :** mature/stable
- **langage :** Markdown/docs + exemples JSON
- **licence :** **dual CC-BY-4.0 (docs) + MIT (code)** → PERMISSIVE. Le schéma SARIF lui-même est un standard OASIS ouvert. Copiable.
- **module/pattern précis :** structure `sarifLog` → `runs[]` → `tool.driver.rules[]` + `results[]` avec `ruleId`, `level`, `message`, `locations[].physicalLocation`.
- **mécanisme réel :** SARIF est le format d'échange standard consommé nativement par VS Code (extension SARIF Viewer) et GitHub Code Scanning. Chaque `result` pointe un fichier:ligne (`region.startLine`) + niveau (`error`/`warning`/`note`). C'est exactement ce dont la phase 4 (VS Code inline diagnostics) a besoin — mapper chaque `ORMRecommendation` (avec son `python_file`/`python_line`) vers un `result`.
- **snippet portable (~16 lignes) — squelette SARIF minimal valide :**
  ```python
  def to_sarif(recommendations):
      return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
          "tool": {"driver": {"name": "django-query-optimizer",
            "rules": [{"id": r.issue_type} for r in {x.issue_type: x for x in recommendations}.values()]}},
          "results": [{
            "ruleId": r.issue_type,
            "level": {"CRITICAL":"error","HIGH":"error","MEDIUM":"warning","LOW":"note"}.get(r.severity.name,"warning"),
            "message": {"text": r.message},
            "locations": [{"physicalLocation": {
              "artifactLocation": {"uri": r.python_file},
              "region": {"startLine": r.python_line}}}],
          } for r in recommendations],
        }],
      }
  ```
- **intégration ici :** vérifier que `reporting/sarif.py` respecte bien `level` ∈ {none,note,warning,error} (SARIF n'a pas "critical" — mapper CRITICAL/HIGH→error). Ajouter `$schema` pour l'auto-complétion/validation VS Code. Publier le SARIF en artefact CI pour GitHub Code Scanning (upload-sarif action).
- **gotchas :** URIs doivent être relatifs à la racine repo (sinon VS Code ne résout pas le fichier) ; `startLine` est 1-indexé. GitHub Code Scanning rejette >5000 results/run et exige `partialFingerprints` pour un bon dedup entre runs — à ajouter pour le suivi des régressions côté GitHub.

---

## Synthèse licences

**Toutes permissives** — aucune source copyleft/restrictive (pas de GPL/AGPL/BSL/Elastic/fair-code) :
- BSD-3-Clause : django-debug-toolbar
- BSD-2-Clause : (django-zen-queries, cité pour mémoire dans la recherche)
- MIT : nplusone, django-silk, django-perf-rec, sarif-tutorials (code)
- CC-BY-4.0 : docs sarif-tutorials

→ Code copiable sous réserve de conserver l'avis de copyright/licence. Vu la trivialité des snippets, préférer la réimplémentation (déjà le cas dans ce repo).

## Priorités d'intégration (quick-wins d'abord)
1. **SARIF `$schema` + mapping level + partialFingerprints** (phase 4 en cours) — petit, débloque VS Code + GitHub Code Scanning. (source 5)
2. **Factoriser le fingerprinting** partagé entre `n_plus_one.py` et `regression/detector.py`, ajouter cas `IN (...)`. (source 4)
3. **EagerLoadDetector** (sur-fetch inutile) — angle mort actuel. (source 2)
4. **MissingIndexDetector via EXPLAIN** opt-in derrière extra `postgres`. (source 3)

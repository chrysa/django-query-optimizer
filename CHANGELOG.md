# Changelog

All notable changes to `django-query-optimizer` will be documented here.
Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Features
- QueryCollector via Django `execute_wrapper`
- QueryAnalyzer with slow query and duplicate query detection
- ORMRecommendation data class with severity ordering
- pytest plugin scaffold (`--query-analysis` flag, `query_collector` fixture)

# Diagrammes UML — ENSO Monitor (#17)

Ce dossier documente le MVP **tel qu'implémenté**, à partir des modèles SQLAlchemy et du parcours React → FastAPI → PostgreSQL. Les blocs `mermaid` sont directement rendus par GitHub dans chaque fichier Markdown.

| Diagramme | Source Mermaid | Export SVG | Export PNG |
|---|---|---|---|
| Cas d'utilisation | [use-case.md](use-case.md) | [SVG](exports/use-case.svg) | [PNG](exports/use-case.png) |
| Classes du domaine | [class-diagram.md](class-diagram.md) | [SVG](exports/class-diagram.svg) | [PNG](exports/class-diagram.png) |
| Séquence de consultation | [sequence-diagram.md](sequence-diagram.md) | [SVG](exports/sequence-diagram.svg) | [PNG](exports/sequence-diagram.png) |

## Lecture et précautions

- Le diagramme de cas d'utilisation utilise un **flowchart Mermaid**, car Mermaid ne propose pas de syntaxe native de diagramme UML de cas d'utilisation ; le cadre représente la frontière de l'application et les ovales les cas.
- La cardinalité `0..*` du côté de `Observation` sur `Import` est volontaire : un réimport sans changement ne déplace aucune observation vers le nouvel import.
- Le cas de séquence **HTTP 422** concerne la validation de l'API ; dans le formulaire, une période inversée est bloquée avant l'appel HTTP.
- Les fichiers `exports/*.svg` sont vectoriels et recommandés pour le dossier HETIC ; les PNG sont fournis pour la compatibilité avec les éditeurs de documents.

Pour préparer le PDF de conception, insérer les fichiers SVG (ou PNG) et conserver la justification des relations et des scénarios figurant sous chaque diagramme Markdown. La source de vérité est le bloc Mermaid de chaque fichier `.md` ; les exports illustrent les mêmes parcours et relations dans un format statique adapté au PDF.

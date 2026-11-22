# Diagramme de séquence : consultation du graphique ONI

```mermaid
sequenceDiagram
    autonumber
    actor V as Visiteur
    participant UI as React App
    participant Client as Client HTTP
    participant Route as Route FastAPI
    participant Service as Service
    participant Repo as Repository
    participant DB as PostgreSQL

    V->>UI: Choisit début / fin puis Actualiser
    alt Début après fin
        UI-->>V: Message de validation local (aucun GET)
    else Période cohérente
        UI->>UI: Etat loading, masque l'ancienne courbe
        UI->>Client: fetchObservations(start, end)
        Client->>Route: GET /api/v1/observations?start=...&end=...
        alt Paramètres API invalides
            Route-->>Client: HTTP 422
            Client-->>UI: Rejet de la promesse (Erreur API: 422)
            UI-->>V: Alerte et bouton Réessayer
        else Erreur HTTP 5xx ou échec réseau
            opt Le serveur répond avec une erreur
                Route-->>Client: HTTP 5xx
            end
            Client-->>UI: Rejet de la promesse
            UI-->>V: Alerte et bouton Réessayer
        else Requête valide avec réponse 200
            Route->>Service: construire_reponse_observations(db, filtres)
            Service->>Repo: lister_observations(db, debut, fin)
            Repo->>DB: SELECT observations + provenance
            DB-->>Repo: Observations et relations
            Repo-->>Service: Liste triée par date
            Service-->>Route: ObservationsResponse
            Route-->>Client: HTTP 200 + JSON
            Client-->>UI: Observations et provenance
            alt Observations présentes
                UI-->>V: Courbe + statistiques + source si commune
            else Période vide
                UI-->>V: Aucune observation (sans graphique)
            end
        end
    end
```

**Commentaire (3 phrases).** La demande du **Visiteur** traverse le client React, la route FastAPI, le service métier, le repository SQLAlchemy et PostgreSQL ; le service renvoie la provenance par observation. Le frontend rejette une période inversée **sans appel HTTP**, tandis que FastAPI renvoie **422** si les paramètres de l'API sont invalides ; un résultat vide affiche un message sans courbe. En cas d'erreur API/réseau, l'ancienne courbe reste masquée et le Visiteur peut réessayer ; un identifiant de requête empêche aussi une ancienne réponse d'écraser la plus récente.

**Cas justifiés :** les branches représentent les chemins codés dans [`frontend/src/App.tsx`](../../frontend/src/App.tsx), [`frontend/src/api/client.ts`](../../frontend/src/api/client.ts) et [`api/app/routes/observations.py`](../../api/app/routes/observations.py). L'échec HTTP 5xx/réseau est un scénario alternatif à la réponse 200, et non une étape qui la suit.

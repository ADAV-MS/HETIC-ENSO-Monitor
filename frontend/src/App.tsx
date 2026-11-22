import { useState, useEffect, useCallback, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchObservations, type ObservationsResponse } from './api/client';
import Comparison from './components/Comparison';
import './App.css';

type Period = { start: string; end: string };
type LoadState =
  | { status: 'loading'; period: Period }
  | { status: 'success'; period: Period; data: ObservationsResponse }
  | { status: 'error'; period: Period; message: string };

function App() {
  const [start, setStart] = useState('1997-01-01');
  const [end, setEnd] = useState('1998-12-31');
  const [result, setResult] = useState<LoadState>({
    status: 'loading', period: { start: '1997-01-01', end: '1998-12-31' },
  });
  const requestId = useRef(0);

  const fetchPeriod = useCallback(async (period: Period) => {
    const id = ++requestId.current;
    try {
      const data = await fetchObservations(period.start, period.end);
      if (id === requestId.current) {
        setResult({ status: 'success', period, data });
      }
    } catch (err) {
      if (id === requestId.current) {
        setResult({
          status: 'error', period,
          message: err instanceof Error ? err.message : "Erreur de connexion à l'API",
        });
      }
    }
  }, []);

  // L'état initial est déjà 'loading'. L'effet déclenche la lecture réseau,
  // puis les callbacks asynchrones mettent à jour l'interface.
  useEffect(() => {
    const period: Period = { start: '1997-01-01', end: '1998-12-31' };
    const id = ++requestId.current;

    void fetchObservations(period.start, period.end).then(
      (data) => {
        if (id === requestId.current) {
          setResult({ status: 'success', period, data });
        }
      },
      (err: unknown) => {
        if (id === requestId.current) {
          setResult({
            status: 'error', period,
            message: err instanceof Error ? err.message : "Erreur de connexion à l'API",
          });
        }
      },
    );

    return () => { requestId.current += 1; };
  }, []);

  const loadData = (period: Period) => {
    setResult({ status: 'loading', period });
    void fetchPeriod(period);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const period = { start, end };
    if (start > end) {
      requestId.current += 1;
      setResult({ status: 'error', period, message: 'La date de début doit être antérieure à la date de fin.' });
      return;
    }
    loadData(period);
  };

  const loading = result.status === 'loading';
  const data = result.status === 'success' ? result.data : null;
  const stats = data && data.observations.length > 0
    ? {
        moyenne: (data.observations.reduce((s, o) => s + o.value, 0) / data.observations.length).toFixed(2),
        min: Math.min(...data.observations.map((o) => o.value)).toFixed(2),
        max: Math.max(...data.observations.map((o) => o.value)).toFixed(2),
      }
    : null;

  return (
    <main className="app">
      <a href="#contenu" className="skip-link">Aller au contenu</a>
      <header>
        <h1 id="contenu">ENSO Monitor</h1>
        <p className="subtitle">Indice ONI — NOAA CPC</p>
      </header>

      <form onSubmit={handleSubmit} className="filters" aria-busy={loading}>
        <label htmlFor="start">
          Date de début
          <input id="start" type="date" value={start} onChange={(e) => setStart(e.target.value)} required />
        </label>
        <label htmlFor="end">
          Date de fin
          <input id="end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} required />
        </label>
        <button type="submit" disabled={loading}>{loading ? 'Chargement...' : 'Actualiser'}</button>
      </form>

      {loading && <p role="status" aria-live="polite">Chargement des observations du {result.period.start} au {result.period.end}…</p>}
      {result.status === 'error' && (
        <div className="error" role="alert">
          <p>Impossible de charger la période du {result.period.start} au {result.period.end} : {result.message}</p>
          {result.period.start <= result.period.end && (
            <button type="button" onClick={() => loadData(result.period)}>Réessayer</button>
          )}
        </div>
      )}

      {data && (
        <section aria-label="Résultats de la période chargée">
          <p className="meta">Période affichée : <strong>{result.period.start} au {result.period.end}</strong></p>
          {data.source ? (
            <p className="meta">
              Source : <strong>{data.source}</strong> — version {data.version}
              {data.extracted_at && (
                <> — extrait le {new Date(data.extracted_at).toLocaleDateString('fr-FR')}</>
              )}
            </p>
          ) : data.observations.length > 0 ? (
            <p className="meta">
              Plusieurs sources ou indices pour cette période ; chaque observation
              possède sa propre provenance dans la réponse API.
            </p>
          ) : null}
          {data.unit && <p className="meta">Unité : {data.unit} (anomalie Niño 3.4)</p>}

          {data.observations.length === 0 ? (
            <p className="empty">Aucune observation pour cette période.</p>
          ) : (
            <>
              <div className="chart" role="img" aria-label={`Graphique de l'indice ONI de ${result.period.start} à ${result.period.end}`}>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={data.observations}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#cccccc" />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis domain={[-3, 3]} label={{ value: 'ONI (°C)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip formatter={(value) => `${value} °C`} />
                    <Line type="monotone" dataKey="value" stroke="#004080" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <table>
                <caption>Statistiques sur la période</caption>
                <thead><tr><th scope="col">Moyenne</th><th scope="col">Minimum</th><th scope="col">Maximum</th></tr></thead>
                <tbody><tr><td>{stats?.moyenne} °C</td><td>{stats?.min} °C</td><td>{stats?.max} °C</td></tr></tbody>
              </table>
            </>
          )}
        </section>
      )}
      <Comparison />
    </main>
  );
}

export default App;

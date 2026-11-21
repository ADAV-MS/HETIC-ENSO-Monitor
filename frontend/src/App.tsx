import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchObservations, type ObservationsResponse } from './api/client';
import './App.css';

function App() {
  const [start, setStart] = useState('1997-01-01');
  const [end, setEnd] = useState('1998-12-31');
  const [data, setData] = useState<ObservationsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (s: string, e: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchObservations(s, e);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(start, end);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (start > end) {
      setError('La date de début doit être antérieure à la date de fin.');
      return;
    }
    loadData(start, end);
  };

  const stats =
    data && data.observations.length > 0
      ? {
        moyenne: (data.observations.reduce((s, o) => s + o.value, 0) / data.observations.length).toFixed(2),
        min: Math.min(...data.observations.map((o) => o.value)).toFixed(2),
        max: Math.max(...data.observations.map((o) => o.value)).toFixed(2),
      }
      : null;

  return (
    <main className="app">
      <h1>ENSO Monitor</h1>
      <p className="subtitle">Indice ONI — NOAA CPC</p>

      <form onSubmit={handleSubmit} className="filters">
        <label htmlFor="start">
          Date de début
          <input
            id="start"
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            required
          />
        </label>
        <label htmlFor="end">
          Date de fin
          <input
            id="end"
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Chargement...' : 'Actualiser'}
        </button>
      </form>

      {error && (
        <div className="error" role="alert">
          <p>Erreur : {error}</p>
          <button onClick={() => loadData(start, end)} disabled={loading}>
            {loading ? 'Nouvel essai...' : 'Réessayer'}
          </button>
        </div>
      )}

      {data && (
        <>
          <p className="meta">
            Source : <strong>{data.source}</strong> — version {data.version} — extrait le{' '}
            {new Date(data.extracted_at).toLocaleDateString('fr-FR')}
          </p>
          <p className="meta">Unité : {data.unit} (anomalie Niño 3.4)</p>

          {data.observations.length === 0 ? (
            <p className="meta">Aucune observation pour cette période.</p>
          ) : (
            <>
              <div
                className="chart"
                role="img"
                aria-label={`Graphique de l'indice ONI de ${start} à ${end}`}
              >
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={data.observations}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#cccccc" />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis
                      domain={[-3, 3]}
                      label={{ value: 'ONI (°C)', angle: -90, position: 'insideLeft' }}
                    />
                    <Tooltip formatter={(value) => `${value} °C`} />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#004080"
                      dot={false}
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <table>
                <caption>Statistiques sur la période</caption>
                <thead>
                  <tr>
                    <th scope="col">Moyenne</th>
                    <th scope="col">Minimum</th>
                    <th scope="col">Maximum</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{stats?.moyenne} °C</td>
                    <td>{stats?.min} °C</td>
                    <td>{stats?.max} °C</td>
                  </tr>
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </main>
  );
}

export default App;
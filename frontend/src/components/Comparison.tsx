import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchObservations, type ObservationsResponse } from '../api/client';
import './Comparison.css';

interface WindowDef {
  start: string;
  end: string;
  label: string;
}

const WINDOWS: WindowDef[] = [
  { start: '1997-01-01', end: '1998-12-31', label: '1997–1998' },
  { start: '2015-01-01', end: '2016-12-31', label: '2015–2016' },
];

interface WindowStats {
  moyenne: string;
  min: string;
  max: string;
}

function computeStats(data: ObservationsResponse | null): WindowStats | null {
  if (!data || data.observations.length === 0) return null;
  const values = data.observations.map((o) => o.value);
  return {
    moyenne: (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2),
    min: Math.min(...values).toFixed(2),
    max: Math.max(...values).toFixed(2),
  };
}

export default function Comparison() {
  const [dataA, setDataA] = useState<ObservationsResponse | null>(null);
  const [dataB, setDataB] = useState<ObservationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [a, b] = await Promise.all([
          fetchObservations(WINDOWS[0].start, WINDOWS[0].end),
          fetchObservations(WINDOWS[1].start, WINDOWS[1].end),
        ]);
        setDataA(a);
        setDataB(b);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur inconnue');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <section className="comparison" aria-labelledby="comparison-title">
      <h2 id="comparison-title">Comparaison de deux fenêtres historiques</h2>

      {loading && <p className="meta">Chargement des deux fenêtres…</p>}
      {error && (
        <p className="comparison-error" role="alert">
          Erreur : {error}
        </p>
      )}

      {!loading && !error && dataA && dataB && (
        <>
          <div className="windows">
            {[
              { data: dataA, w: WINDOWS[0] },
              { data: dataB, w: WINDOWS[1] },
            ].map(({ data, w }) => {
              const stats = computeStats(data);
              return (
                <article key={w.label} className="window">
                  <h3>{w.label}</h3>
                  <div role="img" aria-label={`Graphique ONI pour la fenêtre ${w.label}`}>
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={data.observations}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#cccccc" />
                        <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                        <YAxis domain={[-3, 3]} tick={{ fontSize: 10 }} />
                        <Tooltip formatter={(v) => `${v} °C`} />
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
                  {stats && (
                    <table className="stats-table">
                      <caption>Statistiques {w.label}</caption>
                      <thead>
                        <tr>
                          <th scope="col">Moyenne</th>
                          <th scope="col">Min</th>
                          <th scope="col">Max</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>{stats.moyenne} °C</td>
                          <td>{stats.min} °C</td>
                          <td>{stats.max} °C</td>
                        </tr>
                      </tbody>
                    </table>
                  )}
                </article>
              );
            })}
          </div>

          <div className="interpretation">
            <h3>Interprétation prudente</h3>
            <p>
              Ces deux fenêtres présentent des valeurs ONI positives prolongées, indiquant
              une anomalie chaude de la température de surface de la mer dans la région
              Niño 3.4. L'ONI est un indicateur climatique parmi d'autres : il ne mesure pas
              directement les impacts (sécheresses, précipitations, tempêtes) et ne permet
              aucune prévision. Le terme « Super El Niño » n'est pas utilisé ici car il ne
              correspond pas à une classification scientifique universelle ; toute
              catégorisation nécessiterait des seuils, une durée et un indice explicitement
              définis.
            </p>
          </div>
        </>
      )}
    </section>
  );
}
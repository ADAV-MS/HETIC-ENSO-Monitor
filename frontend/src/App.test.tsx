import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import App from './App';

// Isole les tests de filtrage des requêtes déclenchées par Comparison.
vi.mock('./components/Comparison', () => ({ default: () => null }));

const mockFetch = vi.fn();

function buildResponse(observations: { date: string; value: number }[]) {
  return {
    source: 'NOAA CPC',
    indice: 'Oceanic Niño Index',
    unit: '°C anomaly',
    version: 'v6',
    extracted_at: '2026-11-16T14:36:22',
    observations,
  };
}

beforeEach(() => {
  mockFetch.mockReset();
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('App', () => {
  it('appelle fetch avec les nouvelles dates après changement de période', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => buildResponse([{ date: '1997-01-01', value: 1.5 }]),
    });

    render(<App />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    mockFetch.mockClear();

    fireEvent.change(screen.getByLabelText(/Date de début/i), {
      target: { value: '2015-01-01' },
    });
    fireEvent.change(screen.getByLabelText(/Date de fin/i), {
      target: { value: '2016-12-31' },
    });
    fireEvent.click(screen.getByRole('button', { name: /actualiser/i }));

    await waitFor(() => {
      const urls = mockFetch.mock.calls.map((c) => String(c[0]));
      expect(
        urls.some(
          (u) => u.includes('start=2015-01-01') && u.includes('end=2016-12-31')
        )
      ).toBe(true);
    });
  });

  it('met à jour les valeurs affichées après changement de période', async () => {
    mockFetch.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('start=2015-01-01') && url.includes('end=2016-12-31')) {
        return Promise.resolve({
          ok: true,
          json: async () =>
            buildResponse([
              { date: '2015-01-01', value: 2.5 },
              { date: '2015-02-01', value: 2.6 },
            ]),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () =>
          buildResponse([
            { date: '1997-01-01', value: 1.5 },
            { date: '1997-02-01', value: 2.0 },
          ]),
      });
    });

    render(<App />);

    const mainTable = await screen.findByRole(
      'table',
      { name: /Statistiques sur la période/i },
      { timeout: 3000 }
    );

    expect(within(mainTable).getByText(/2\.00\s*°C/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Date de début/i), {
      target: { value: '2015-01-01' },
    });
    fireEvent.change(screen.getByLabelText(/Date de fin/i), {
      target: { value: '2016-12-31' },
    });
    fireEvent.click(screen.getByRole('button', { name: /actualiser/i }));

    await waitFor(() => {
      const updatedTable = screen.getByRole('table', { name: /Statistiques sur la période/i });
      expect(within(updatedTable).getByText(/2\.60\s*°C/)).toBeInTheDocument();
    });
  });
});
// Une période mixte ou vide ne possède pas de métadonnées globales fiables.
describe('provenance des observations', () => {
  it("n'affiche pas une fausse source ni une date invalide pour une période mixte", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        ...buildResponse([{ date: '1997-01-01', value: 1.5 }]),
        source: null,
        indice: null,
        unit: null,
        version: null,
        extracted_at: null,
      }),
    });

    render(<App />);
    expect(await screen.findByText(/Plusieurs sources ou indices/i)).toBeInTheDocument();
    expect(screen.queryByText(/Invalid Date/i)).not.toBeInTheDocument();
  });
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

describe('états de chargement et d’erreur', () => {
  it('cache les anciennes données pendant le chargement et en cas d’erreur, puis permet de réessayer', async () => {
    const pending = deferred<{ ok: boolean; json: () => Promise<ReturnType<typeof buildResponse>> }>();
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => buildResponse([{ date: '1997-01-01', value: 1.5 }]) })
      .mockImplementationOnce(() => pending.promise)
      .mockResolvedValueOnce({ ok: true, json: async () => buildResponse([{ date: '2015-01-01', value: 2.5 }]) });

    render(<App />);
    expect(await screen.findByRole('table', { name: /Statistiques sur la période/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Date de début/i), { target: { value: '2015-01-01' } });
    fireEvent.change(screen.getByLabelText(/Date de fin/i), { target: { value: '2016-12-31' } });
    // Editing the form must not change the period on the already loaded chart.
    expect(screen.getByRole('img', { name: /1997-01-01 à 1998-12-31/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /actualiser/i }));
    expect(screen.getByRole('status')).toHaveTextContent('2015-01-01');
    expect(screen.queryByRole('table', { name: /Statistiques sur la période/i })).not.toBeInTheDocument();
    pending.reject(new Error('Service temporairement indisponible'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Service temporairement indisponible');
    expect(screen.queryByRole('img', { name: /Graphique de l'indice ONI/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Réessayer/i }));
    expect(await screen.findByRole('img', { name: /2015-01-01 à 2016-12-31/ })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('affiche un état vide sans graphique pour une période sans observation', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => buildResponse([]) });
    render(<App />);
    expect(await screen.findByText('Aucune observation pour cette période.')).toBeInTheDocument();
    expect(screen.getByText(/Période affichée/)).toHaveTextContent('1997-01-01 au 1998-12-31');
    expect(screen.queryByRole('img', { name: /Graphique de l'indice ONI/ })).not.toBeInTheDocument();
  });

  it('refuse une période invalide sans afficher les anciennes données', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => buildResponse([{ date: '1997-01-01', value: 1.5 }]) });
    render(<App />);
    await screen.findByRole('table', { name: /Statistiques sur la période/i });
    fireEvent.change(screen.getByLabelText(/Date de début/i), { target: { value: '2018-01-01' } });
    fireEvent.change(screen.getByLabelText(/Date de fin/i), { target: { value: '2016-12-31' } });
    fireEvent.click(screen.getByRole('button', { name: /actualiser/i }));
    expect(screen.getByRole('alert')).toHaveTextContent('La date de début doit être antérieure');
    expect(screen.queryByRole('table', { name: /Statistiques sur la période/i })).not.toBeInTheDocument();
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});

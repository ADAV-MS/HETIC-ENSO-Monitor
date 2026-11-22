export interface ObservationProvenance {
  source_id: number;
  source: string;
  source_url: string;
  version: string;
  extracted_at: string | null;
  import_id: number;
  imported_at: string | null;
  indice_code: string;
  indice: string;
  unit: string;
}

export interface Observation {
  date: string;
  value: number;
  provenance: ObservationProvenance;
}

export interface ObservationsResponse {
  // null si la période est vide ou comporte plusieurs provenances.
  source: string | null;
  indice: string | null;
  unit: string | null;
  version: string | null;
  extracted_at: string | null;
  observations: Observation[];
}

const API_URL = import.meta.env.VITE_API_URL;

export async function fetchObservations(
  start: string,
  end: string
): Promise<ObservationsResponse> {
  const response = await fetch(`${API_URL}/observations?start=${start}&end=${end}`);

  if (!response.ok) {
    throw new Error(`Erreur API: ${response.status}`);
  }

  return response.json() as Promise<ObservationsResponse>;
}

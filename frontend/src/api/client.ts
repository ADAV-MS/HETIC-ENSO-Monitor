export interface Observation {
  date: string;
  value: number;
}

export interface ObservationsResponse {
  source: string;
  indice: string;
  unit: string;
  version: string;
  extracted_at: string;
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
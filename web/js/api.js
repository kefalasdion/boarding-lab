export class SimulationRequestError extends Error {
  constructor(message, {status = 0, code = 'network_error', issues = []} = {}) {
    super(message);
    this.name = 'SimulationRequestError';
    this.status = status;
    this.code = code;
    this.issues = issues;
  }
}

export async function requestJson(path, payload, {signal} = {}) {
  let response;
  try {
    response = await fetch(path, {
      method: payload === undefined ? 'GET' : 'POST',
      headers: payload === undefined ? {} : {'Content-Type': 'application/json'},
      body: payload === undefined ? undefined : JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new SimulationRequestError('The simulator could not be reached. Please try again.');
  }

  let data;
  try {
    data = await response.json();
  } catch {
    throw new SimulationRequestError('The simulator returned an unreadable response.', {
      status: response.status,
      code: 'invalid_response',
    });
  }
  if (!response.ok) {
    const issues = Array.isArray(data.issues) ? data.issues : [];
    const detail = issues.map((issue) => `${issue.path}: ${issue.message}`).join(' · ');
    throw new SimulationRequestError(
      detail || data.message || 'The simulation request failed.',
      {status: response.status, code: data.error || 'request_failed', issues},
    );
  }
  return data;
}

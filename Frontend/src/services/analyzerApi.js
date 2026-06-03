const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

/**
 * @param {string} gitUrl  - public GitHub / Git repo URL
 * @returns {Promise<import('../types').RepoAnalysisResult>}
 */
export async function analyzeRepo(gitUrl) {
  const response = await fetch(`${BASE_URL}/api/v1/analyze/repo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ git_url: gitUrl }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(err.detail ?? 'Analysis failed')
  }

  return response.json()
}

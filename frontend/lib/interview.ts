const getBackendUrl = () => {
  if (process.env.BACKEND_URL) return process.env.BACKEND_URL
  if (process.env.NEXT_PUBLIC_API) return process.env.NEXT_PUBLIC_API.replace(/\/api\/v1$/, '')
  return 'http://localhost:8000'
}

export async function fetchInterview(id: string) {
  try {
    const base = getBackendUrl()
    const res = await fetch(`${base}/api/v1/interviews/${id}`, {
      next: { revalidate: 30 },
      cache: 'no-store',
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

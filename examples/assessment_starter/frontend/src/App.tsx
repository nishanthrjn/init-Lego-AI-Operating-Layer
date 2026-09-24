import { useState } from 'react'
import type { FormEvent } from 'react'

export default function App() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!question.trim() || loading) return
    setLoading(true)
    setAnswer('')
    setError('')
    try {
      const response = await fetch('/api/v1/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal: AbortSignal.timeout(15000),
      })
      if (!response.ok) throw new Error(
        response.status === 422 ? 'Enter a question of at most 4,000 characters.' : 'Could not get an answer. Please try again.',
      )
      const data: unknown = await response.json()
      if (!data || typeof data !== 'object' || !('answer' in data) || typeof data.answer !== 'string') {
        throw new Error('The server returned an invalid response.')
      }
      setAnswer(data.answer)
    } catch (cause) {
      setError(cause instanceof Error && cause.name !== 'TimeoutError' ? cause.message : 'Request timed out. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <p className="eyebrow">ASSESSMENT STARTER</p>
      <h1>Ask a question</h1>
      <p>A small application with a deterministic offline answer.</p>
      <form onSubmit={submit}>
        <label htmlFor="question">Your question</label>
        <textarea id="question" value={question} maxLength={4000} rows={5}
          onChange={(event) => setQuestion(event.target.value)} disabled={loading} required />
        <button disabled={loading || !question.trim()}>{loading ? 'Answering…' : 'Ask question'}</button>
      </form>
      {error && <p role="alert" className="error">{error}</p>}
      <section aria-live="polite" aria-busy={loading}>
        {loading && <p>Preparing your answer…</p>}
        {answer && <><h2>Answer</h2><p className="answer">{answer}</p></>}
      </section>
    </main>
  )
}

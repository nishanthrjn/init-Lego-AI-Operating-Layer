import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

async function submit() {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Your question'), 'Why use ports?')
  await user.click(screen.getByRole('button', { name: 'Ask question' }))
  return user
}

describe('question form', () => {
  it('rejects empty and whitespace-only questions without calling the API', async () => {
    render(<App />)
    const question = screen.getByLabelText('Your question')
    expect(screen.getByRole('button', { name: 'Ask question' })).toBeDisabled()
    await userEvent.setup().type(question, '   ')
    expect(screen.getByRole('button', { name: 'Ask question' })).toBeDisabled()
    fireEvent.submit(question.closest('form')!)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('sends the question and blocks duplicate submissions until the answer arrives', async () => {
    let resolve!: (response: Response) => void
    vi.mocked(fetch).mockReturnValue(new Promise<Response>((done) => { resolve = done }))
    render(<App />)
    await submit()
    const question = screen.getByLabelText('Your question')
    expect(question).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Answering…' })).toBeDisabled()
    expect(screen.getByText('Preparing your answer…')).toBeInTheDocument()
    fireEvent.submit(question.closest('form')!)
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch).toHaveBeenCalledWith('/api/v1/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: 'Why use ports?' }),
      signal: expect.any(AbortSignal),
    })
    await act(async () => { resolve(new Response(JSON.stringify({ answer: 'Replaceable providers.' }))) })
    expect(await screen.findByText('Replaceable providers.')).toBeInTheDocument()
    expect(question).toBeEnabled()
    expect(screen.queryByText('Preparing your answer…')).not.toBeInTheDocument()
  })

  it.each([
    [422, 'Enter a question of at most 4,000 characters.'],
    [500, 'Could not get an answer. Please try again.'],
  ])('shows an actionable error for HTTP %s', async (status, message) => {
    vi.mocked(fetch).mockResolvedValue(new Response('private provider detail', { status }))
    render(<App />)
    await submit()
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(screen.queryByText('private provider detail')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ask question' })).toBeEnabled()
  })

  it.each([null, {}, { answer: 42 }])('rejects malformed response data %j', async (data) => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(data)))
    render(<App />)
    await submit()
    expect(await screen.findByRole('alert')).toHaveTextContent('The server returned an invalid response.')
  })

  it('shows a network error and allows a successful retry', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ answer: 'Recovered' })))
    render(<App />)
    const user = await submit()
    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to fetch')
    await user.click(screen.getByRole('button', { name: 'Ask question' }))
    expect(await screen.findByText('Recovered')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('handles the configured timeout without waiting in real time', async () => {
    const controller = new AbortController()
    const timeout = vi.spyOn(AbortSignal, 'timeout').mockReturnValue(controller.signal)
    vi.mocked(fetch).mockImplementation((_url, options) => new Promise((_resolve, reject) => {
      options!.signal!.addEventListener('abort', () => reject(options!.signal!.reason), { once: true })
    }))
    render(<App />)
    await submit()
    expect(timeout).toHaveBeenCalledWith(15000)
    await act(async () => { controller.abort(new DOMException('Expired', 'TimeoutError')) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Request timed out. Please try again.')
    expect(screen.getByRole('button', { name: 'Ask question' })).toBeEnabled()
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TelegramPost from './TelegramPost'
import api from './services/api'

vi.mock('./services/api', () => ({
  default: { getReplies: vi.fn() }
}))

describe('TelegramPost', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders channel link and post link with correct hrefs', () => {
    render(<TelegramPost channel="dubai_flea" messageId={42} />)
    expect(screen.getByRole('link', { name: /dubai_flea/ })).toHaveAttribute(
      'href',
      'https://t.me/dubai_flea'
    )
    expect(screen.getByRole('link', { name: /Открыть в Telegram/ })).toHaveAttribute(
      'href',
      'https://t.me/dubai_flea/42'
    )
  })

  it('renders classification lines with joined subcategories', () => {
    render(
      <TelegramPost
        channel="c"
        messageId={1}
        classifications={{ Электроника: ['Телефоны', 'Ноутбуки'], Мебель: [] }}
      />
    )
    expect(screen.getByText('Электроника:')).toBeInTheDocument()
    expect(screen.getByText('Телефоны, Ноутбуки')).toBeInTheDocument()
    expect(screen.getByText('Мебель:')).toBeInTheDocument()
  })

  it('renders no category section without classifications', () => {
    const { container } = render(<TelegramPost channel="c" messageId={1} classifications={{}} />)
    expect(container.querySelector('.post-categories-section')).toBeNull()
  })

  it('injects telegram widget script with data-telegram-post', () => {
    const { container } = render(<TelegramPost channel="dubai_flea" messageId={42} />)
    const script = container.querySelector('.telegram-post-container script')
    expect(script).not.toBeNull()
    expect(script).toHaveAttribute('data-telegram-post', 'dubai_flea/42')
    expect(script.getAttribute('src')).toContain('telegram.org/js/telegram-widget.js')
  })

  it('shows no replies button when hasReplies=false', () => {
    render(<TelegramPost channel="c" messageId={1} hasReplies={false} />)
    expect(screen.queryByRole('button', { name: /Ответы/ })).not.toBeInTheDocument()
  })

  it('fetches and shows replies on click, toggles them off, and does not refetch', async () => {
    const user = userEvent.setup()
    api.getReplies.mockResolvedValue([
      { message_id: 10, text: 'Ещё продаётся?', posted_at: '2024-05-01T10:00:00', tg_link: 'https://t.me/c/10' }
    ])
    render(<TelegramPost channel="c" messageId={5} hasReplies />)

    await user.click(screen.getByRole('button', { name: /Ответы/ }))
    expect(api.getReplies).toHaveBeenCalledWith('c', 5)
    expect(await screen.findByText('Ещё продаётся?')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Открыть в Telegram →/ })).toHaveAttribute(
      'href',
      'https://t.me/c/10'
    )

    await user.click(screen.getByRole('button', { name: /Ответы/ }))
    expect(screen.queryByText('Ещё продаётся?')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Ответы/ }))
    expect(await screen.findByText('Ещё продаётся?')).toBeInTheDocument()
    expect(api.getReplies).toHaveBeenCalledTimes(1)
  })

  it('swallows getReplies errors and shows no replies', async () => {
    const user = userEvent.setup()
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    api.getReplies.mockRejectedValue(new Error('boom'))
    render(<TelegramPost channel="c" messageId={5} hasReplies />)

    await user.click(screen.getByRole('button', { name: /Ответы/ }))
    await waitFor(() => expect(spy).toHaveBeenCalled())
    expect(document.querySelector('.replies-list')).toBeNull()
    expect(screen.getByRole('button', { name: /Ответы/ })).toBeEnabled()
    spy.mockRestore()
  })
})

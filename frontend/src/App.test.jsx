import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import api from './services/api'

vi.mock('./services/api', () => ({
  default: {
    getItems: vi.fn(),
    getCategories: vi.fn(),
    getChannels: vi.fn(),
    getReplies: vi.fn(),
    getBotConfig: vi.fn(() => ({ username: 'testbot' }))
  }
}))

vi.mock('./AdBlock', () => ({ default: () => null }))
vi.mock('./TelegramPost', () => ({
  default: ({ channel, messageId }) => (
    <div data-testid="post">{`${channel}/${messageId}`}</div>
  )
}))

const items = [
  { channel_name: 'chan_a', message_id: 1, classifications: {}, is_has_replies: false },
  { channel_name: 'chan_a', message_id: 2, classifications: {}, is_has_replies: false },
  { channel_name: 'chan_b', message_id: 3, classifications: {}, is_has_replies: true }
]

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getBotConfig.mockReturnValue({ username: 'testbot' })
    api.getCategories.mockResolvedValue({ Электроника: ['Телефоны'], Мебель: ['Диваны'] })
    api.getChannels.mockResolvedValue([{ name: 'chan_a' }, { name: 'chan_b' }])
    api.getItems.mockResolvedValue({ items, total_pages: 1 })
  })

  it('renders one post per item and the bot link', async () => {
    render(<App />)
    const posts = await screen.findAllByTestId('post')
    expect(posts.map((p) => p.textContent)).toEqual(['chan_a/1', 'chan_a/2', 'chan_b/3'])
    expect(screen.getByRole('link', { name: /Подписаться на уведомления/ })).toHaveAttribute(
      'href',
      'https://t.me/testbot'
    )
    expect(api.getItems).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, page_size: 21, channel: 'all' })
    )
  })

  it('shows the error state when fetching fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    api.getItems.mockRejectedValue(new Error('HTTP error! status: 500'))
    render(<App />)
    expect(await screen.findByText(/HTTP error! status: 500/)).toBeInTheDocument()
    expect(screen.getByText('Ошибка:')).toBeInTheDocument()
    expect(screen.queryByText('Ничего не найдено')).not.toBeInTheDocument()
    expect(screen.queryAllByTestId('post')).toHaveLength(0)
  })

  it('shows the empty state when there are no items', async () => {
    api.getItems.mockResolvedValue({ items: [], total_pages: 0 })
    render(<App />)
    expect(await screen.findByText('Ничего не найдено')).toBeInTheDocument()
    expect(screen.getByText('Попробуйте изменить параметры поиска')).toBeInTheDocument()
  })

  it('category change resets subcategory and refetches with new params', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findAllByTestId('post')
    const category = screen.getByLabelText(/Категория/)
    const subcategory = screen.getByLabelText(/Подкатегория/)
    expect(subcategory).toBeDisabled()

    await screen.findByRole('option', { name: 'Электроника' })
    await user.selectOptions(category, 'Электроника')
    await screen.findByRole('option', { name: 'Телефоны' })
    await user.selectOptions(subcategory, 'Телефоны')
    await waitFor(() =>
      expect(api.getItems).toHaveBeenLastCalledWith(
        expect.objectContaining({ category: 'Электроника', subcategory: 'Телефоны' })
      )
    )

    await user.selectOptions(category, 'Мебель')
    await waitFor(() =>
      expect(api.getItems).toHaveBeenLastCalledWith(
        expect.objectContaining({ category: 'Мебель', subcategory: '', page: 1 })
      )
    )
    expect(subcategory).toHaveValue('')
  })

  it('reset button restores default filters and refetches', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findAllByTestId('post')
    await screen.findByRole('option', { name: 'Мебель' })
    await user.selectOptions(screen.getByLabelText(/Категория/), 'Мебель')
    await waitFor(() =>
      expect(api.getItems).toHaveBeenLastCalledWith(expect.objectContaining({ category: 'Мебель' }))
    )
    await user.click(screen.getByRole('button', { name: /Сбросить/ }))
    await waitFor(() =>
      expect(api.getItems).toHaveBeenLastCalledWith(
        expect.objectContaining({ category: '', channel: 'all', search: '' })
      )
    )
  })
})

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import api from './api'

const okResponse = (body) => ({ ok: true, status: 200, json: async () => body })
const errResponse = (status) => ({ ok: false, status, json: async () => ({}) })

describe('api service', () => {
  let fetchMock

  beforeEach(() => {
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  describe('getItems', () => {
    it('drops null/undefined/empty params but keeps 0 and channel=all', async () => {
      fetchMock.mockResolvedValue(okResponse({ items: [] }))
      await api.getItems({
        page: 0,
        page_size: 21,
        channel: 'all',
        search: '',
        category: null,
        subcategory: undefined,
        date_from: '2024-01-01'
      })
      const url = fetchMock.mock.calls[0][0]
      expect(url.startsWith('/api/items?')).toBe(true)
      const qs = new URLSearchParams(url.split('?')[1])
      expect(Object.fromEntries(qs)).toEqual({
        page: '0',
        page_size: '21',
        channel: 'all',
        date_from: '2024-01-01'
      })
    })

    it('url-encodes values', async () => {
      fetchMock.mockResolvedValue(okResponse({}))
      await api.getItems({ search: 'a&b c' })
      expect(fetchMock.mock.calls[0][0]).toBe('/api/items?search=a%26b+c')
    })

    it('returns parsed JSON body', async () => {
      const body = { items: [{ message_id: 1 }], total_pages: 1 }
      fetchMock.mockResolvedValue(okResponse(body))
      await expect(api.getItems({})).resolves.toEqual(body)
    })

    it('throws on non-ok response', async () => {
      fetchMock.mockResolvedValue(errResponse(500))
      await expect(api.getItems({})).rejects.toThrow('HTTP error! status: 500')
    })
  })

  describe('getItemById', () => {
    it('requests /api/<channel>/<id>', async () => {
      fetchMock.mockResolvedValue(okResponse({ message_id: 7 }))
      await expect(api.getItemById('chan', 7)).resolves.toEqual({ message_id: 7 })
      expect(fetchMock).toHaveBeenCalledWith('/api/chan/7')
    })

    it('404 -> Item not found', async () => {
      fetchMock.mockResolvedValue(errResponse(404))
      await expect(api.getItemById('chan', 1)).rejects.toThrow('Item not found')
    })

    it('other errors -> HTTP error message', async () => {
      fetchMock.mockResolvedValue(errResponse(503))
      await expect(api.getItemById('chan', 1)).rejects.toThrow('HTTP error! status: 503')
    })
  })

  describe('getReplies', () => {
    it('requests /api/<channel>/<id>/replies', async () => {
      fetchMock.mockResolvedValue(okResponse([]))
      await api.getReplies('chan', 3)
      expect(fetchMock).toHaveBeenCalledWith('/api/chan/3/replies')
    })

    it('404 -> Message not found', async () => {
      fetchMock.mockResolvedValue(errResponse(404))
      await expect(api.getReplies('chan', 3)).rejects.toThrow('Message not found')
    })

    it('other errors -> HTTP error message', async () => {
      fetchMock.mockResolvedValue(errResponse(500))
      await expect(api.getReplies('chan', 3)).rejects.toThrow('HTTP error! status: 500')
    })
  })

  describe('channels / categories / replies count', () => {
    it.each([
      ['getChannels', [], '/api/channels'],
      ['getCategories', [], '/api/categories'],
      ['getRepliesCount', ['chan', 9], '/api/chan/9/replies/count']
    ])('%s hits the right URL and throws on 500', async (method, args, url) => {
      fetchMock.mockResolvedValueOnce(okResponse({ ok: 1 }))
      await expect(api[method](...args)).resolves.toEqual({ ok: 1 })
      expect(fetchMock).toHaveBeenCalledWith(url)

      fetchMock.mockResolvedValueOnce(errResponse(500))
      await expect(api[method](...args)).rejects.toThrow('HTTP error! status: 500')
    })
  })

  describe('getBotConfig', () => {
    it('defaults to baraholichbot', () => {
      vi.stubEnv('VITE_BOT_USERNAME', '')
      expect(api.getBotConfig()).toEqual({ username: 'baraholichbot' })
    })

    it('honours VITE_BOT_USERNAME', () => {
      vi.stubEnv('VITE_BOT_USERNAME', 'custombot')
      expect(api.getBotConfig()).toEqual({ username: 'custombot' })
    })
  })
})

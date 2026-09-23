import { useState, useEffect, useCallback, useRef } from 'react'
import TelegramPost from './TelegramPost'
import AdBlock from './AdBlock'
import api from './services/api'

function App() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [categories, setCategories] = useState({})
  const [channels, setChannels] = useState([])
  const [filters, setFilters] = useState({
    search: '',
    category: '',
    subcategory: '',
    dateFrom: '',
    dateTo: '',
    channel: 'all'
  })

  const sentinelRef = useRef(null)
  const pageSize = 21
  const botConfig = api.getBotConfig()

  // Load categories and channels on mount
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [categoriesData, channelsData] = await Promise.all([
          api.getCategories(),
          api.getChannels()
        ])
        setCategories(categoriesData)
        setChannels(channelsData)
      } catch (err) {
        console.error('Error loading initial data:', err)
      }
    }
    loadInitialData()
  }, [])

  const fetchItems = useCallback(async (resetItems = false) => {
    try {
      if (resetItems) {
        setLoading(true)
      } else {
        setLoadingMore(true)
      }
      setError(null)

      const currentPage = resetItems ? 1 : page + 1

      const params = {
        page: currentPage,
        page_size: pageSize,
        channel: filters.channel,
        search: filters.search,
        category: filters.category,
        subcategory: filters.subcategory,
        date_from: filters.dateFrom,
        date_to: filters.dateTo
      }

      const data = await api.getItems(params)

      if (resetItems) {
        setItems(data.items)
        setPage(1)
      } else {
        setItems(prev => [...prev, ...data.items])
        setPage(currentPage)
      }

      setTotalPages(data.total_pages)
      setHasMore(currentPage < data.total_pages)
    } catch (err) {
      setError(err.message)
      console.error('Error fetching items:', err)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [page, pageSize, filters])

  // Fetch items when filters change (reset)
  useEffect(() => {
    setItems([])
    setPage(1)
    setHasMore(true)
    fetchItems(true)
  }, [filters])

  const loadMore = useCallback(() => {
    if (!loadingMore && hasMore) {
      fetchItems(false)
    }
  }, [loadingMore, hasMore, fetchItems])

  // Intersection Observer для автоматической подгрузки при скролле
  useEffect(() => {
    if (!sentinelRef.current) return

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (entry.isIntersecting && hasMore && !loadingMore && !loading) {
          console.log('🔄 Загрузка следующей страницы...')
          loadMore()
        }
      },
      {
        root: null,
        rootMargin: '200px',
        threshold: 0
      }
    )

    observer.observe(sentinelRef.current)

    return () => observer.disconnect()
  }, [hasMore, loadingMore, loading, loadMore])

  const handleFilterChange = (key, value) => {
    setFilters(prev => {
      const newFilters = { ...prev, [key]: value }
      // Reset subcategory when category changes
      if (key === 'category') {
        newFilters.subcategory = ''
      }
      return newFilters
    })
    setPage(1)
  }

  const availableSubcategories = filters.category
    ? (categories[filters.category] || [])
    : []

  const handleResetFilters = () => {
    setFilters({
      search: '',
      category: '',
      subcategory: '',
      dateFrom: '',
      dateTo: '',
      channel: 'all'
    })
  }

  const currentChannel = channels.find(ch => ch.name === filters.channel)
  const pageTitle = filters.channel === 'all'
    ? 'Барахолка Дубая'
    : (currentChannel?.name || 'Барахолка')
  const pageDescription = filters.channel === 'all'
    ? 'объявления из всех Telegram каналов Дубая'
    : `Объявления из канала ${currentChannel?.name || ''}`

  return (
    <>
      <header className="header">
        <div className="container">
          <div className="header-content">
            <div>
              <h1>🛍️ {pageTitle}</h1>
              <p>{pageDescription}</p>
            </div>
            <a
              href={`https://t.me/${botConfig.username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="subscribe-btn"
            >
              🔔 Подписаться на уведомления
            </a>
          </div>
        </div>
      </header>

      <div className="container">
        <div className="filters">
          <div className="filters-header">
            <div className="filters-title">
              🔍 Фильтры поиска
            </div>
            <button className="filters-reset" onClick={handleResetFilters}>
              ✕ Сбросить
            </button>
          </div>
          <div className="filter-row">
            <div className="filter-group">
              <label htmlFor="channel">📡 Канал</label>
              <select
                id="channel"
                value={filters.channel}
                onChange={(e) => handleFilterChange('channel', e.target.value)}
              >
                <option value="all">Все каналы</option>
                {channels.map((channel) => (
                  <option key={channel.name} value={channel.name}>
                    {channel.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label htmlFor="search">🔎 Поиск</label>
              <input
                id="search"
                type="text"
                placeholder="Поиск по тексту..."
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
              />
            </div>
          </div>

          <div className="filter-row">
            <div className="filter-group">
              <label htmlFor="category">📁 Категория</label>
              <select
                id="category"
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.target.value)}
              >
                <option value="">Все категории</option>
                {Object.keys(categories).map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label htmlFor="subcategory">📂 Подкатегория</label>
              <select
                id="subcategory"
                value={filters.subcategory}
                onChange={(e) => handleFilterChange('subcategory', e.target.value)}
                disabled={!filters.category}
              >
                <option value="">Все подкатегории</option>
                {availableSubcategories.map((subcategory) => (
                  <option key={subcategory} value={subcategory}>
                    {subcategory}
                  </option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label htmlFor="dateFrom">📅 С даты</label>
              <input
                id="dateFrom"
                type="date"
                value={filters.dateFrom}
                onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
              />
            </div>

            <div className="filter-group">
              <label htmlFor="dateTo">📅 По дату</label>
              <input
                id="dateTo"
                type="date"
                value={filters.dateTo}
                onChange={(e) => handleFilterChange('dateTo', e.target.value)}
              />
            </div>
          </div>
        </div>

        {loading && <div className="loading">Загрузка...</div>}

        {error && (
          <div className="error">
            <strong>Ошибка:</strong> {error}
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="no-results">
            <h3>Ничего не найдено</h3>
            <p>Попробуйте изменить параметры поиска</p>
          </div>
        )}

        {!loading && items.length > 0 && (
          <div className="content-with-sidebar">
            {/* Левый sidebar с рекламой */}
            <aside className="sidebar sidebar-left">
              <div className="sidebar-ad-sticky">
                <AdBlock slot="sidebar-left" format="vertical" />
              </div>
            </aside>

            {/* Основной контент */}
            <div className="main-content">
              <div className="items-grid">
                {items.map((item, index) => {
                  // Каждый 6-й элемент - реклама (начиная с 5-го индекса: 5, 11, 17...)
                  const shouldShowAd = (index + 1) % 6 === 0;

                  return (
                    <>
                      <TelegramPost
                        key={`${item.channel_name}-${item.message_id}`}
                        channel={item.channel_name}
                        messageId={item.message_id}
                        classifications={item.classifications}
                        hasReplies={item.is_has_replies}
                      />
                      {shouldShowAd && (
                        <div key={`ad-${index}`} className="inline-ad-item">
                          <AdBlock slot={`inline-ad-${Math.floor(index / 6)}`} />
                        </div>
                      )}
                    </>
                  );
                })}
              </div>

              {/* Sentinel для бесконечного скролла */}
              <div ref={sentinelRef} style={{
                height: '100px',
                margin: '40px 0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                {loadingMore && (
                  <div className="loading">Загрузка...</div>
                )}
                {!hasMore && (
                  <div style={{ color: '#999', fontSize: '14px' }}>
                    ✓ Все посты загружены
                  </div>
                )}
              </div>
            </div>

            {/* Правый sidebar с рекламой */}
            <aside className="sidebar sidebar-right">
              <div className="sidebar-ad-sticky">
                <AdBlock slot="sidebar-right" format="vertical" />
              </div>
            </aside>
          </div>
        )}
      </div>
    </>
  )
}

export default App

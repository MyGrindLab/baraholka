import { useEffect, useRef, useState } from 'react'
import api from './services/api'

function TelegramPost({ channel, messageId, classifications, hasReplies = false }) {
  const containerRef = useRef(null)
  const widgetLoadedRef = useRef(false)
  const [replies, setReplies] = useState([])
  const [showReplies, setShowReplies] = useState(false)
  const [loadingReplies, setLoadingReplies] = useState(false)

  // Загрузка виджета Telegram
  useEffect(() => {
    if (!containerRef.current || widgetLoadedRef.current) return

    widgetLoadedRef.current = true
    containerRef.current.innerHTML = ''

    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    script.setAttribute('data-telegram-post', `${channel}/${messageId}`)
    script.setAttribute('data-width', '100%')

    containerRef.current.appendChild(script)
  }, [channel, messageId])

  const handleToggleReplies = async () => {
    if (showReplies) {
      setShowReplies(false)
      return
    }

    if (replies.length === 0) {
      setLoadingReplies(true)
      try {
        const data = await api.getReplies(channel, messageId)
        setReplies(data)
        setShowReplies(true)
      } catch (err) {
        console.error('Error fetching replies:', err)
      } finally {
        setLoadingReplies(false)
      }
    } else {
      setShowReplies(true)
    }
  }

  const telegramLink = `https://t.me/${channel}/${messageId}`

  const formatDate = (dateString) => {
    if (!dateString) return null
    // Ensure the date is treated as UTC
    const utcDate = dateString.endsWith('Z') ? dateString : dateString + 'Z'
    const date = new Date(utcDate)
    const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
    return new Intl.DateTimeFormat('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: userTimeZone
    }).format(date)
  }

  const channelLink = `https://t.me/${channel}`

  return (
    <div className="telegram-post-wrapper">
      {/* Название канала */}
      <div className="post-section post-channel-section">
        <a
          href={channelLink}
          target="_blank"
          rel="noopener noreferrer"
          className="channel-name"
        >
          📡 {channel}
        </a>
      </div>

      {/* Разделитель */}
      <div className="post-divider"></div>

      {/* Категории и подкатегории */}
      {classifications && Object.keys(classifications).length > 0 && (
        <>
          <div className="post-section post-categories-section">
            {Object.entries(classifications).map(([category, subcategories]) => (
              <div key={category} className="category-line">
                <span className="category-name">{category}:</span>
                {subcategories && subcategories.length > 0 && (
                  <span className="subcategories-text">
                    {subcategories.join(', ')}
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Разделитель */}
          <div className="post-divider"></div>
        </>
      )}

      {/* Контент сообщения */}
      <div ref={containerRef} className="telegram-post-container"></div>

      {/* Разделитель перед ответами */}
      {hasReplies && <div className="post-divider"></div>}

      {/* Ответы */}
      {hasReplies && (
        <div className="post-section">
          <button
            className="replies-toggle"
            onClick={handleToggleReplies}
            disabled={loadingReplies}
          >
            💬 Ответы
            {loadingReplies ? ' ...' : (showReplies ? ' ▼' : ' ▶')}
          </button>

          {showReplies && replies.length > 0 && (
            <div className="replies-list">
              {replies.map((reply) => (
                <div key={reply.message_id} className="reply-item">
                  <div className="reply-meta">
                    📅 {formatDate(reply.posted_at)}
                  </div>
                  {reply.text && (
                    <div className="reply-text">{reply.text}</div>
                  )}
                  <a
                    href={reply.tg_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="reply-link"
                  >
                    Открыть в Telegram →
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="post-footer">
        <a
          href={telegramLink}
          target="_blank"
          rel="noopener noreferrer"
          className="telegram-link-btn"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
          </svg>
          Открыть в Telegram
        </a>
      </div>
    </div>
  )
}

export default TelegramPost

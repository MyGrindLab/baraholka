const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

class ApiService {
  /**
   * Get paginated items with filters
   * @param {Object} params - Query parameters
   * @param {number} params.page - Page number
   * @param {number} params.page_size - Items per page
   * @param {string} params.channel - Channel name
   * @param {string} [params.search] - Search text
   * @param {string} [params.category] - Category filter
   * @param {string} [params.subcategory] - Subcategory filter
   * @param {string} [params.date_from] - Start date filter
   * @param {string} [params.date_to] - End date filter
   * @returns {Promise<Object>} Paginated response with items
   */
  async getItems(params) {
    const queryParams = new URLSearchParams()

    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        queryParams.append(key, value.toString())
      }
    })

    const response = await fetch(`${API_BASE_URL}/items?${queryParams}`)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  /**
   * Get a specific item by channel and message ID
   * @param {string} channel - Channel name
   * @param {number} messageId - Message ID
   * @returns {Promise<Object>} Item object
   */
  async getItemById(channel, messageId) {
    const response = await fetch(`${API_BASE_URL}/${channel}/${messageId}`)

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Item not found')
      }
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  /**
   * Get list of available channels
   * @returns {Promise<Array>} Array of channel objects
   */
  async getChannels() {
    const response = await fetch(`${API_BASE_URL}/channels`)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  /**
   * Get categories with subcategories
   * @returns {Promise<Object>} Categories object
   */
  async getCategories() {
    const response = await fetch(`${API_BASE_URL}/categories`)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  /**
   * Get replies for a specific message
   * @param {string} channel - Channel name
   * @param {number} messageId - Message ID
   * @returns {Promise<Array>} Array of reply messages
   */
  async getReplies(channel, messageId) {
    const response = await fetch(`${API_BASE_URL}/${channel}/${messageId}/replies`)

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Message not found')
      }
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  /**
   * Get reply count for a specific message
   * @param {string} channel - Channel name
   * @param {number} messageId - Message ID
   * @returns {Promise<Object>} Object with message_id and replies_count
   */
  async getRepliesCount(channel, messageId) {
    const response = await fetch(`${API_BASE_URL}/${channel}/${messageId}/replies/count`)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  /**
   * Get bot configuration
   * @returns {Object} Bot configuration
   */
  getBotConfig() {
    return {
      username: import.meta.env.VITE_BOT_USERNAME || 'baraholichbot'
    }
  }
}

export default new ApiService()

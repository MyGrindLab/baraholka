import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
})

// jsdom has no IntersectionObserver; App uses it for infinite scroll.
if (typeof globalThis.IntersectionObserver === 'undefined') {
  class IntersectionObserverStub {
    constructor(callback, options = {}) {
      this.callback = callback
      this.root = options.root ?? null
      this.rootMargin = options.rootMargin ?? '0px'
      this.thresholds = [].concat(options.threshold ?? 0)
    }
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return []
    }
  }
  globalThis.IntersectionObserver = IntersectionObserverStub
}

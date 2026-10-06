// The latest product search the shopping assistant asked the page to show.
// ChatPanel sets it; ChatResults (rendered at the top of the page) displays it.
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import type { PageSearchResults } from './api'

interface ChatResultsState {
  results: PageSearchResults | null
  // Bumped on every new search so the page can scroll to it even if the results look the same.
  version: number
  show: (r: PageSearchResults) => void
  clear: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<PageSearchResults | null>(null)
  const [version, setVersion] = useState(0)
  const show = useCallback((r: PageSearchResults) => {
    setResults(r)
    setVersion((v) => v + 1)
  }, [])
  const clear = useCallback(() => setResults(null), [])
  return <ChatResultsContext.Provider value={{ results, version, show, clear }}>{children}</ChatResultsContext.Provider>
}

export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}

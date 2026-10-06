import { Fragment, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { formatPrice, type PageSearchResults } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import { OPEN_CHAT_EVENT } from '../openChat'

interface ChatProduct {
  product_id: string
  name: string
  price: number
  image_url: string
  url: string
  total_stock: number
}

interface BrowseRequest {
  query: string
  category: string | null
  max_price: number | null
  sort: PageSearchResults['sort']
  size_in_stock?: string | null
  title: string
}

interface HistoryMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: string
  products: ChatProduct[]
  page_search: BrowseRequest | null
}

interface ChatOption {
  product_id: string
  name: string
  price: number
  image_url: string
  sizes_in_stock: string[]
}

interface Message {
  role: 'user' | 'assistant' | 'error'
  text: string
  options?: ChatOption[] // tappable answers to a "which one did you mean?" question
  retryText?: string // on errors: the question to send again
  products?: ChatProduct[]
  // Live results (total known) or a saved browse request from history (can be shown again).
  pageResults?: { title: string; total?: number; browse?: BrowseRequest }
}

const MAX_LEN = 1000
const REQUEST_TIMEOUT_MS = 90_000
const SLOW_AFTER_MS = 8_000

class ChatError extends Error {}

// Turn a failed request into a message a shopper can act on.
function friendlyError(status: number | null, detail: string | undefined, timedOut: boolean): string {
  if (timedOut) return 'This is taking much longer than usual, so I stopped waiting.'
  if (status === null) return "I couldn't reach the shop's server. Check your internet connection."
  if (status === 429) return detail ?? "You're sending messages quickly. Wait a few seconds."
  if (status === 503) return detail ?? "The assistant isn't available right now."
  if (status >= 500) return detail ?? "The assistant ran into a problem answering that."
  return detail ?? 'Something went wrong with that message.'
}

// Replies are plain text; older saved replies use **bold**. Render just that, safely (React escapes the rest).
function formatText(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>,
  )
}

function fromHistory(m: HistoryMessage): Message {
  return {
    role: m.role,
    text: m.content,
    products: m.products,
    pageResults: m.page_search ? { title: m.page_search.title, browse: m.page_search } : undefined,
  }
}

export default function ChatPanel() {
  const { user } = useAuth()
  const chatResults = useChatResults()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [historyState, setHistoryState] = useState<'none' | 'loading' | 'loaded' | 'error'>('none')
  const [historyCount, setHistoryCount] = useState(0) // saved messages shown above the greeting
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [slow, setSlow] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const onProductPage = /^\/products\/[^/]+$/.test(location.pathname)

  // A different person logged in (or out): drop what's on screen, then load
  // that customer's own saved history (the server decides whose, from the login cookie).
  const userId = user?.id ?? null
  useEffect(() => {
    setMessages([])
    setHistoryCount(0)
    setConversationId(null)
    if (userId === null) {
      setHistoryState('none')
      return
    }
    const ctrl = new AbortController()
    setHistoryState('loading')
    fetch('/api/chat/history', { credentials: 'same-origin', signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data: { messages: HistoryMessage[] }) => {
        // Keep anything typed while loading after the saved history.
        setMessages((current) => [...data.messages.map(fromHistory), ...current])
        setHistoryCount(data.messages.length)
        setHistoryState('loaded')
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setHistoryState('error')
      })
    return () => ctrl.abort()
  }, [userId])

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight })
  }, [messages, sending, open])

  // Other parts of the page can open the chat (see openChat.ts), optionally with a question filled in.
  useEffect(() => {
    const onOpen = (e: Event) => {
      const prefill = (e as CustomEvent<{ prefill?: string }>).detail?.prefill
      setOpen(true)
      if (prefill) setDraft(prefill)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
    window.addEventListener(OPEN_CHAT_EVENT, onOpen)
    return () => window.removeEventListener(OPEN_CHAT_EVENT, onOpen)
  }, [])

  useEffect(() => {
    if (open) inputRef.current?.focus()
    // On wide screens the page makes room for the open panel (see .chat-open in index.css),
    // so results shown on the page aren't hidden behind it.
    document.body.classList.toggle('chat-open', open)
  }, [open])

  function send(e: FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text || sending) return
    setDraft('')
    setMessages((m) => [...m, { role: 'user', text }])
    void ask(text)
  }

  // Tapping one of the assistant's suggested products answers its question.
  function choose(option: ChatOption) {
    if (sending) return
    const text = `I mean the ${option.name}.`
    setMessages((m) => [...m, { role: 'user', text }])
    void ask(text)
  }

  // Send the same question again after an error, without repeating the customer's bubble.
  function retry(index: number, text: string) {
    if (sending) return
    setMessages((m) => m.filter((_, i) => i !== index))
    void ask(text)
  }

  async function ask(text: string) {
    setSending(true)
    setSlow(false)
    const slowTimer = setTimeout(() => setSlow(true), SLOW_AFTER_MS)
    const ctrl = new AbortController()
    const timeout = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS)
    try {
      let res: Response
      try {
        res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          signal: ctrl.signal,
          body: JSON.stringify({
            message: text,
            conversation_id: conversationId,
            // Where the customer is, so "this" can mean the product that's open.
            page: { path: location.pathname + location.search },
          }),
        })
      } catch {
        throw new ChatError(friendlyError(null, undefined, ctrl.signal.aborted))
      }
      const data = await res.json().catch(() => null)
      // A 5xx with no JSON body comes from the dev server's proxy: the backend itself isn't answering.
      if (!data) throw new ChatError(friendlyError(res.status >= 500 ? null : res.status, undefined, false))
      if (!res.ok) throw new ChatError(friendlyError(res.status, data.detail, false))
      setConversationId(data.conversation_id)
      const page: PageSearchResults | null = data.search_results
      if (page) chatResults.show(page)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: data.reply,
          products: data.products,
          options: data.options,
          pageResults: page ? { title: page.title, total: page.total } : undefined,
        },
      ])
    } catch (err) {
      const msg = err instanceof ChatError ? err.message : 'Something went wrong with that message.'
      setMessages((m) => [...m, { role: 'error', text: msg, retryText: text }])
    } finally {
      clearTimeout(slowTimer)
      clearTimeout(timeout)
      setSending(false)
      setSlow(false)
      inputRef.current?.focus()
    }
  }

  async function showAgain(browse: BrowseRequest) {
    const res = await fetch('/api/page-search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(browse),
    })
    if (res.ok) chatResults.show(await res.json())
  }

  async function clearChat() {
    if (user) {
      if (!window.confirm('Delete your saved chat history? This cannot be undone.')) return
      const res = await fetch('/api/chat/history', { method: 'DELETE', credentials: 'same-origin' })
      if (!res.ok) {
        setMessages((m) => [...m, { role: 'error', text: "Couldn't clear your history. Please try again." }])
        return
      }
    }
    setMessages([])
    setHistoryCount(0)
    setConversationId(null)
    inputRef.current?.focus()
  }

  const greeting = user
    ? historyCount > 0
      ? `Welcome back, ${user.first_name}! Here's our conversation so far.`
      : `Hi ${user.first_name}! I'm the Campus Customs assistant. What are you shopping for today?`
    : "Hi! I'm the Campus Customs assistant. What are you shopping for today?"

  return (
    <div className="chat-dock">
      {open && (
        <section className="chat-panel" role="dialog" aria-label="Shopping assistant">
          <header className="chat-head">
            <div>
              <strong>Campus Customs Assistant</strong>
              <span className="chat-status">
                {user ? `Signed in as ${user.first_name} · chat history saved` : 'Guest · this chat is not saved'}
              </span>
            </div>
            <div className="chat-head-actions">
              {messages.length > 0 && (
                <button className="link-btn" onClick={clearChat} disabled={sending}>
                  {user ? 'Clear history' : 'New chat'}
                </button>
              )}
              <button className="icon-btn" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
            </div>
          </header>

          <div className="chat-body" ref={bodyRef} aria-live="polite">
            {historyState === 'loading' && <div className="chat-bubble chat-meta">Loading your saved chat…</div>}
            {historyState === 'error' && (
              <div className="chat-bubble chat-error">Couldn't load your saved chat. New messages will still be saved.</div>
            )}
            {messages.map((m, i) => (
              <Fragment key={i}>
              {i === historyCount && <div className="chat-bubble">{greeting}</div>}
              <div className={`chat-bubble chat-${m.role}`} role={m.role === 'error' ? 'alert' : undefined}>
                {formatText(m.text)}
                {m.role === 'error' && m.retryText && (
                  <div className="chat-error-actions">
                    <span>Your question wasn't lost. You can send it again:</span>
                    <button className="btn btn-primary btn-sm" onClick={() => retry(i, m.retryText!)} disabled={sending}>
                      Try again
                    </button>
                  </div>
                )}
                {m.pageResults && (
                  <div className="chat-page-note">
                    {m.pageResults.total === undefined
                      ? `Showed products on the page: ${m.pageResults.title}`
                      : m.pageResults.total > 0
                        ? `Showing ${m.pageResults.total} ${m.pageResults.total === 1 ? 'product' : 'products'} on the page: ${m.pageResults.title}`
                        : `No matching products: ${m.pageResults.title}`}
                    {m.pageResults.browse ? (
                      <button className="link-btn" onClick={() => showAgain(m.pageResults!.browse!)}>Show again ↓</button>
                    ) : (
                      <button
                        className="link-btn"
                        onClick={() => {
                          setOpen(false)
                          document.querySelector('.chat-results')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                        }}
                      >
                        View on page ↓
                      </button>
                    )}
                  </div>
                )}
                {m.options && m.options.length > 0 && (
                  <div className="chat-options" role="group" aria-label="Choose a product">
                    {m.options.map((o) => (
                      <button key={o.product_id} className="chat-option" onClick={() => choose(o)}
                              disabled={sending || i !== messages.length - 1}>
                        <img src={o.image_url} alt="" />
                        <span>
                          <strong>{o.name}</strong>
                          <small>{formatPrice(o.price)} · {o.sizes_in_stock.length ? o.sizes_in_stock.join(' ') : 'sold out'}</small>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
                {m.products && m.products.length > 0 && (
                  <ul className="chat-products">
                    {m.products.map((p) => (
                      <li key={p.product_id}>
                        <Link to={p.url} className="chat-product">
                          <img src={p.image_url} alt="" />
                          <span>
                            <strong>{p.name}</strong>
                            <small>{formatPrice(p.price)}{p.total_stock === 0 ? ' · Sold out' : ''}</small>
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              </Fragment>
            ))}
            {messages.length === historyCount && <div className="chat-bubble">{greeting}</div>}
            {sending && (
              <div className="chat-bubble chat-thinking" role="status">
                <span className="chat-typing" aria-hidden="true"><span /><span /><span /></span>
                <span>{slow ? 'Still working on it… thanks for waiting.' : 'Finding an answer…'}</span>
              </div>
            )}
          </div>

          <form className="chat-input" onSubmit={send}>
            <input
              ref={inputRef}
              type="text"
              placeholder={onProductPage ? 'Ask about this product…' : 'Ask about a product, price or size…'}
              value={draft}
              maxLength={MAX_LEN}
              onChange={(e) => setDraft(e.target.value)}
              aria-label="Message"
            />
            <button className="btn btn-primary btn-sm" type="submit" disabled={sending || !draft.trim()}>
              {sending ? 'Wait…' : 'Send'}
            </button>
          </form>
        </section>
      )}
      <button
        className={`chat-toggle ${open ? 'is-open' : ''}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Close shopping assistant' : 'Open shopping assistant'}
      >
        {open ? (
          <span aria-hidden="true">×</span>
        ) : (
          <>
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.2 3.6c-.5.4-1.3 0-1.3-.6V16A2.5 2.5 0 0 1 4 13.5Z" fill="currentColor" />
            </svg>
            <span>Ask us</span>
          </>
        )}
      </button>
    </div>
  )
}

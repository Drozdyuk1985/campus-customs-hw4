import { useEffect, useRef } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useChatResults } from '../chatResults'
import ProductCard from './ProductCard'

const CATEGORY_LINKS = ['T-Shirts', 'Crewnecks', 'Hoodies', 'Quarter-Zips', 'Long Sleeves', 'Jackets & Fleece']

// Product cards from the shopping assistant's latest search, shown at the top of the page.
export default function ChatResults() {
  const { results, version, clear } = useChatResults()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const ref = useRef<HTMLElement>(null)
  const onDetailPage = /^\/products\/[^/]+$/.test(pathname)

  // New results while reading a product page: go to the products page to show them.
  // Otherwise bring the results into view.
  useEffect(() => {
    if (version === 0) return
    if (onDetailPage) navigate('/products')
    else ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    // Only react to new searches, not to page changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version])

  if (!results || onDetailPage) return null
  const searched = results.query || results.category || 'that search'
  const filters = [
    results.category,
    results.max_price != null ? `under $${results.max_price}` : null,
    results.size_in_stock ? `size ${results.size_in_stock} in stock` : null,
    results.sort === 'price_low_to_high' ? 'lowest price first' : results.sort === 'price_high_to_low' ? 'highest price first' : null,
  ].filter(Boolean)

  return (
    <section className="chat-results container" ref={ref} aria-labelledby="chat-results-title" aria-live="polite">
      <div className="chat-results-head">
        <div>
          <span className="eyebrow">From the shopping assistant</span>
          <h2 id="chat-results-title">{results.title}</h2>
          <p className="muted small">
            {results.total} {results.total === 1 ? 'product' : 'products'}
            {results.query && <> matching “{results.query}”</>}
            {filters.length > 0 && <> · {filters.join(' · ')}</>}
          </p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={clear}>Clear results</button>
      </div>

      {results.total === 0 ? (
        <div className="chat-results-empty">
          <p><strong>No products matched “{searched}”.</strong> Try a broader word, or browse a category:</p>
          <div className="chips">
            {CATEGORY_LINKS.map((c) => (
              <Link key={c} className="chip" to={`/products?category=${encodeURIComponent(c)}`}>{c}</Link>
            ))}
            <Link className="chip active" to="/products">All products</Link>
          </div>
        </div>
      ) : (
        <>
          {!results.exact && (
            <p className="notice chat-results-partial">
              No exact match for “{searched}”. These are the closest items we have.
            </p>
          )}
          <div className="product-grid">
            {results.products.map((p) => <ProductCard key={p.product_id} product={p} />)}
          </div>
        </>
      )}
    </section>
  )
}

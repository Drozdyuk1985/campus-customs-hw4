import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchCategories, fetchProducts, type ProductFilters, type ProductSummary } from '../api'
import ProductCard from '../components/ProductCard'

// Price bands chosen around the catalogue's actual prices ($32 to $98).
const PRICE_BANDS = [
  { id: 'under-50', label: 'Under $50', min: undefined, max: 50 },
  { id: '50-70', label: '$50 – $70', min: 50, max: 70 },
  { id: '70-90', label: '$70 – $90', min: 70, max: 90 },
  { id: '90-plus', label: '$90 and up', min: 90, max: undefined },
] as const
const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const SORTS = [
  { id: 'name', label: 'Name (A–Z)' },
  { id: 'price_low_to_high', label: 'Price: low to high' },
  { id: 'price_high_to_low', label: 'Price: high to low' },
] as const
const FILTER_KEYS = ['category', 'q', 'price', 'size', 'sort'] as const

export default function Products() {
  const [params, setParams] = useSearchParams()
  const category = params.get('category') ?? ''
  const q = params.get('q') ?? ''
  const price = params.get('price') ?? ''
  const size = params.get('size') ?? ''
  const sort = params.get('sort') ?? 'name'
  const band = PRICE_BANDS.find((b) => b.id === price)
  const activeCount = [category, q, band ? price : '', SIZES.includes(size) ? size : ''].filter(Boolean).length

  const [search, setSearch] = useState(q)
  const [categories, setCategories] = useState<string[]>([])
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    fetchCategories(ctrl.signal).then(setCategories).catch(() => {})
    return () => ctrl.abort()
  }, [])

  // Keep the box in sync when the URL changes (e.g. back button or "Clear all").
  useEffect(() => {
    setSearch(q)
  }, [q])

  // Debounce typing into the URL so every keystroke isn't a request.
  useEffect(() => {
    const t = setTimeout(() => {
      if (search.trim() === q) return
      setParam('q', search.trim())
    }, 250)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, q])

  useEffect(() => {
    const ctrl = new AbortController()
    const filters: ProductFilters = {
      q, category,
      minPrice: band?.min, maxPrice: band?.max,
      size: SIZES.includes(size) ? size : undefined,
      sort,
    }
    setError(false)
    fetchProducts(filters, ctrl.signal)
      .then(setProducts)
      .catch((e) => {
        if (e.name !== 'AbortError') setError(true)
      })
    return () => ctrl.abort()
  }, [q, category, band, size, sort])

  function setParam(key: (typeof FILTER_KEYS)[number], value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: key === 'q' })
  }
  const toggle = (key: 'category' | 'price' | 'size', value: string, current: string) =>
    setParam(key, current === value ? '' : value)

  function clearAll() {
    const next = new URLSearchParams(params)
    FILTER_KEYS.filter((k) => k !== 'sort').forEach((k) => next.delete(k))
    setParams(next)
    setSearch('')
  }

  const summary = [
    category,
    band?.label,
    SIZES.includes(size) ? `size ${size} in stock` : '',
    q ? `“${q}”` : '',
  ].filter(Boolean)

  return (
    <div className="container page">
      <div className="page-head">
        <h1>{category || 'All products'}</h1>
        <p className="muted" aria-live="polite">
          {products === null ? 'Loading…' : `${products.length} ${products.length === 1 ? 'item' : 'items'}`}
          {summary.length > 0 && ` · ${summary.join(' · ')}`}
        </p>
      </div>

      <section className="filter-panel" aria-label="Filter products">
        <div className="filter-row">
          <span className="filter-label">Category</span>
          <div className="chips" role="group" aria-label="Category">
            <button className={`chip ${category === '' ? 'active' : ''}`} aria-pressed={category === ''} onClick={() => setParam('category', '')}>All</button>
            {categories.map((c) => (
              <button key={c} className={`chip ${category === c ? 'active' : ''}`} aria-pressed={category === c} onClick={() => toggle('category', c, category)}>
                {c}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-row">
          <span className="filter-label">Price</span>
          <div className="chips" role="group" aria-label="Price">
            {PRICE_BANDS.map((b) => (
              <button key={b.id} className={`chip ${price === b.id ? 'active' : ''}`} aria-pressed={price === b.id} onClick={() => toggle('price', b.id, price)}>
                {b.label}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-row">
          <span className="filter-label">Size in stock</span>
          <div className="chips" role="group" aria-label="Size in stock">
            {SIZES.map((s) => (
              <button key={s} className={`chip chip-size ${size === s ? 'active' : ''}`} aria-pressed={size === s} onClick={() => toggle('size', s, size)}>
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-row filter-row-last">
          <input
            type="search"
            className="search"
            placeholder="Search: hockey, Saybrook, gray…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search products"
          />
          <label className="sort">
            <span className="filter-label">Sort</span>
            <select value={sort} onChange={(e) => setParam('sort', e.target.value === 'name' ? '' : e.target.value)}>
              {SORTS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </label>
          <button className="btn btn-ghost btn-sm clear-filters" onClick={clearAll} disabled={activeCount === 0}>
            Clear all filters{activeCount > 0 ? ` (${activeCount})` : ''}
          </button>
        </div>
      </section>

      {error && <p className="notice notice-error">Products could not be loaded. Is the backend running?</p>}

      {products !== null && products.length === 0 && !error && (
        <div className="empty">
          <p>
            <strong>No products match these filters.</strong>
            <br />
            <span className="muted">Try removing one, for example a different size or price range.</span>
          </p>
          <button className="btn btn-primary" onClick={clearAll}>Clear all filters</button>
        </div>
      )}

      <div className="product-grid">
        {products?.map((p) => <ProductCard key={p.product_id} product={p} highlightSize={SIZES.includes(size) ? size : undefined} />)}
      </div>
    </div>
  )
}

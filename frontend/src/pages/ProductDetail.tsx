import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, LOW_STOCK, NotFoundError, type ProductDetail as Product } from '../api'
import NotFound from './NotFound'
import { openChat } from '../openChat'

function stockLabel(quantity: number) {
  if (quantity === 0) return 'Sold out'
  if (quantity <= LOW_STOCK) return `Only ${quantity} left`
  return `${quantity} in stock`
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [status, setStatus] = useState<'loading' | 'ok' | 'missing' | 'error'>('loading')

  useEffect(() => {
    const ctrl = new AbortController()
    setStatus('loading')
    fetchProduct(productId, ctrl.signal)
      .then((p) => {
        setProduct(p)
        setStatus('ok')
      })
      .catch((e) => {
        if (e.name === 'AbortError') return
        setStatus(e instanceof NotFoundError ? 'missing' : 'error')
      })
    return () => ctrl.abort()
  }, [productId])

  if (status === 'missing') return <NotFound what="product" />
  if (status === 'error')
    return (
      <div className="container page">
        <p className="notice notice-error">This product could not be loaded. Is the backend running?</p>
      </div>
    )
  if (status === 'loading' || !product) return <div className="container page muted">Loading…</div>

  const inStockSizes = product.inventory.filter((s) => s.quantity > 0).length

  return (
    <div className="container page">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/products">Products</Link>
        <span>/</span>
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link>
        <span>/</span>
        <span aria-current="page">{product.name}</span>
      </nav>

      <div className="detail">
        <div className="detail-img">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div className="detail-info">
          <span className="eyebrow">{product.garment_type}</span>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>

          <div className="detail-block">
            <h2>Colors</h2>
            <div className="tags">
              {product.colors.map((c) => <span key={c} className="tag">{c}</span>)}
            </div>
          </div>

          <div className="detail-block">
            <h2>
              Sizes & stock
              <span className="muted small"> · {inStockSizes} of {product.inventory.length} sizes available</span>
            </h2>
            <ul className="size-grid">
              {product.inventory.map((s) => (
                <li
                  key={s.size}
                  className={`size ${s.quantity === 0 ? 'size-out' : s.quantity <= LOW_STOCK ? 'size-low' : ''}`}
                >
                  <strong>{s.size}</strong>
                  <span>{stockLabel(s.quantity)}</span>
                </li>
              ))}
            </ul>
            <p className="muted small">{product.total_stock} items in stock across all sizes.</p>
          </div>

          <div className="ask-box">
            <div>
              <strong>Questions about this piece?</strong>
              <span>Our shopping assistant knows this product's sizes, stock and colours.</span>
            </div>
            <div className="ask-chips">
              {[
                // The size question is left open so the customer types their size before sending.
                { label: 'Is this in my size?', prefill: 'Is this available in size ' },
                { label: 'What colours does it come in?', prefill: 'What colours does this come in?' },
                { label: 'Show me something similar', prefill: 'Can you suggest something similar that is in stock?' },
              ].map((q) => (
                <button key={q.label} className="chip" onClick={() => openChat(q.prefill)}>{q.label}</button>
              ))}
            </div>
          </div>

          <Link to="/products" className="btn btn-ghost">← Back to all products</Link>
        </div>
      </div>
    </div>
  )
}

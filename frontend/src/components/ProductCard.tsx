import { Link } from 'react-router-dom'
import { formatPrice, type ProductSummary } from '../api'

export default function ProductCard({ product, highlightSize }: { product: ProductSummary; highlightSize?: string }) {
  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card-img">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {product.total_stock === 0 && <span className="badge badge-dark">Sold out</span>}
        <span className="card-cta" aria-hidden="true">View details →</span>
      </div>
      <div className="product-card-body">
        <span className="eyebrow">{product.category}</span>
        <h3>{product.name}</h3>
        <p className="product-card-desc">{product.short_description}</p>
        <div className="card-foot">
          <span className="price">{formatPrice(product.price)}</span>
          <span className="card-sizes" aria-label={`Sizes in stock: ${product.sizes_in_stock.join(', ') || 'none'}`}>
            {product.sizes_in_stock.length === 0
              ? 'Sold out'
              : product.sizes_in_stock.map((s) => (
                  <span key={s} className={s === highlightSize ? 'hl' : undefined}>{s}</span>
                ))}
          </span>
        </div>
      </div>
    </Link>
  )
}

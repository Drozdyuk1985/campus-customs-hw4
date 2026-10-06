import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchCategories, fetchProducts, type ProductSummary } from '../api'
import ProductCard from '../components/ProductCard'
import { openChat } from '../openChat'

const HERO_IDS = ['basic-hoodie-big-yale', 'yale-grandpa-crewneck', 'boola-boola-t-shirt']
// Themes that really appear in the catalogue's product names.
const RIBBON = ['Residential colleges', 'Graduate & professional schools', 'Varsity sports', 'Mom · Dad · Grandpa', 'Game day', 'Bulldogs']

export default function Home() {
  const [products, setProducts] = useState<ProductSummary[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [error, setError] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    Promise.all([fetchProducts({}, ctrl.signal), fetchCategories(ctrl.signal)])
      .then(([p, c]) => {
        setProducts(p)
        setCategories(c)
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setError(true)
      })
    return () => ctrl.abort()
  }, [])

  const hero = useMemo(
    () => HERO_IDS.map((id) => products.find((p) => p.product_id === id)).filter((p) => p !== undefined),
    [products],
  )
  const tiles = useMemo(
    () =>
      categories
        .map((c) => ({ name: c, items: products.filter((p) => p.category === c) }))
        .filter((t) => t.items.length > 0),
    [categories, products],
  )
  const hoodies = products.filter((p) => p.category === 'Hoodies').slice(0, 4)
  const tees = products.filter((p) => p.category === 'T-Shirts').slice(0, 4)
  const priceRange = products.length
    ? `$${Math.min(...products.map((p) => p.price))}–$${Math.max(...products.map((p) => p.price))}`
    : ''

  return (
    <>
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <span className="eyebrow eyebrow-light">Yale apparel · New Haven</span>
            <h1>
              Wear your <em>Bulldog</em> pride.
            </h1>
            <p>
              Hoodies, crewnecks, tees and layers for students, alumni and families.
              Find your residential college, your sport or your school, then pick your size.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-light">Shop the collection</Link>
              <button className="btn btn-outline-light" onClick={() => openChat()}>Ask the assistant</button>
            </div>
            {products.length > 0 && (
              <dl className="hero-facts">
                <div><dt>{products.length}</dt><dd>styles</dd></div>
                <div><dt>{categories.length}</dt><dd>categories</dd></div>
                <div><dt>XS–XXL</dt><dd>sizes</dd></div>
                <div><dt>{priceRange}</dt><dd>price range</dd></div>
              </dl>
            )}
          </div>
          <div className="hero-art" aria-hidden="true">
            {hero.map((p, i) => (
              <figure key={p.product_id} className={`hero-polaroid hero-polaroid-${i}`}>
                <img src={p.image_url} alt="" />
                <figcaption>{p.name}</figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      <div className="ribbon" aria-hidden="true">
        <div className="ribbon-track">
          {[...RIBBON, ...RIBBON].map((t, i) => (
            <span key={i}>{t}<i>✦</i></span>
          ))}
        </div>
      </div>

      {error && (
        <div className="container">
          <p className="notice notice-error">Products could not be loaded. Is the backend running?</p>
        </div>
      )}

      {tiles.length > 0 && (
        <section className="section container" data-reveal>
          <div className="section-head">
            <div>
              <span className="eyebrow">Start here</span>
              <h2 className="varsity">Shop by category</h2>
            </div>
            <Link to="/products" className="link-arrow">View all {products.length} →</Link>
          </div>
          <div className="category-grid">
            {tiles.map((t) => (
              <Link key={t.name} to={`/products?category=${encodeURIComponent(t.name)}`} className="category-tile">
                <span className="patch">
                  <img src={t.items[0].image_url} alt="" loading="lazy" />
                </span>
                <span className="category-label">
                  {t.name}
                  <small>{t.items.length} styles</small>
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {hoodies.length > 0 && (
        <section className="section container" data-reveal>
          <div className="section-head">
            <div>
              <span className="eyebrow">Cozy layers</span>
              <h2 className="varsity">Layer up</h2>
            </div>
            <Link to="/products?category=Hoodies" className="link-arrow">All hoodies →</Link>
          </div>
          <div className="product-grid">
            {hoodies.map((p) => <ProductCard key={p.product_id} product={p} />)}
          </div>
        </section>
      )}

      <section className="section container" data-reveal>
        <div className="ways">
          <div className="ways-intro">
            <span className="eyebrow">Not sure yet?</span>
            <h2 className="varsity">Three easy ways to find yours</h2>
          </div>
          <Link to="/products?size=M" className="way">
            <span className="way-num">1</span>
            <strong>Filter by size and budget</strong>
            <span>Only see styles that are in stock in your size and within your price range.</span>
          </Link>
          <button className="way" onClick={() => openChat('I need a gift idea. Can you help?')}>
            <span className="way-num">2</span>
            <strong>Ask the shopping assistant</strong>
            <span>Describe who it's for. It checks real prices and stock, and suggests in-stock alternatives.</span>
          </button>
          <Link to="/about" className="way">
            <span className="way-num">3</span>
            <strong>Visit us on Broadway</strong>
            <span>See it in person at 57 Broadway, New Haven, CT 06511.</span>
          </Link>
        </div>
      </section>

      {tees.length > 0 && (
        <section className="section container" data-reveal>
          <div className="section-head">
            <div>
              <span className="eyebrow">Everyday favourites</span>
              <h2 className="varsity">Tees for every day</h2>
            </div>
            <Link to="/products?category=T-Shirts" className="link-arrow">All T-shirts →</Link>
          </div>
          <div className="product-grid">
            {tees.map((p) => <ProductCard key={p.product_id} product={p} />)}
          </div>
        </section>
      )}

      <section className="section container visit" data-reveal>
        <div className="visit-card">
          <div>
            <span className="eyebrow eyebrow-light">Come visit</span>
            <h2>Find us on Broadway</h2>
            <p>
              Campus Customs runs the Yale Bulldog Blue shop at <strong>57 Broadway, New Haven, CT 06511</strong>,
              just steps from campus.
            </p>
          </div>
          <Link to="/about" className="btn btn-light">About the shop</Link>
        </div>
      </section>
    </>
  )
}

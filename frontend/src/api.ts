// Types and fetch helpers for the FastAPI backend (backend/main.py).

export interface ProductSummary {
  product_id: string
  name: string
  garment_type: string
  category: string
  short_description: string
  colors: string[]
  price: number
  image_url: string
  total_stock: number
  sizes_in_stock: string[]
}

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductDetail extends ProductSummary {
  description: string
  search_tags: string[]
  inventory: SizeStock[]
}

export class NotFoundError extends Error {}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal })
  if (res.status === 404) throw new NotFoundError('Not found')
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export function fetchCategories(signal?: AbortSignal) {
  return getJson<string[]>('/api/categories', signal)
}

export interface ProductFilters {
  q?: string
  category?: string
  minPrice?: number
  maxPrice?: number
  size?: string
  sort?: string
}

export function fetchProducts(params: ProductFilters, signal?: AbortSignal) {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.category) search.set('category', params.category)
  if (params.minPrice !== undefined) search.set('min_price', String(params.minPrice))
  if (params.maxPrice !== undefined) search.set('max_price', String(params.maxPrice))
  if (params.size) search.set('size', params.size)
  if (params.sort && params.sort !== 'name') search.set('sort', params.sort)
  const qs = search.toString()
  return getJson<ProductSummary[]>(`/api/products${qs ? `?${qs}` : ''}`, signal)
}

export function fetchProduct(productId: string, signal?: AbortSignal) {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`, signal)
}

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export const LOW_STOCK = 3

// Search results the shopping assistant puts on the page (POST /api/chat -> search_results).
export interface PageSearchResults {
  title: string
  query: string
  category: string | null
  max_price: number | null
  sort: 'relevance' | 'price_low_to_high' | 'price_high_to_low'
  size_in_stock: string | null
  total: number
  exact: boolean
  products: ProductSummary[]
}

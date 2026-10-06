import { Link } from 'react-router-dom'

export default function NotFound({ what = 'page' }: { what?: string }) {
  return (
    <div className="container page empty">
      <h1>We couldn't find that {what}.</h1>
      <Link to="/products" className="btn btn-primary">Browse products</Link>
    </div>
  )
}

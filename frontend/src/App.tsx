import { useEffect } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './auth'
import ChatPanel from './components/ChatPanel'
import ChatResults from './components/ChatResults'
import Crest from './components/Crest'
import { openChat } from './openChat'
import About from './pages/About'
import CreateAccount from './pages/CreateAccount'
import Home from './pages/Home'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import ProductDetail from './pages/ProductDetail'
import Products from './pages/Products'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

// Fade sections up as they scroll into view. Elements opt in with data-reveal.
// (Turned off for people who ask for reduced motion; see index.css.)
function RevealOnScroll() {
  const { pathname } = useLocation()
  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('revealed')
          io.unobserve(e.target)
        }
      }),
      { rootMargin: '0px 0px -8% 0px' },
    )
    const watch = () => document.querySelectorAll('[data-reveal]:not(.revealed)').forEach((el) => io.observe(el))
    watch()
    // Content arrives after data loads, so keep watching for new sections.
    const mo = new MutationObserver(watch)
    mo.observe(document.body, { childList: true, subtree: true })
    return () => {
      io.disconnect()
      mo.disconnect()
    }
  }, [pathname])
  return null
}

function AccountNav() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  if (loading) return <div className="account-nav" />
  if (user) {
    return (
      <div className="account-nav">
        <span className="greeting" title={user.email}>Hi, {user.first_name}</span>
        <button
          className="btn btn-ghost btn-sm"
          onClick={async () => {
            await logout()
            navigate('/', { state: { flash: "You've been logged out." } })
          }}
        >
          Log out
        </button>
      </div>
    )
  }
  return (
    <div className="account-nav">
      <NavLink to="/login">Log in</NavLink>
      <NavLink to="/create-account" className="btn btn-primary btn-sm">Create account</NavLink>
    </div>
  )
}

// One-time message passed through navigation state (e.g. after login/logout).
function Flash() {
  const location = useLocation()
  const flash = (location.state as { flash?: string } | null)?.flash
  if (!flash) return null
  return (
    <div className="container">
      <p className="notice flash" role="status">{flash}</p>
    </div>
  )
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <RevealOnScroll />
      <div className="announce">
        <div className="container announce-inner">
          <span>Officially licensed Yale apparel</span>
          <span className="announce-dot" aria-hidden="true">✦</span>
          <span>Visit us at 57 Broadway, New Haven</span>
        </div>
      </div>
      <header className="site-header">
        <div className="container header-inner">
          <Link to="/" className="brand" aria-label="Campus Customs home">
            <Crest size={34} />
            <span className="brand-name">
              Campus Customs
              <small>Yale Bulldog Blue</small>
            </span>
          </Link>
          <nav className="main-nav" aria-label="Main">
            <NavLink to="/" end>Home</NavLink>
            <NavLink to="/products">Products</NavLink>
            <NavLink to="/about">About Us</NavLink>
            <button className="nav-ask" onClick={() => openChat()}>Ask the assistant</button>
          </nav>
          <AccountNav />
        </div>
      </header>

      <main>
        <Flash />
        <ChatResults />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>

      <footer className="site-footer">
        <div className="footer-rule" aria-hidden="true" />
        <div className="container footer-inner">
          <div className="footer-brand">
            <Crest size={40} />
            <div>
              <div className="footer-name">Campus Customs</div>
              <p>Yale apparel for students, alumni and the families who cheer them on.</p>
            </div>
          </div>
          <nav className="footer-col" aria-label="Shop">
            <h2>Shop</h2>
            <Link to="/products">All products</Link>
            <Link to="/products?category=Hoodies">Hoodies</Link>
            <Link to="/products?category=Crewnecks">Crewnecks</Link>
            <Link to="/products?category=T-Shirts">T-Shirts</Link>
          </nav>
          <nav className="footer-col" aria-label="Help">
            <h2>Help</h2>
            <button className="footer-link-btn" onClick={() => openChat()}>Ask the assistant</button>
            <Link to="/about">About us</Link>
            <Link to="/login">Log in</Link>
            <Link to="/create-account">Create account</Link>
          </nav>
          <div className="footer-col">
            <h2>Visit</h2>
            <p>57 Broadway<br />New Haven, CT 06511</p>
          </div>
        </div>
        <p className="container footer-note">HW4 class project for Yale SOM MGT 409. Not the official store.</p>
      </footer>

      <ChatPanel />
    </>
  )
}

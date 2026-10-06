import { Link } from 'react-router-dom'

// Facts here are limited to what yalebulldogblue.com states (operator, licensing,
// address, what it sells) and what is in our own catalogue. No invented history.
export default function About() {
  return (
    <div className="container page about">
      <div className="page-head">
        <span className="eyebrow">About us</span>
        <h1>
          Made for <span className="accent">Bulldogs</span>, near and far.
        </h1>
      </div>

      <div className="about-grid">
        <section className="about-card">
          <h2>Who we are</h2>
          <p>
            Campus Customs runs Yale Bulldog Blue, a shop for officially licensed Yale
            merchandise. Alongside clothing, the shop also carries accessories, home goods
            and gifts.
          </p>
        </section>

        <section className="about-card">
          <h2>What you'll find here</h2>
          <p>
            This site focuses on clothing: T-shirts, crewnecks, hoodies, quarter-zips,
            long sleeves, jackets and fleece. Pieces celebrate residential colleges,
            graduate and professional schools, Yale sports, and the people who cheer them on.
          </p>
          <Link to="/products" className="link-arrow">Browse the collection →</Link>
        </section>

        <section className="about-card">
          <h2>Visit the shop</h2>
          <p>
            57 Broadway
            <br />
            New Haven, CT 06511
          </p>
        </section>

        <section className="about-card">
          <h2>Need help choosing?</h2>
          <p>
            A shopping assistant is coming to this site soon. It will help you compare
            styles and check which sizes are in stock.
          </p>
        </section>
      </div>
    </div>
  )
}

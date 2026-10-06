// The Campus Customs mark: an original shield monogram (not a Yale logo).
export default function Crest({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size * 1.15} viewBox="0 0 40 46" aria-hidden="true" className="crest">
      <path d="M20 1.5 37 6.5v14.8C37 32.6 29.7 40.6 20 44.5 10.3 40.6 3 32.6 3 21.3V6.5Z" fill="currentColor" />
      <path d="M20 4.6 34 8.7v12.5c0 9.6-6 16.3-14 19.8-8-3.5-14-10.2-14-19.8V8.7Z" fill="none" stroke="#fff" strokeOpacity=".55" strokeWidth=".9" />
      <text x="20" y="27.5" textAnchor="middle" fontFamily="'Fraunces Variable', Georgia, serif" fontSize="15" fontWeight="700" style={{ fill: 'var(--crest-ink, #fff)' }} letterSpacing=".5">
        CC
      </text>
      <path d="M11 32.2h18" stroke="#fff" strokeOpacity=".6" strokeWidth=".8" />
    </svg>
  )
}

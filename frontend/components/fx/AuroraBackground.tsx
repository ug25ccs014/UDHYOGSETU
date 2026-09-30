export default function AuroraBackground({ className = '' }: { className?: string }) {
  return (
    <div className={`aurora-bg ${className}`} aria-hidden="true">
      <span className="aurora-blob aurora-blob-a" />
      <span className="aurora-blob aurora-blob-b" />
      <span className="aurora-blob aurora-blob-c" />
    </div>
  )
}

interface InlineStatProps {
  label: string
  value: string | number
}

export function InlineStat({ label, value }: InlineStatProps) {
  return (
    <div>
      <span className="text-xl font-semibold">{value}</span>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  )
}

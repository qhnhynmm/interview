import { Icon } from '@/components/icons.jsx'

// Color tones for ToggleChip. `accent` glows burgundy; `neutral` is a quiet
// gray/white so two toggles sitting side by side stay visually distinct.
const CHIP_TONE = {
  accent: {
    border: 'var(--tint-border)',
    background: 'var(--tint)',
    color: 'var(--on-tint)',
    glow: '0 0 0 3px rgba(190, 18, 60, 0.08)',
  },
  neutral: {
    border: 'rgba(255, 255, 255, 0.22)',
    background: 'rgba(255, 255, 255, 0.08)',
    color: 'var(--color-text)',
    glow: '0 0 0 3px rgba(255, 255, 255, 0.05)',
  },
}

// Pill toggle button used in the code panels' top toolbar. Lights up with its
// tone color when its panel is visible, dims to a quiet outline when hidden.
export default function ToggleChip({ active, onClick, icon, label, title, tone = 'accent' }) {
  const t = CHIP_TONE[tone] ?? CHIP_TONE.accent
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        height: 30,
        padding: '0 12px',
        fontSize: 12,
        fontWeight: 600,
        cursor: 'pointer',
        borderRadius: 999,
        border: `1px solid ${active ? t.border : 'var(--color-border)'}`,
        background: active ? t.background : 'transparent',
        color: active ? t.color : 'var(--color-muted)',
        boxShadow: active ? t.glow : 'none',
        transition: 'background 0.15s ease, color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease',
      }}
    >
      <Icon name={icon} size={14} />
      {label}
    </button>
  )
}

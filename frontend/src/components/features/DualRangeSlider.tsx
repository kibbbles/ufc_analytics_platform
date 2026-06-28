import { useRef, useCallback, useEffect } from 'react'

interface Props {
  min: number
  max: number
  step?: number
  valueLo: number
  valueHi: number
  onChange: (lo: number, hi: number) => void
  disabled?: boolean
  unit?: string        // e.g. "pp" appended to labels
}

export function DualRangeSlider({ min, max, step = 1, valueLo, valueHi, onChange, disabled, unit = '' }: Props) {
  const trackRef = useRef<HTMLDivElement>(null)
  const dragRef  = useRef<{ type: 'lo' | 'hi' | 'fill'; startX: number; startLo: number; startHi: number } | null>(null)

  const toPercent = (v: number) => ((v - min) / (max - min)) * 100
  const fromPercent = (pct: number) => {
    const raw = min + (pct / 100) * (max - min)
    return Math.round(raw / step) * step
  }
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

  const getDelta = useCallback((clientX: number): number => {
    const track = trackRef.current
    if (!track) return 0
    const rect = track.getBoundingClientRect()
    return ((clientX - dragRef.current!.startX) / rect.width) * (max - min)
  }, [max, min])

  const handlePointerMove = useCallback((e: PointerEvent) => {
    if (!dragRef.current) return
    const delta = getDelta(e.clientX)
    const { type, startLo, startHi } = dragRef.current

    if (type === 'fill') {
      const gap  = startHi - startLo
      let lo = startLo + delta
      let hi = startHi + delta
      if (lo < min) { lo = min; hi = min + gap }
      if (hi > max) { hi = max; lo = max - gap }
      lo = clamp(Math.round(lo / step) * step, min, max - step)
      hi = clamp(Math.round(hi / step) * step, min + step, max)
      if (lo !== valueLo || hi !== valueHi) onChange(lo, hi)
    } else if (type === 'lo') {
      const lo = clamp(Math.round((startLo + delta) / step) * step, min, valueHi - step)
      if (lo !== valueLo) onChange(lo, valueHi)
    } else {
      const hi = clamp(Math.round((startHi + delta) / step) * step, valueLo + step, max)
      if (hi !== valueHi) onChange(valueLo, hi)
    }
  }, [getDelta, min, max, step, valueLo, valueHi, onChange])

  const handlePointerUp = useCallback(() => {
    dragRef.current = null
    window.removeEventListener('pointermove', handlePointerMove)
    window.removeEventListener('pointerup', handlePointerUp)
  }, [handlePointerMove])

  const startDrag = useCallback((type: 'lo' | 'hi' | 'fill', e: React.PointerEvent) => {
    if (disabled) return
    e.preventDefault()
    dragRef.current = { type, startX: e.clientX, startLo: valueLo, startHi: valueHi }
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
  }, [disabled, valueLo, valueHi, handlePointerMove, handlePointerUp])

  // Keyboard for thumbs
  const handleKeyLo = (e: React.KeyboardEvent) => {
    if (disabled) return
    if (e.key === 'ArrowLeft')  onChange(clamp(valueLo - step, min, valueHi - step), valueHi)
    if (e.key === 'ArrowRight') onChange(clamp(valueLo + step, min, valueHi - step), valueHi)
  }
  const handleKeyHi = (e: React.KeyboardEvent) => {
    if (disabled) return
    if (e.key === 'ArrowLeft')  onChange(valueLo, clamp(valueHi - step, valueLo + step, max))
    if (e.key === 'ArrowRight') onChange(valueLo, clamp(valueHi + step, valueLo + step, max))
  }

  // Click on track to set nearest thumb
  const handleTrackClick = (e: React.MouseEvent) => {
    if (disabled) return
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    const pct = ((e.clientX - rect.left) / rect.width) * 100
    const v = clamp(fromPercent(pct), min, max)
    const midpoint = (valueLo + valueHi) / 2
    if (v <= midpoint) onChange(clamp(v, min, valueHi - step), valueHi)
    else               onChange(valueLo, clamp(v, valueLo + step, max))
  }

  useEffect(() => () => {
    window.removeEventListener('pointermove', handlePointerMove)
    window.removeEventListener('pointerup', handlePointerUp)
  }, [handlePointerMove, handlePointerUp])

  const loPercent = toPercent(valueLo)
  const hiPercent = toPercent(valueHi)
  const thumbSize = 16

  return (
    <div className={`select-none ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
      <div
        ref={trackRef}
        className="relative h-5 cursor-pointer"
        style={{ paddingInline: thumbSize / 2 }}
        onClick={handleTrackClick}
      >
        {/* Track */}
        <div
          className="absolute inset-y-0 left-0 right-0 flex items-center"
          style={{ paddingInline: thumbSize / 2 }}
        >
          <div className="w-full h-1 rounded-full bg-[var(--color-border)]" />
        </div>

        {/* Fill bar (draggable) */}
        <div
          className="absolute inset-y-0 flex items-center"
          style={{
            left: `calc(${loPercent}% + ${thumbSize / 2}px)`,
            right: `calc(${100 - hiPercent}% + ${thumbSize / 2}px)`,
          }}
          onPointerDown={(e) => { e.stopPropagation(); startDrag('fill', e) }}
        >
          <div
            className="w-full h-1 rounded-full cursor-ew-resize"
            style={{ background: 'var(--color-accent, #e63946)' }}
          />
        </div>

        {/* Lo thumb */}
        <div
          role="slider"
          aria-valuemin={min}
          aria-valuemax={valueHi - step}
          aria-valuenow={valueLo}
          tabIndex={disabled ? -1 : 0}
          className="absolute top-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--color-accent,#e63946)] bg-[var(--color-bg)] cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--color-accent,#e63946)] focus:ring-offset-1"
          style={{ left: `${loPercent}%`, width: thumbSize, height: thumbSize }}
          onPointerDown={(e) => { e.stopPropagation(); startDrag('lo', e) }}
          onKeyDown={handleKeyLo}
        />

        {/* Hi thumb */}
        <div
          role="slider"
          aria-valuemin={valueLo + step}
          aria-valuemax={max}
          aria-valuenow={valueHi}
          tabIndex={disabled ? -1 : 0}
          className="absolute top-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--color-accent,#e63946)] bg-[var(--color-bg)] cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--color-accent,#e63946)] focus:ring-offset-1"
          style={{ left: `${hiPercent}%`, width: thumbSize, height: thumbSize }}
          onPointerDown={(e) => { e.stopPropagation(); startDrag('hi', e) }}
          onKeyDown={handleKeyHi}
        />
      </div>

      <div className="flex justify-between text-[11px] text-[var(--color-text-muted)] font-mono tabular-nums mt-0.5">
        <span>{min}{unit}</span>
        <span className="font-medium text-[var(--color-text)]">{valueLo}–{valueHi}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  )
}

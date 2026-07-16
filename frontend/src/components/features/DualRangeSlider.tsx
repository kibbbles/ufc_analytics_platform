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

  // Latest controlled values / callback held in refs so the pointer handlers
  // below can keep a STABLE identity across renders. If they were recreated
  // mid-drag (valueLo/valueHi/onChange all change on the first move), the
  // unmount cleanup effect would detach the live window listeners and the drag
  // would die after a single step - the "takes several drags to move it" bug.
  const valueLoRef  = useRef(valueLo)
  const valueHiRef  = useRef(valueHi)
  const onChangeRef = useRef(onChange)
  valueLoRef.current  = valueLo
  valueHiRef.current  = valueHi
  onChangeRef.current = onChange

  const toPercent = (v: number) => ((v - min) / (max - min)) * 100
  const fromPercent = (pct: number) => {
    const raw = min + (pct / 100) * (max - min)
    return Math.round(raw / step) * step
  }
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

  const handlePointerMove = useCallback((e: PointerEvent) => {
    const drag  = dragRef.current
    const track = trackRef.current
    if (!drag || !track) return
    const delta = ((e.clientX - drag.startX) / track.getBoundingClientRect().width) * (max - min)
    const { type, startLo, startHi } = drag
    const vLo = valueLoRef.current
    const vHi = valueHiRef.current
    const snap = (v: number) => Math.round(v / step) * step

    if (type === 'fill') {
      const gap  = startHi - startLo
      let lo = startLo + delta
      let hi = startHi + delta
      if (lo < min) { lo = min; hi = min + gap }
      if (hi > max) { hi = max; lo = max - gap }
      lo = clamp(snap(lo), min, max - step)
      hi = clamp(snap(hi), min + step, max)
      if (lo !== vLo || hi !== vHi) onChangeRef.current(lo, hi)
    } else if (type === 'lo') {
      const lo = clamp(snap(startLo + delta), min, vHi - step)
      if (lo !== vLo) onChangeRef.current(lo, vHi)
    } else {
      const hi = clamp(snap(startHi + delta), vLo + step, max)
      if (hi !== vHi) onChangeRef.current(vLo, hi)
    }
  }, [min, max, step])

  const handlePointerUp = useCallback(() => {
    dragRef.current = null
    window.removeEventListener('pointermove', handlePointerMove)
    window.removeEventListener('pointerup', handlePointerUp)
  }, [handlePointerMove])

  const startDrag = useCallback((type: 'lo' | 'hi' | 'fill', e: React.PointerEvent) => {
    if (disabled) return
    e.preventDefault()
    dragRef.current = { type, startX: e.clientX, startLo: valueLoRef.current, startHi: valueHiRef.current }
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
  }, [disabled, handlePointerMove, handlePointerUp])

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
            style={{ background: 'var(--color-accent)' }}
          />
        </div>

        {/* Lo thumb */}
        <div
          role="slider"
          aria-valuemin={min}
          aria-valuemax={valueHi - step}
          aria-valuenow={valueLo}
          tabIndex={disabled ? -1 : 0}
          className="absolute top-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--color-accent)] bg-[var(--color-bg)] cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:ring-offset-1"
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
          className="absolute top-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--color-accent)] bg-[var(--color-bg)] cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:ring-offset-1"
          style={{ left: `${hiPercent}%`, width: thumbSize, height: thumbSize }}
          onPointerDown={(e) => { e.stopPropagation(); startDrag('hi', e) }}
          onKeyDown={handleKeyHi}
        />
      </div>

      <div className="flex justify-between text-xs text-[var(--color-text-muted)] font-mono tabular-nums mt-0.5">
        <span>{min}{unit}</span>
        <span className="font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">{valueLo}–{valueHi}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  )
}

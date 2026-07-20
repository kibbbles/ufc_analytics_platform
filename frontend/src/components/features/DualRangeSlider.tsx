import { useRef, useCallback, useEffect, useLayoutEffect } from 'react'

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

  // Latest controlled values / callback held in refs. handlePointerMove is
  // attached once at drag start and closes over that render's scope, so it must
  // read valueLo/valueHi/onChange through refs to see values updated during the
  // drag. Reading them directly would freeze the drag at its starting values.
  const valueLoRef  = useRef(valueLo)
  const valueHiRef  = useRef(valueHi)
  const onChangeRef = useRef(onChange)

  // Written in a layout effect rather than during render: render must stay pure
  // for StrictMode's double-invoke and concurrent rendering. Layout timing is
  // deliberate - it commits synchronously, so the refs are current before the
  // next pointermove can be dispatched mid-drag.
  useLayoutEffect(() => {
    valueLoRef.current  = valueLo
    valueHiRef.current  = valueHi
    onChangeRef.current = onChange
  })

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

  // Listeners are torn down by aborting the controller they were attached with,
  // never by passing the same function reference back to removeEventListener.
  // Teardown therefore does not depend on handler identity staying stable, so a
  // mid-drag change to min/max/step can no longer strand a live listener.
  const dragAbortRef = useRef<AbortController | null>(null)

  const endDrag = useCallback(() => {
    dragRef.current = null
    dragAbortRef.current?.abort()
    dragAbortRef.current = null
  }, [])

  const startDrag = useCallback((type: 'lo' | 'hi' | 'fill', e: React.PointerEvent) => {
    if (disabled) return
    e.preventDefault()
    dragRef.current = { type, startX: e.clientX, startLo: valueLoRef.current, startHi: valueHiRef.current }
    dragAbortRef.current?.abort()
    const controller = new AbortController()
    dragAbortRef.current = controller
    window.addEventListener('pointermove', handlePointerMove, { signal: controller.signal })
    window.addEventListener('pointerup', endDrag, { signal: controller.signal })
  }, [disabled, handlePointerMove, endDrag])

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

  // Unmount-only: empty deps mean this never re-runs mid-drag to detach the
  // listeners out from under an in-progress drag.
  useEffect(() => () => dragAbortRef.current?.abort(), [])

  const loPercent = toPercent(valueLo)
  const hiPercent = toPercent(valueHi)
  const thumbSize = 16

  return (
    <div className={`select-none ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
      {/* Rail: the usable track, inset by half a thumb on each side so the
          extreme thumbs stay in bounds. Thumb centers and the fill are all
          positioned as percentages of THIS element, so they share one basis
          and always line up. The drag math also measures this element, so
          pointer travel maps 1:1 to value across the full range. */}
      <div
        ref={trackRef}
        className="relative h-5 cursor-pointer"
        style={{ marginInline: thumbSize / 2 }}
        onClick={handleTrackClick}
      >
        {/* Track */}
        <div className="absolute inset-y-0 left-0 right-0 flex items-center">
          <div className="w-full h-1 rounded-full bg-[var(--color-border)]" />
        </div>

        {/* Fill bar (draggable) - full-height hit area, thin visible line */}
        <div
          className="absolute inset-y-0 flex items-center cursor-ew-resize"
          style={{ left: `${loPercent}%`, right: `${100 - hiPercent}%` }}
          onPointerDown={(e) => { e.stopPropagation(); startDrag('fill', e) }}
        >
          <div className="w-full h-1 rounded-full" style={{ background: 'var(--color-accent)' }} />
        </div>

        {/* Lo thumb */}
        <div
          role="slider"
          aria-valuemin={min}
          aria-valuemax={valueHi - step}
          aria-valuenow={valueLo}
          tabIndex={disabled ? -1 : 0}
          className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--color-accent)] bg-[var(--color-bg)] cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:ring-offset-1"
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
          className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--color-accent)] bg-[var(--color-bg)] cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:ring-offset-1"
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

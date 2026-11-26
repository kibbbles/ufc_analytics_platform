// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, renderHook } from '@testing-library/react'
import { useClampPage } from './useClampPage'

afterEach(cleanup)

describe('useClampPage', () => {
  it('sends a page past the end to the last page', () => {
    const goTo = vi.fn()
    renderHook(() => useClampPage(9, 4, goTo))
    expect(goTo).toHaveBeenCalledExactlyOnceWith(4)
  })

  it('leaves a page inside the range alone', () => {
    const goTo = vi.fn()
    renderHook(() => useClampPage(4, 4, goTo))
    expect(goTo).not.toHaveBeenCalled()
  })

  it('waits until the total is known', () => {
    const goTo = vi.fn()
    const { rerender } = renderHook(({ total }) => useClampPage(9, total, goTo), {
      initialProps: { total: 0 },
    })
    expect(goTo).not.toHaveBeenCalled()
    rerender({ total: 3 })
    expect(goTo).toHaveBeenCalledExactlyOnceWith(3)
  })
})

// @vitest-environment jsdom
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it } from 'vitest'
import { act, cleanup, renderHook } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { useListParams } from './useListParams'

afterEach(cleanup)

function renderAt(url: string) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
  )
  return renderHook(() => useListParams(), { wrapper })
}

describe('useListParams', () => {
  it('reads the page and search from the URL', () => {
    const { result } = renderAt('/fighters?page=5&q=silva')
    expect(result.current.page).toBe(5)
    expect(result.current.query).toBe('silva')
  })

  it('goes back to page 1 when the search changes', () => {
    const { result } = renderAt('/fighters?page=5&q=silva')
    act(() => result.current.setQuery('jones'))
    expect(result.current.page).toBe(1)
    expect(result.current.query).toBe('jones')
  })

  it('keeps the search when the page changes', () => {
    const { result } = renderAt('/fighters?q=silva')
    act(() => result.current.setPage(3))
    expect(result.current.page).toBe(3)
    expect(result.current.query).toBe('silva')
  })
})

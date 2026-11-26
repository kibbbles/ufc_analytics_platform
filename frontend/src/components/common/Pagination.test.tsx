// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Pagination from './Pagination'

afterEach(cleanup)

function setup(page = 1, totalPages = 227) {
  const onPageChange = vi.fn()
  render(
    <Pagination
      page={page}
      totalPages={totalPages}
      onPrev={() => {}}
      onNext={() => {}}
      onPageChange={onPageChange}
    />,
  )
  const field = screen.getByRole('textbox', { name: 'Page number' }) as HTMLInputElement
  return { onPageChange, field, user: userEvent.setup() }
}

describe('Pagination page field', () => {
  it('jumps to a typed page on Enter', async () => {
    const { onPageChange, field, user } = setup()
    await user.click(field)
    await user.keyboard('50{Enter}')
    expect(onPageChange).toHaveBeenCalledExactlyOnceWith(50)
  })

  it('jumps when the field loses focus, which is how the iOS Done key commits', async () => {
    const { onPageChange, field, user } = setup()
    await user.click(field)
    await user.keyboard('27')
    await user.click(document.body)
    expect(onPageChange).toHaveBeenCalledExactlyOnceWith(27)
  })

  it('clamps a page past the end to the last page', async () => {
    const { onPageChange, field, user } = setup()
    await user.click(field)
    await user.keyboard('500{Enter}')
    expect(onPageChange).toHaveBeenCalledExactlyOnceWith(227)
  })

  it('clamps page 0 to the first page', async () => {
    const { onPageChange, field, user } = setup(5)
    await user.click(field)
    await user.keyboard('0{Enter}')
    expect(onPageChange).toHaveBeenCalledExactlyOnceWith(1)
  })

  it.each(['abc', '-3', '2.5', ' '])('ignores %j and shows the current page again', async typed => {
    const { onPageChange, field, user } = setup(4)
    await user.click(field)
    await user.keyboard(typed + '{Enter}')
    expect(onPageChange).not.toHaveBeenCalled()
    expect(field.value).toBe('4')
  })

  it('does not reload the page the user is already on', async () => {
    const { onPageChange, field, user } = setup(4)
    await user.click(field)
    await user.keyboard('4{Enter}')
    expect(onPageChange).not.toHaveBeenCalled()
  })

  it('puts the current page back on Escape', async () => {
    const { onPageChange, field, user } = setup(4)
    await user.click(field)
    await user.keyboard('90{Escape}')
    expect(onPageChange).not.toHaveBeenCalled()
    expect(field.value).toBe('4')
  })

  it('asks for the number pad with a Go key', () => {
    const { field } = setup()
    expect(field.inputMode).toBe('numeric')
    expect(field.getAttribute('enterkeyhint')).toBe('go')
  })

  it('disables Next on the last page', () => {
    setup(227)
    expect(screen.getByRole('button', { name: 'Next page' })).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: 'Previous page' })).toHaveProperty('disabled', false)
  })
})

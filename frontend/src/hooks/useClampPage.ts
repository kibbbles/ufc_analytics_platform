import { useEffect, useRef } from 'react'

/**
 * Sends a page number past the end of the list to the last page: an old link,
 * a filter that leaves fewer pages, or the API shrinking between loads.
 * Does nothing until the total is known (0 means not loaded or no results).
 */
export function useClampPage(page: number, totalPages: number, goTo: (page: number) => void) {
  const goToRef = useRef(goTo)
  useEffect(() => {
    goToRef.current = goTo
  })

  useEffect(() => {
    if (totalPages > 0 && page > totalPages) goToRef.current(totalPages)
  }, [page, totalPages])
}

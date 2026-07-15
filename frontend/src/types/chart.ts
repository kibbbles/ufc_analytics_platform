/** One entry in a Recharts tooltip payload. */
export interface ChartTooltipEntry {
  dataKey?: string | number
  name?: string | number
  value?: number | string
  color?: string
  fill?: string
  payload?: Record<string, unknown>
}

/** Props Recharts passes to a custom tooltip `content` function or component. */
export interface ChartTooltipProps {
  active?: boolean
  label?: string | number
  payload?: ChartTooltipEntry[]
}

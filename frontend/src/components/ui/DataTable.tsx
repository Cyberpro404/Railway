import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface Column<T> {
  key: keyof T | string
  label: string
  width?: string
  render?: (value: unknown, item: T) => ReactNode
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyExtractor: (item: T) => string | number
  className?: string
  striped?: boolean
  hoverable?: boolean
}

export default function DataTable<T extends Record<string, any>>({
  columns,
  data,
  keyExtractor,
  className,
  striped = true,
  hoverable = true,
}: DataTableProps<T>) {
  return (
    <div className={cn('overflow-x-auto rounded-lg border border-border/50', className)}>
      <table className="w-full">
        <thead>
          <tr className="border-b border-border/50 bg-background/50 backdrop-blur-sm">
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className={cn(
                  'px-6 py-3 text-left text-sm font-semibold text-text-muted',
                  'uppercase tracking-wider',
                  col.width && `w-${col.width}`
                )}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/30">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-6 py-8 text-center text-text-muted">
                No data available
              </td>
            </tr>
          ) : (
            data.map((item, idx) => (
              <tr
                key={keyExtractor(item)}
                className={cn(
                  'transition-all duration-200',
                  striped && idx % 2 === 0 && 'bg-background/30',
                  hoverable && 'hover:bg-primary/5'
                )}
              >
                {columns.map((col) => (
                  <td
                    key={`${keyExtractor(item)}-${String(col.key)}`}
                    className="px-6 py-4 text-sm text-text"
                  >
                    {col.render
                      ? col.render((item as any)[col.key], item)
                      : ((item as any)[col.key] as ReactNode)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

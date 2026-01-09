import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${hours}h ${minutes}m ${secs}s`
}

export function formatNumber(value: number, decimals: number = 2): string {
  return value.toFixed(decimals)
}

export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'good':
    case 'normal':
      return 'text-success'
    case 'warning':
    case 'satisfactory':
      return 'text-warning'
    case 'critical':
    case 'unacceptable':
      return 'text-critical'
    default:
      return 'text-text-muted'
  }
}

export function exportToCSV(data: any[], filename: string) {
  if (data.length === 0) return
  
  const headers = Object.keys(data[0])
  const csv = [
    headers.join(','),
    ...data.map(row => headers.map(header => {
      const value = row[header]
      return typeof value === 'string' ? `"${value}"` : value
    }).join(','))
  ].join('\n')
  
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}


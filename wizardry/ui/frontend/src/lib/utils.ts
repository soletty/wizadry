import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)

  if (diffInHours < 1) {
    const diffInMinutes = Math.floor(diffInHours * 60)
    return `${diffInMinutes} minute${diffInMinutes !== 1 ? 's' : ''} ago`
  } else if (diffInHours < 24) {
    const hours = Math.floor(diffInHours)
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`
  } else if (diffInHours < 24 * 7) {
    const days = Math.floor(diffInHours / 24)
    return `${days} day${days !== 1 ? 's' : ''} ago`
  } else {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
}

export function formatDuration(startDate: string, endDate?: string): string {
  const start = new Date(startDate)
  const end = endDate ? new Date(endDate) : new Date()
  const diffInMs = end.getTime() - start.getTime()
  
  const diffInMinutes = Math.floor(diffInMs / (1000 * 60))
  const diffInHours = Math.floor(diffInMinutes / 60)
  const diffInDays = Math.floor(diffInHours / 24)

  if (diffInDays > 0) {
    const remainingHours = diffInHours % 24
    const remainingMinutes = diffInMinutes % 60
    return `${diffInDays}d ${remainingHours}h ${remainingMinutes}m`
  } else if (diffInHours > 0) {
    const remainingMinutes = diffInMinutes % 60
    return `${diffInHours}h ${remainingMinutes}m`
  } else {
    return `${diffInMinutes}m`
  }
}

export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'text-green-600'
    case 'failed':
      return 'text-red-600'
    case 'in_progress':
      return 'text-blue-600'
    case 'terminated':
      return 'text-gray-600'
    default:
      return 'text-gray-500'
  }
}
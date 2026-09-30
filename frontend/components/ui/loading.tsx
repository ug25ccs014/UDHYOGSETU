import { Loader2 } from 'lucide-react'

export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-gray-600">
      <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      <p className="mt-4 text-sm">{message}</p>
    </div>
  )
}
import { Metadata } from 'next'
import { Suspense } from 'react'
import { LoginForm } from '@/components/auth'

export const metadata: Metadata = {
  title: 'Sign In | ekona Content Creation Hub',
  description: 'Access your ekona Content Creation Hub to start creating professional presentations with advanced AI agents powered by Swiss expertise',
}

function LoginFallback() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="w-full max-w-lg">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginForm />
    </Suspense>
  )
}
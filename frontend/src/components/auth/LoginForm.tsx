'use client'

import { Loader2 } from 'lucide-react'
import Image from 'next/image'
import { useRouter, useSearchParams } from 'next/navigation'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'

export function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { signInWithOAuth, isLoading } = useSupabaseAuth()

  // Handle URL error parameter
  const error = searchParams.get('error')

  const handleAzureSignIn = async () => {
    const redirectTo = searchParams.get('redirectTo')
    const result = await signInWithOAuth('azure', redirectTo || '/dashboard')

    if (!result.success && result.error) {
      console.error('Azure AD sign in failed:', result.error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="w-full max-w-lg">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12">

          {/* Logo and Branding */}
          <div className="text-center mb-10">
            <Image
              src="/ekona_logo_transparent.png"
              alt="ekona"
              width={256}
              height={256}
              className="mx-auto mb-6"
              priority
            />
            <div className="space-y-2 mb-8">
              <p className="text-2xl font-bold text-gray-700">CONTENT CREATION HUB</p>
            </div>

            <h2 className="text-xl font-medium text-gray-900">Welcome back</h2>
          </div>

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertDescription>
                {decodeURIComponent(error)}
              </AlertDescription>
            </Alert>
          )}

          {/* Sign In Button */}
          <Button
            onClick={handleAzureSignIn}
            disabled={isLoading}
            className="w-full h-14 bg-red-600 hover:bg-red-700 text-white font-medium text-base"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Connecting to Azure AD...
              </>
            ) : (
              'Sign in with Azure AD'
            )}
          </Button>

          {/* Security note */}
          <p className="text-center text-xs text-gray-400 mt-6">
            Secured by Microsoft Azure Active Directory
          </p>
        </div>

        {/* Footer */}
        <div className="text-center mt-8">
          <p className="text-sm text-gray-400">
            © 2025 ekona AG | All rights reserved | Made in Switzerland <span className="inline-block align-middle mx-1" title="Swiss Flag" aria-label="Swiss Flag">🇨🇭</span> 
          </p>
        </div>
      </div>
    </div>
  )
}
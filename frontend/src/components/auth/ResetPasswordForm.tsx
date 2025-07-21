'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import Link from 'next/link'
import { Loader2, Mail, ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'

import { useSupabaseAuth } from '@/hooks/useSupabaseAuth'
import { resetPasswordSchema, type ResetPasswordFormData } from '@/schemas/auth'

export function ResetPasswordForm() {
  const [resetSent, setResetSent] = useState(false)
  const { resetPassword, isLoading } = useSupabaseAuth()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
    getValues
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema)
  })

  const onSubmit = async (data: ResetPasswordFormData) => {
    const result = await resetPassword(data.email)
    
    if (result.success) {
      setResetSent(true)
    } else if (result.error) {
      setError('root', {
        message: (result.error as any)?.message || 'An error occurred while sending reset email'
      })
    }
  }

  const isFormLoading = isLoading || isSubmitting

  if (resetSent) {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
            <Mail className="h-6 w-6 text-blue-600" />
          </div>
          <CardTitle className="text-2xl font-bold text-ekona-teal">
            Check your email
          </CardTitle>
          <CardDescription>
            We&apos;ve sent a password reset link to <strong>{getValues('email')}</strong>
          </CardDescription>
        </CardHeader>
        
        <CardContent className="text-center">
          <p className="text-sm text-muted-foreground mb-4">
            If you don&apos;t see the email in your inbox, check your spam folder.
          </p>
          
          <Button
            variant="outline"
            onClick={() => setResetSent(false)}
            className="w-full"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Try different email
          </Button>
        </CardContent>

        <CardFooter>
          <div className="text-center text-sm text-muted-foreground w-full">
            Remember your password?{' '}
            <Link
              href="/auth/login"
              className="text-ekona-teal hover:text-ekona-blue font-medium transition-colors"
            >
              Sign in
            </Link>
          </div>
        </CardFooter>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="space-y-1 text-center">
        <CardTitle className="text-2xl font-bold text-ekona-teal">
          Reset your password
        </CardTitle>
        <CardDescription>
          Enter your email address and we&apos;ll send you a link to reset your password.
        </CardDescription>
      </CardHeader>
      
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {errors.root && (
            <Alert variant="destructive">
              <AlertDescription>{errors.root.message}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="Enter your email address"
              disabled={isFormLoading}
              {...register('email')}
              className={errors.email ? 'border-destructive' : ''}
            />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button
            type="submit"
            className="w-full bg-ekona-teal hover:bg-ekona-blue"
            disabled={isFormLoading}
          >
            {isFormLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending reset link...
              </>
            ) : (
              'Send reset link'
            )}
          </Button>

          <div className="text-center text-sm text-muted-foreground">
            Remember your password?{' '}
            <Link
              href="/auth/login"
              className="text-ekona-teal hover:text-ekona-blue font-medium transition-colors"
            >
              Sign in
            </Link>
          </div>
        </CardFooter>
      </form>
    </Card>
  )
}
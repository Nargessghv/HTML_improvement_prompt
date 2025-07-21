import { Metadata } from 'next'
import { ResetPasswordForm } from '@/components/auth'

export const metadata: Metadata = {
  title: 'Reset Password | Ekona Slide Creator',
  description: 'Reset your Ekona Slide Creator account password',
}

export default function ResetPasswordPage() {
  return <ResetPasswordForm />
}
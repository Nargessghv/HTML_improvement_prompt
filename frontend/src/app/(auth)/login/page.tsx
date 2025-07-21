import { Metadata } from 'next'
import { LoginForm } from '@/components/auth'

export const metadata: Metadata = {
  title: 'Sign In | Ekona Slide Creator',
  description: 'Sign in to your Ekona Slide Creator account to start creating AI-powered presentations',
}

export default function LoginPage() {
  return <LoginForm />
}
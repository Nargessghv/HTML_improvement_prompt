import { Metadata } from 'next'
import { LoginForm } from '@/components/auth'

export const metadata: Metadata = {
  title: 'Sign In | ekona Content Creation Hub',
  description: 'Access your ekona Content Creation Hub to start creating professional presentations with advanced AI agents powered by Swiss expertise',
}

export default function LoginPage() {
  return <LoginForm />
}
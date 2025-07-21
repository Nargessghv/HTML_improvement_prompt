import { Metadata } from 'next'
import { RegisterForm } from '@/components/auth'

export const metadata: Metadata = {
  title: 'Sign Up | Ekona Slide Creator',
  description: 'Create your Ekona Slide Creator account to start building AI-powered presentations',
}

export default function RegisterPage() {
  return <RegisterForm />
}
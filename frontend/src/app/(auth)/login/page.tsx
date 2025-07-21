import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Login | Ekona Slide Creator',
  description: 'Sign in to your Ekona Slide Creator account',
}

export default function LoginPage() {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
          Sign in to your account
        </h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Welcome back to Ekona Slide Creator
        </p>
      </div>
      
      <div className="rounded-lg bg-white dark:bg-gray-800 px-6 py-8 shadow-sm">
        <div className="space-y-4">
          <p className="text-center text-gray-600 dark:text-gray-400">
            Login form will be implemented here
          </p>
          
          {/* TODO: Implement LoginForm component */}
          {/* <LoginForm /> */}
        </div>
      </div>
    </div>
  )
}
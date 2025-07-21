import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Register | Ekona Slide Creator',
  description: 'Create your Ekona Slide Creator account',
}

export default function RegisterPage() {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
          Create your account
        </h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Join Ekona Slide Creator and start creating amazing presentations
        </p>
      </div>
      
      <div className="rounded-lg bg-white dark:bg-gray-800 px-6 py-8 shadow-sm">
        <div className="space-y-4">
          <p className="text-center text-gray-600 dark:text-gray-400">
            Registration form will be implemented here
          </p>
          
          {/* TODO: Implement RegisterForm component */}
          {/* <RegisterForm /> */}
        </div>
      </div>
    </div>
  )
}
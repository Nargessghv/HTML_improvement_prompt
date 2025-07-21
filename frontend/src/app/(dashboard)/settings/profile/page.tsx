import { Metadata } from 'next'
import { ProfileForm } from '@/components/auth'

export const metadata: Metadata = {
  title: 'Profile Settings - Ekona Slide Creator',
  description: 'Manage your profile information and preferences'
}

export default function ProfilePage() {
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Profile Settings</h1>
          <p className="text-muted-foreground mt-2">
            Manage your profile information, avatar, and account preferences
          </p>
        </div>
        
        <div className="flex justify-center">
          <ProfileForm />
        </div>
      </div>
    </div>
  )
}
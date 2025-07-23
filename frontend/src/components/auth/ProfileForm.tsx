'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { profileSchema, type ProfileFormData } from '@/schemas/auth'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { User, Upload, Loader2 } from 'lucide-react'

interface ProfileFormProps {
  onSuccess?: () => void
}

export function ProfileForm({ onSuccess }: ProfileFormProps) {
  const { user, updateProfile } = useSupabaseAuth()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.user_metadata?.full_name || '',
      display_name: user?.user_metadata?.display_name || '',
      bio: user?.user_metadata?.bio || '',
      avatar_url: user?.user_metadata?.avatar_url || ''
    }
  })

  const avatarUrl = watch('avatar_url')

  const onSubmit = async (data: ProfileFormData) => {
    setIsSubmitting(true)
    setError(null)
    setSuccess(null)

    try {
      const result = await updateProfile({
        full_name: data.full_name,
        display_name: data.display_name || undefined,
        bio: data.bio || undefined,
        avatar_url: data.avatar_url || undefined
      })

      if (result.success) {
        setSuccess('Profile updated successfully!')
        onSuccess?.()
      } else {
        setError((result.error as any)?.message || 'Failed to update profile')
      }
    } catch (err) {
      console.error('Profile update error:', err)
      setError('An unexpected error occurred')
    } finally {
      setIsSubmitting(false)
    }
  }

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <User className="h-5 w-5" />
          Profile Settings
        </CardTitle>
        <CardDescription>
          Update your profile information and preferences
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        
        {success && (
          <Alert className="border-green-200 bg-green-50 text-green-800">
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Avatar Section */}
          <div className="flex items-center gap-6">
            <Avatar className="h-20 w-20">
              <AvatarImage 
                src={avatarUrl} 
                alt={user?.user_metadata?.full_name || 'Profile'} 
              />
              <AvatarFallback className="text-lg">
                {user?.user_metadata?.full_name 
                  ? getInitials(user.user_metadata.full_name)
                  : 'UN'
                }
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <Label htmlFor="avatar_url">Avatar URL</Label>
              <div className="flex gap-2 mt-1">
                <Input
                  id="avatar_url"
                  type="url"
                  placeholder="https://example.com/avatar.jpg"
                  {...register('avatar_url')}
                />
                <Button type="button" variant="outline" size="icon">
                  <Upload className="h-4 w-4" />
                </Button>
              </div>
              {errors.avatar_url && (
                <p className="text-sm text-red-600 mt-1">
                  {errors.avatar_url.message}
                </p>
              )}
            </div>
          </div>

          {/* Basic Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="full_name">
                Full Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="full_name"
                {...register('full_name')}
                className={errors.full_name ? 'border-red-500' : ''}
              />
              {errors.full_name && (
                <p className="text-sm text-red-600 mt-1">
                  {errors.full_name.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="display_name">Display Name</Label>
              <Input
                id="display_name"
                placeholder="Optional display name"
                {...register('display_name')}
                className={errors.display_name ? 'border-red-500' : ''}
              />
              {errors.display_name && (
                <p className="text-sm text-red-600 mt-1">
                  {errors.display_name.message}
                </p>
              )}
            </div>
          </div>

          {/* Bio */}
          <div>
            <Label htmlFor="bio">Bio</Label>
            <ScrollArea className="h-[120px]">
              <Textarea
                id="bio"
                placeholder="Tell us about yourself..."
                className={`min-h-[120px] max-h-none resize-none border-0 shadow-none focus-visible:ring-0 ${errors.bio ? 'border-red-500' : ''}`}
                {...register('bio')}
              />
            </ScrollArea>
            {errors.bio && (
              <p className="text-sm text-red-600 mt-1">
                {errors.bio.message}
              </p>
            )}
          </div>

          {/* Email (Read-only) */}
          <div>
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              value={user?.email || ''}
              disabled
              className="bg-gray-50"
            />
            <p className="text-sm text-gray-600 mt-1">
              Email cannot be changed here. Contact support if you need to update your email.
            </p>
          </div>

          {/* Submit Button */}
          <Button 
            type="submit" 
            disabled={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Updating Profile...
              </>
            ) : (
              'Update Profile'
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
import { createClient } from '@supabase/supabase-js'
import { Database } from '@/lib/supabase'
import { env, serverEnv } from '@/lib/env'

// Admin client for server-side operations that bypass RLS
export function createAdminClient() {
  if (typeof window !== 'undefined') {
    throw new Error('Admin client should only be used on the server side')
  }

  if (!serverEnv?.SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error(
      'SUPABASE_SERVICE_ROLE_KEY is required for admin operations.\n' +
      'This key should be kept secret and only used on the server side.'
    )
  }

  return createClient<Database>(
    env.NEXT_PUBLIC_SUPABASE_URL,
    serverEnv.SUPABASE_SERVICE_ROLE_KEY,
    {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    }
  )
}

// Helper functions for common admin operations
export class SupabaseAdmin {
  private client = createAdminClient()

  // User management
  async createUser(email: string, password: string, metadata?: Record<string, unknown>) {
    const { data, error } = await this.client.auth.admin.createUser({
      email,
      password,
      user_metadata: metadata,
    })

    if (error) throw error
    return data
  }

  async deleteUser(userId: string) {
    const { error } = await this.client.auth.admin.deleteUser(userId)
    if (error) throw error
  }

  async updateUserMetadata(userId: string, metadata: Record<string, unknown>) {
    const { data, error } = await this.client.auth.admin.updateUserById(userId, {
      user_metadata: metadata,
    })

    if (error) throw error
    return data
  }

  // File management
  async uploadFile(bucket: string, path: string, file: File | Buffer) {
    const { data, error } = await this.client.storage
      .from(bucket)
      .upload(path, file, {
        upsert: true,
      })

    if (error) throw error
    return data
  }

  async deleteFile(bucket: string, path: string) {
    const { error } = await this.client.storage
      .from(bucket)
      .remove([path])

    if (error) throw error
  }

  async getFileUrl(bucket: string, path: string) {
    const { data } = this.client.storage
      .from(bucket)
      .getPublicUrl(path)

    return data.publicUrl
  }

  // Database operations (bypasses RLS)
  async insertData<T = unknown>(table: string, data: T) {
    const { data: result, error } = await this.client
      .from(table)
      .insert(data as never)
      .select()

    if (error) throw error
    return result
  }

  async updateData<T = unknown>(table: string, id: string, data: T) {
    const { data: result, error } = await this.client
      .from(table)
      .update(data as never)
      .eq('id', id)
      .select()

    if (error) throw error
    return result
  }

  async deleteData(table: string, id: string) {
    const { error } = await this.client
      .from(table)
      .delete()
      .eq('id', id)

    if (error) throw error
  }

  // Health check
  async healthCheck() {
    try {
      const { error } = await this.client
        .from('projects')
        .select('id')
        .limit(1)

      return { healthy: !error, error: error?.message }
    } catch (error) {
      return { 
        healthy: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      }
    }
  }
}

// Export singleton instance
export const supabaseAdmin = new SupabaseAdmin()
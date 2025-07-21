import { NextResponse } from 'next/server'
import { env } from '@/lib/env'

export async function GET() {
  try {
    const health = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      environment: env.NODE_ENV,
      version: process.env.npm_package_version || '1.0.0',
      services: {
        supabase: {
          configured: !!env.NEXT_PUBLIC_SUPABASE_URL && !!env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
          url: env.NEXT_PUBLIC_SUPABASE_URL ? 'configured' : 'missing',
        },
        api: {
          configured: !!env.NEXT_PUBLIC_API_URL,
          url: env.NEXT_PUBLIC_API_URL ? 'configured' : 'missing',
        },
      },
      features: {
        realtime: env.NEXT_PUBLIC_ENABLE_REALTIME,
        aiChat: env.NEXT_PUBLIC_ENABLE_AI_CHAT,
        export: env.NEXT_PUBLIC_ENABLE_EXPORT,
        collaboration: env.NEXT_PUBLIC_ENABLE_COLLABORATION,
      },
    }

    return NextResponse.json(health, { status: 200 })
  } catch (error) {
    return NextResponse.json(
      {
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
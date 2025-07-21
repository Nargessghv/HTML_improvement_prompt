# Ekona Slide Creator - Frontend

This is the frontend application for the Ekona AI-Powered PowerPoint Slide Creator system. Built with [Next.js](https://nextjs.org) and bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **UI**: Tailwind CSS + shadcn/ui components
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **State Management**: Zustand
- **Real-time**: Supabase Realtime subscriptions

## Prerequisites

Before running this application, you need:

1. **Supabase Project**: Set up a Supabase project with the required database schema
2. **Environment Configuration**: Configure environment variables (see setup below)
3. **Backend API**: The Python backend API should be running (typically on port 8000)

## Environment Setup

1. **Copy environment template:**
   ```bash
   cp .env.local.example .env.local
   ```

2. **Configure your environment variables** in `.env.local`:
   - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anonymous key
   - `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)

3. **For detailed environment setup**, see [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md)

## Getting Started

After setting up your environment, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Health Check

Visit [http://localhost:3000/health](http://localhost:3000/health) to verify your environment configuration and check service connectivity.

## Project Structure

```
src/
├── app/                 # Next.js app directory
├── components/          # Reusable UI components
├── hooks/              # Custom React hooks
├── lib/                # Utility libraries
│   ├── supabase/       # Supabase client configuration
│   ├── env.ts          # Environment validation
│   └── utils.ts        # Utility functions
└── types/              # TypeScript type definitions
```

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

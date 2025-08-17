'use client'

import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useSupabaseAuth } from "@/hooks/useSupabaseAuthSimple";
import { NewProjectModal } from "@/components/modals/NewProjectModal";
import Image from "next/image";
import Link from "next/link";
import { useState, useEffect } from "react";
import { Loader2, ArrowRight, Zap, Brain, BarChart3, Sparkles } from "lucide-react";

export default function Home() {
  const { isAuthenticated, isLoading, user } = useSupabaseAuth();
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [presentationTopic, setPresentationTopic] = useState("");

  // Redirect to login if not authenticated (must be before any conditional returns)
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      window.location.href = '/login'
    }
  }, [isLoading, isAuthenticated])

  // If loading, show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  // If authenticated, show authenticated experience
  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container max-w-6xl mx-auto px-4 py-8">
          {/* Header with auth info */}
          <header className="text-center mb-16">
            <div className="flex items-center justify-between mb-8">
              <Image
                src="/ekona_logo_transparent.png"
                alt="Ekona Logo"
                width={120}
                height={40}
                className="h-10 w-auto"
                priority
              />
              <div className="flex items-center gap-4">
                <span className="text-sm text-muted-foreground">
                  Welcome back, {user.email?.split('@')[0]}
                </span>
                <Link href="/dashboard">
                  <Button variant="outline" size="sm">
                    Dashboard
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </Link>
              </div>
            </div>
            <h1 className="text-5xl md:text-6xl font-light tracking-tight text-foreground mb-6">
              Ready to Create?
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
              Your AI-powered presentation studio is ready. Start a new project or continue where you left off.
            </p>
          </header>

          {/* Quick Start - Functional */}
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 mb-16">
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-subtle hover:shadow-card-hover transition-all duration-300">
              <CardHeader>
                <CardTitle className="text-xl font-light flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Quick Start
                </CardTitle>
                <CardDescription className="text-muted-foreground">
                  Create a new presentation instantly
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <Input 
                  placeholder="Enter your presentation topic..." 
                  className="border-border/50 focus:border-primary/50"
                  value={presentationTopic}
                  onChange={(e) => setPresentationTopic(e.target.value)}
                />
                <Button 
                  className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-light"
                  onClick={() => {
                    if (presentationTopic.trim()) {
                      setShowNewProjectModal(true)
                    }
                  }}
                  disabled={!presentationTopic.trim()}
                >
                  Create Presentation
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-subtle hover:shadow-card-hover transition-all duration-300">
              <CardHeader>
                <CardTitle className="text-xl font-light flex items-center gap-2">
                  <Brain className="h-5 w-5 text-primary" />
                  AI Agents
                </CardTitle>
                <CardDescription className="text-muted-foreground">
                  6 specialized agents work together to create your slides
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-muted-foreground">
                  <li className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
                    <span>Layout Analysis</span>
                  </li>
                  <li className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
                    <span>Content Generation</span>
                  </li>
                  <li className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
                    <span>HTML Visualizations</span>
                  </li>
                  <li className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
                    <span>Quality Review</span>
                  </li>
                </ul>
                <div className="mt-4">
                  <Link href="/dashboard">
                    <Button variant="outline" size="sm" className="w-full">
                      View Workflow
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-subtle hover:shadow-card-hover transition-all duration-300">
              <CardHeader>
                <CardTitle className="text-xl font-light flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-primary" />
                  Your Projects
                </CardTitle>
                <CardDescription className="text-muted-foreground">
                  Access and manage your presentations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="text-center py-4">
                    <div className="text-2xl font-bold text-foreground mb-2">Ready</div>
                    <p className="text-sm text-muted-foreground">Your presentation studio</p>
                  </div>
                  <Link href="/dashboard">
                    <Button variant="outline" className="w-full">
                      Go to Dashboard
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="text-center space-y-4">
            <div className="flex justify-center gap-4">
              <Link href="/projects">
                <Button size="lg" className="font-light">
                  View All Projects
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
              <Button variant="outline" size="lg" className="font-light border-border/50 hover:bg-secondary/50">
                View Documentation
              </Button>
            </div>
            
            <div className="flex items-center justify-center gap-3 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <div className="swiss-flag"></div>
                <span>Swiss AI Expertise</span>
              </div>
            </div>
          </div>

          {/* New Project Modal */}
          <NewProjectModal 
            open={showNewProjectModal}
            onOpenChange={setShowNewProjectModal}
            initialTopic={presentationTopic}
          />
        </div>
      </div>
    );
  }

  // If not authenticated, show loading while redirecting
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Redirecting to sign in...</p>
        </div>
      </div>
    )
  }

  // This return should never be reached since authenticated users are handled above
  return null;
}
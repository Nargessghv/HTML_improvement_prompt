import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import Image from "next/image";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container max-w-6xl mx-auto px-4 py-8">
        <header className="text-center mb-16">
          <div className="flex items-center justify-center mb-8">
            <Image
              src="/ekona_logo_transparent.png"
              alt="Ekona Logo"
              width={120}
              height={40}
              className="h-10 w-auto"
              priority
            />
          </div>
          <h1 className="text-5xl md:text-6xl font-light tracking-tight text-foreground mb-6">
            AI-Powered Slide Creator
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Create professional presentations with advanced AI agents powered by Swiss AI expertise
          </p>
        </header>

        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 mb-16">
          <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-subtle hover:shadow-card-hover transition-all duration-300">
            <CardHeader>
              <CardTitle className="text-xl font-light">Quick Start</CardTitle>
              <CardDescription className="text-muted-foreground">
                Get started with creating your first presentation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <Input 
                placeholder="Enter your presentation topic..." 
                className="border-border/50 focus:border-primary/50"
              />
              <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-light">
                Create Presentation
              </Button>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-subtle hover:shadow-card-hover transition-all duration-300">
            <CardHeader>
              <CardTitle className="text-xl font-light">AI Agents</CardTitle>
              <CardDescription className="text-muted-foreground">
                7 specialized agents work together to create your slides
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3 text-muted-foreground">
                <li className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-primary rounded-full"></div>
                  <span>Layout Analysis</span>
                </li>
                <li className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-primary rounded-full"></div>
                  <span>Content Generation</span>
                </li>
                <li className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-primary rounded-full"></div>
                  <span>HTML Visualizations</span>
                </li>
                <li className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-primary rounded-full"></div>
                  <span>Quality Review</span>
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-subtle hover:shadow-card-hover transition-all duration-300">
            <CardHeader>
              <CardTitle className="text-xl font-light">Real-time Progress</CardTitle>
              <CardDescription className="text-muted-foreground">
                Track your presentation generation in real-time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary w-1/3 rounded-full transition-all duration-500"></div>
                </div>
                <p className="text-sm text-muted-foreground font-light">33% Complete</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="text-center space-y-4">
          <Button variant="outline" size="lg" className="font-light border-border/50 hover:bg-secondary/50">
            View Documentation
          </Button>
          
          <div className="flex items-center justify-center gap-3 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="swiss-flag"></div>
              <span>Swiss AI Expertise</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

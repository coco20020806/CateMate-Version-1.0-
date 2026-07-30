import React from "react";
import { Link, useLocation } from "wouter";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  PlaySquare,
  Database,
  BoxSelect,
  Settings,
  PlusCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface NavItemProps {
  href: string;
  icon: React.ElementType;
  children: React.ReactNode;
}

function NavItem({ href, icon: Icon, children }: NavItemProps) {
  const [location] = useLocation();
  const isActive = location === href || (href !== "/" && location.startsWith(href));

  return (
    <Link href={href} className={cn(
      "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
      isActive
        ? "bg-primary/10 text-primary"
        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
    )}>
      <Icon className="h-4 w-4" />
      {children}
    </Link>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col md:flex-row">
      <aside className="w-full md:w-64 border-r border-border bg-card flex flex-col flex-shrink-0">
        <div className="h-16 flex items-center px-6 border-b border-border">
          <div className="flex items-center gap-2 text-primary font-bold text-lg tracking-tight">
            <BoxSelect className="h-6 w-6" />
            CateMate
          </div>
        </div>
        <div className="p-4 flex flex-col gap-1 flex-1">
          <NavItem href="/" icon={LayoutDashboard}>Dashboard</NavItem>
          <NavItem href="/runs" icon={PlaySquare}>Run History</NavItem>
          <NavItem href="/datasources" icon={Database}>Data Sources</NavItem>
          <NavItem href="/modules" icon={BoxSelect}>Module Catalog</NavItem>
          <NavItem href="/settings" icon={Settings}>Settings</NavItem>
          
          <div className="mt-8">
            <Button asChild className="w-full justify-start gap-2" variant="default">
              <Link href="/runs/new">
                <PlusCircle className="h-4 w-4" />
                New Analysis
              </Link>
            </Button>
          </div>
        </div>
      </aside>
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </main>
    </div>
  );
}

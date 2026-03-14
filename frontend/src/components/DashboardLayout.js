import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { LogOut, Activity, User, Database } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const DashboardLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <div className="flex items-center justify-between px-6 h-16">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
                <Activity className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h1 className="text-lg font-semibold">RCA Platform</h1>
                <p className="text-xs text-muted-foreground">Root Cause Analysis</p>
              </div>
            </div>
            
            <div className="hidden md:flex items-center gap-2 ml-6 px-3 py-1.5 rounded-md bg-accent/10 border border-accent/20">
              <Database className="w-3.5 h-3.5 text-accent" />
              <span className="text-xs font-medium text-accent">System Online</span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-secondary border border-border">
              <User className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium" data-testid="user-name">{user?.full_name}</span>
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={handleLogout}
              data-testid="logout-button"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="p-6">
        {children}
      </main>
    </div>
  );
};

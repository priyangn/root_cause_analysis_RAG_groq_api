import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';
import { toast } from 'sonner';
import { Activity } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success('Login successful');
      navigate('/dashboard', { replace: true });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background via-background to-secondary/10">
      <div className="absolute inset-0 grid-bg opacity-50" />
      
      <Card className="relative z-10 w-full max-w-md p-8 data-card backdrop-blur-sm bg-card/95">
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <Activity className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">CauseSense AI</h1>
          </div>
          <p className="text-sm text-muted-foreground">AI Root Cause Intelligence Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5" data-testid="login-form">
          <div>
            <label className="metric-label block mb-2">Email Address</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="engineer@company.com"
              required
              data-testid="login-email-input"
              className="h-10"
            />
          </div>

          <div>
            <label className="metric-label block mb-2">Password</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              data-testid="login-password-input"
              className="h-10"
            />
          </div>

          <Button 
            type="submit" 
            className="w-full h-10 font-medium" 
            disabled={loading}
            data-testid="login-submit-button"
          >
            {loading ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                <span>Signing in...</span>
              </div>
            ) : 'Sign In'}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary hover:underline font-medium" data-testid="register-link">
              Create account
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}

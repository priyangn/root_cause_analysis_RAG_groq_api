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
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        backgroundImage: 'url(https://images.unsplash.com/photo-1771013304380-dfaf9f928de6?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDN8MHwxfHNlYXJjaHw0fHxhYnN0cmFjdCUyMGN5YmVyJTIwZGF0YSUyMHZpc3VhbGl6YXRpb24lMjB0ZWNobm9sb2d5JTIwYmFja2dyb3VuZHxlbnwwfHx8fDE3NzM1MTE1ODR8MA&ixlib=rb-4.1.0&q=85)',
        backgroundSize: 'cover',
        backgroundPosition: 'center'
      }}
    >
      <div className="absolute inset-0 bg-black/70" />
      
      <Card className="relative z-10 w-full max-w-md p-8 card-industrial">
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-10 h-10 text-primary" />
            <h1 className="text-3xl font-bold font-heading tracking-tight text-gradient">RCA PLATFORM</h1>
          </div>
          <p className="text-muted-foreground text-sm font-mono uppercase tracking-wider">Machine Failure Analysis</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-2">Email</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="engineer@company.com"
              required
              data-testid="login-email-input"
              className="font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-2">Password</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              data-testid="login-password-input"
              className="font-mono"
            />
          </div>

          <Button 
            type="submit" 
            className="w-full rounded-sm font-medium tracking-wide uppercase h-11" 
            disabled={loading}
            data-testid="login-submit-button"
          >
            {loading ? 'Authenticating...' : 'Login'}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary hover:underline font-medium" data-testid="register-link">
              Register here
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}
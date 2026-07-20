import React, { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';
import GoogleSignInButton from '../components/GoogleSignInButton';
import { toast } from 'sonner';
import { Activity } from 'lucide-react';

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: ''
  });
  const [loading, setLoading] = useState(false);
  const { register, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(formData.email, formData.password, formData.full_name);
      toast.success('Registration successful');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = useCallback(async (credential) => {
    setLoading(true);
    try {
      await loginWithGoogle(credential);
      toast.success('Signed in with Google');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Google sign-in failed');
    } finally {
      setLoading(false);
    }
  }, [loginWithGoogle, navigate]);

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
            <h1 className="text-3xl font-bold font-heading tracking-tight text-gradient">CauseSense AI</h1>
          </div>
          <p className="text-muted-foreground text-sm font-mono uppercase tracking-wider">AI Root Cause Intelligence</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6" data-testid="register-form">
          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-2">Full Name</label>
            <Input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({...formData, full_name: e.target.value})}
              placeholder="John Doe"
              required
              data-testid="register-name-input"
              className="font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-2">Email</label>
            <Input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              placeholder="engineer@company.com"
              required
              data-testid="register-email-input"
              className="font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-2">Password</label>
            <Input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              placeholder="••••••••"
              required
              data-testid="register-password-input"
              className="font-mono"
            />
          </div>

          <Button 
            type="submit" 
            className="w-full rounded-sm font-medium tracking-wide uppercase h-11" 
            disabled={loading}
            data-testid="register-submit-button"
          >
            {loading ? 'Creating Account...' : 'Register'}
          </Button>
        </form>

        <div className="mt-5">
          <GoogleSignInButton onCredential={handleGoogle} disabled={loading} />
        </div>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="text-primary hover:underline font-medium" data-testid="login-link">
              Login here
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}
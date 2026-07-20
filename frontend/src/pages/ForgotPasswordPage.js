import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';
import { toast } from 'sonner';
import { Activity, Mail } from 'lucide-react';
import { authAPI } from '../lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authAPI.forgotPassword({ email: email.trim().toLowerCase() });
      setSent(true);
      toast.success('Check your email');
      // Always show the server's generic message (never a reset token)
      if (data?.message) {
        // kept for accessibility; UI uses fixed copy below
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not start password reset');
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
          <p className="text-sm text-muted-foreground">Reset your password</p>
        </div>

        {!sent ? (
          <form onSubmit={handleSubmit} className="space-y-5" data-testid="forgot-password-form">
            <div>
              <label className="metric-label block mb-2">Email Address</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="engineer@company.com"
                required
                data-testid="forgot-email-input"
                className="h-10"
              />
            </div>

            <Button
              type="submit"
              className="w-full h-10 font-medium"
              disabled={loading}
              data-testid="forgot-submit-button"
            >
              {loading ? 'Sending...' : 'Send reset link'}
            </Button>
          </form>
        ) : (
          <div className="space-y-4 text-center" data-testid="forgot-password-result">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
              <Mail className="w-6 h-6 text-primary" />
            </div>
            <p className="text-sm text-muted-foreground">
              If an account exists for <strong>{email}</strong>, we sent a password reset link.
              Check your inbox and spam folder. The link expires in 1 hour.
            </p>
            <Button
              type="button"
              variant="outline"
              className="w-full h-10"
              onClick={() => setSent(false)}
            >
              Use a different email
            </Button>
          </div>
        )}

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            Remembered your password?{' '}
            <Link to="/login" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}

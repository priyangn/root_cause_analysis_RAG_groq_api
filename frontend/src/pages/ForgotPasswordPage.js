import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';
import { toast } from 'sonner';
import { Activity } from 'lucide-react';
import { authAPI } from '../lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [resetUrl, setResetUrl] = useState('');
  const [doneMessage, setDoneMessage] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResetUrl('');
    setDoneMessage('');
    try {
      const { data } = await authAPI.forgotPassword({ email: email.trim().toLowerCase() });
      setDoneMessage(data.message);
      if (data.reset_url) {
        setResetUrl(data.reset_url);
      }
      toast.success('Reset instructions ready');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not start password reset');
    } finally {
      setLoading(false);
    }
  };

  const openResetLink = () => {
    if (!resetUrl) return;
    try {
      const url = new URL(resetUrl);
      navigate(`${url.pathname}${url.search}`);
    } catch {
      window.location.href = resetUrl;
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

        {!doneMessage ? (
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
          <div className="space-y-4" data-testid="forgot-password-result">
            <p className="text-sm text-muted-foreground">{doneMessage}</p>
            {resetUrl && (
              <Button
                type="button"
                className="w-full h-10 font-medium"
                onClick={openResetLink}
                data-testid="forgot-open-reset-link"
              >
                Continue to reset password
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              className="w-full h-10"
              onClick={() => {
                setDoneMessage('');
                setResetUrl('');
              }}
            >
              Try another email
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

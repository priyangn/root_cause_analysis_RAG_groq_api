import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';
import { toast } from 'sonner';
import { Activity, ArrowLeft } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [step, setStep] = useState(1); // 1: request token, 2: reset password
  const navigate = useNavigate();

  const handleRequestReset = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${BACKEND_URL}/api/auth/forgot-password`, { email });
      
      if (response.data.reset_token) {
        // Development mode: show token
        setResetToken(response.data.reset_token);
        toast.success('Reset token generated! Copy it from below.');
        setStep(2);
      } else {
        toast.success(response.data.message);
        setStep(2);
      }
    } catch (error) {
      toast.error('Failed to process request');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${BACKEND_URL}/api/auth/reset-password`, {
        token: resetToken,
        new_password: newPassword
      });
      
      toast.success('Password reset successful! Please login.');
      navigate('/login');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Password reset failed');
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
          <p className="text-sm text-muted-foreground">Password Reset</p>
        </div>

        {step === 1 ? (
          <form onSubmit={handleRequestReset} className="space-y-5">
            <div>
              <label className="metric-label block mb-2">Email Address</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="engineer@company.com"
                required
                className="h-10"
              />
              <p className="text-xs text-muted-foreground mt-2">
                Enter your email to receive a password reset token
              </p>
            </div>

            <Button 
              type="submit" 
              className="w-full h-10 font-medium" 
              disabled={loading}
            >
              {loading ? 'Processing...' : 'Request Reset Token'}
            </Button>
          </form>
        ) : (
          <form onSubmit={handleResetPassword} className="space-y-5">
            <div>
              <label className="metric-label block mb-2">Reset Token</label>
              <Input
                type="text"
                value={resetToken}
                onChange={(e) => setResetToken(e.target.value)}
                placeholder="Paste your reset token here"
                required
                className="h-10 font-mono text-xs"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Copy the token from above or from your email
              </p>
            </div>

            <div>
              <label className="metric-label block mb-2">New Password</label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
                required
                className="h-10"
              />
            </div>

            <Button 
              type="submit" 
              className="w-full h-10 font-medium" 
              disabled={loading}
            >
              {loading ? 'Resetting...' : 'Reset Password'}
            </Button>
          </form>
        )}

        <div className="mt-6 text-center">
          <Link to="/login" className="text-sm text-primary hover:underline font-medium inline-flex items-center gap-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Login
          </Link>
        </div>
      </Card>
    </div>
  );
}

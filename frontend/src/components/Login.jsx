
import React from 'react';
import { GoogleLogin, GoogleOAuthProvider } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BrainCircuit } from "lucide-react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "154618380883-hlmnd78sufsgvrmvk39ht872brk4o32r.apps.googleusercontent.com";

export default function Login() {
    const { handleLoginSuccess } = useAuth();
    const [error, setError] = React.useState('');
    const [isLoading, setIsLoading] = React.useState(false);

    const onSuccess = async (credentialResponse) => {
        try {
            setIsLoading(true);
            setError(''); // Clear previous errors

            if (!credentialResponse.credential) {
                setError('No credential received from Google');
                setIsLoading(false);
                return;
            }

            // Verify with backend
            const data = await api.login(credentialResponse.credential);
            handleLoginSuccess(data);
        } catch (err) {
            console.error('Login error:', err);
            setError('Failed to log in with server');
            setIsLoading(false);
        }
    };

    return (
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
            <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
                <Card className="w-full max-w-md shadow-lg border-primary/20 bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
                    <CardHeader className="text-center space-y-4 pb-8">
                        <div className="mx-auto bg-primary/10 p-4 rounded-full w-fit">
                            <BrainCircuit className="h-10 w-10 text-primary" />
                        </div>
                        <div className="space-y-2">
                            <CardTitle className="text-2xl font-bold">LLM Council</CardTitle>
                            <CardDescription>Enter the boardroom to consult with AI experts.</CardDescription>
                        </div>
                    </CardHeader>
                    <CardContent className="flex flex-col items-center gap-4">
                        <div className="w-full flex justify-center py-4 relative" aria-busy={isLoading}>
                            {isLoading ? (
                                <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-r-transparent" />
                                    <span>Verifying credentials...</span>
                                </div>
                            ) : (
                                <GoogleLogin
                                    onSuccess={onSuccess}
                                    onError={() => setError('Login Failed')}
                                    useOneTap
                                    theme="filled_black"
                                    shape="pill"
                                />
                            )}
                        </div>
                        {error && (
                            <div className="text-sm text-destructive bg-destructive/10 px-4 py-2 rounded-md w-full text-center">
                                {error}
                            </div>
                        )}
                        <p className="text-xs text-center text-muted-foreground mt-4 max-w-xs">
                            By continuing, you agree to the Terms of Service and Privacy Policy.
                        </p>
                    </CardContent>
                </Card>
            </div>
        </GoogleOAuthProvider>
    );
}

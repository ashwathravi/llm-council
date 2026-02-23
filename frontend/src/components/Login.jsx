
import React from 'react';
import { GoogleLogin, GoogleOAuthProvider } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContextDefinition';
import { api } from '../api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BrainCircuit } from "lucide-react";

const BUILD_GOOGLE_CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID || '').trim();

export default function Login() {
    const { handleLoginSuccess } = useAuth();
    const [error, setError] = React.useState('');
    const [isLoading, setIsLoading] = React.useState(false);
    const [googleClientId, setGoogleClientId] = React.useState(BUILD_GOOGLE_CLIENT_ID);
    const [isConfigLoading, setIsConfigLoading] = React.useState(!BUILD_GOOGLE_CLIENT_ID);

    React.useEffect(() => {
        let isMounted = true;

        if (BUILD_GOOGLE_CLIENT_ID) {
            setIsConfigLoading(false);
            return () => {
                isMounted = false;
            };
        }

        const loadAuthConfig = async () => {
            try {
                const data = await api.getAuthConfig();
                const runtimeClientId = (data?.google_client_id || '').trim();
                if (isMounted && runtimeClientId) {
                    setGoogleClientId(runtimeClientId);
                }
            } catch (err) {
                console.error('Failed to load auth config:', err);
            } finally {
                if (isMounted) {
                    setIsConfigLoading(false);
                }
            }
        };

        loadAuthConfig();

        return () => {
            isMounted = false;
        };
    }, []);

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

    if (isConfigLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
                <Card className="w-full max-w-md shadow-lg border-primary/20 bg-card/95 backdrop-blur">
                    <CardHeader className="text-center space-y-4 pb-8">
                        <div className="mx-auto bg-primary/10 p-4 rounded-full w-fit">
                            <BrainCircuit className="h-10 w-10 text-primary" />
                        </div>
                        <div className="space-y-2">
                            <CardTitle className="text-2xl font-bold">Loading</CardTitle>
                            <CardDescription>
                                Fetching sign-in configuration...
                            </CardDescription>
                        </div>
                    </CardHeader>
                </Card>
            </div>
        );
    }

    if (!googleClientId) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
                <Card className="w-full max-w-md shadow-lg border-destructive/20 bg-card/95 backdrop-blur">
                    <CardHeader className="text-center space-y-4 pb-8">
                        <div className="mx-auto bg-destructive/10 p-4 rounded-full w-fit">
                            <BrainCircuit className="h-10 w-10 text-destructive" />
                        </div>
                        <div className="space-y-2">
                            <CardTitle className="text-2xl font-bold text-destructive">Configuration Error</CardTitle>
                            <CardDescription>
                                Google Sign-In is not configured.
                            </CardDescription>
                        </div>
                    </CardHeader>
                    <CardContent className="text-center text-sm text-muted-foreground">
                        Please set GOOGLE_CLIENT_ID (backend) or VITE_GOOGLE_CLIENT_ID (frontend build-time) in your environment variables.
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <GoogleOAuthProvider clientId={googleClientId}>
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

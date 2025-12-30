import React from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import './Login.css';

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
        <div className="login-container">
            <div className="login-card">
                <h1>LLM Council</h1>
                <p>Sign in to consult the council</p>

                <div className="google-btn-container" aria-busy={isLoading}>
                    {isLoading ? (
                        <div className="loading-state">
                            <div className="spinner" aria-hidden="true"></div>
                            <span>Verifying credentials...</span>
                        </div>
                    ) : (
                        <GoogleLogin
                            onSuccess={onSuccess}
                            onError={() => setError('Login Failed')}
                            useOneTap
                        />
                    )}
                </div>

                {error && <div className="error-message" role="alert">{error}</div>}
            </div>
        </div>
    );
}

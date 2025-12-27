import React from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../contexts/authContext';
import { api } from '../api';
import './Login.css';

export default function Login() {
    const { handleLoginSuccess } = useAuth();
    const [error, setError] = React.useState('');

    const onSuccess = async (credentialResponse) => {
        try {
            if (!credentialResponse.credential) {
                setError('No credential received from Google');
                return;
            }

            // Verify with backend
            const data = await api.login(credentialResponse.credential);
            handleLoginSuccess(data);
        } catch (err) {
            console.error('Login error:', err);
            setError('Failed to log in with server');
        }
    };

    return (
        <div className="login-container">
            <div className="login-card">
                <h1>LLM Council</h1>
                <p>Sign in to consult the council</p>

                <div className="google-btn-container">
                    <GoogleLogin
                        onSuccess={onSuccess}
                        onError={() => setError('Login Failed')}
                        useOneTap
                    />
                </div>

                {error && <div className="error-message">{error}</div>}
            </div>
        </div>
    );
}

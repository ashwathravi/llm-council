import React, { createContext, useContext, useState, useEffect } from 'react';
import { googleLogout, useGoogleLogin } from '@react-oauth/google';
import { api } from '../api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(localStorage.getItem('auth_token'));
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // If we have a token, we consider the user logged in for now,
        // but in a real app we might validate it or fetch user profile on load.
        // For simplicity, we just rely on the presence of the token.
        if (token) {
            // Ideally we would decode the token or fetch /me, but we stored user in localStorage too?
            // Let's store user info in localStorage for persistence across reloads
            const storedUser = localStorage.getItem('auth_user');
            if (storedUser) {
                setUser(JSON.parse(storedUser));
            }
        }
        setIsLoading(false);
    }, [token]);

    const login = useGoogleLogin({
        onSuccess: async (tokenResponse) => {
            try {
                // Exchange Google ID token for session JWT
                // Note: useGoogleLogin with default flow gives 'access_token' (OAuth2). 
                // But for ID token verification we usually want the 'credential' from the GIS button 
                // OR we can use the 'id_token' flow if configured.
                // However, standard flow is to send 'access_token' to backend which then calls Google UserInfo,
                // OR send 'id_token'.
                // Let's stick to the simplest: Use the GoogleLogin component (Button) which gives a credential (id_token).
                // But useGoogleLogin hook gives an access_token by default unless flow: 'auth-code'.
                // Wait, for @react-oauth/google, the <GoogleLogin> component returns a credential (JWT id_token).
                // The useGoogleLogin hook returns a code or access_token.
                // I will use `GoogleLogin` component in Login.jsx instead of the hook here for the initial sign-in.
                // So this `login` helper might not be needed if we use the component directly.
            } catch (error) {
                console.error('Login failed:', error);
            }
        },
        onError: error => console.log('Login Failed:', error)
    });

    const handleLoginSuccess = (sessionData) => {
        setToken(sessionData.access_token);
        setUser(sessionData.user);
        localStorage.setItem('auth_token', sessionData.access_token);
        localStorage.setItem('auth_user', JSON.stringify(sessionData.user));
    };

    const logout = () => {
        googleLogout();
        setToken(null);
        setUser(null);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
    };

    return (
        <AuthContext.Provider value={{ user, token, handleLoginSuccess, logout, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);

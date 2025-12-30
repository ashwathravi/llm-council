import React, { useState, createContext, useContext } from 'react';
import { googleLogout } from '@react-oauth/google';

export const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(() => localStorage.getItem('auth_token'));
    const [user, setUser] = useState(() => {
        return { name: "Test User", email: "test@example.com", id: "mock-123" };
    });
    const isLoading = false;

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

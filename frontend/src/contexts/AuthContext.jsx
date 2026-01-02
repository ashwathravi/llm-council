import React, { useState, createContext, useContext } from 'react';

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
        // Dynamically import googleLogout to avoid bundling @react-oauth/google in main chunk
        import('@react-oauth/google').then(({ googleLogout }) => {
            googleLogout();
        }).catch(err => console.error("Failed to load googleLogout", err));

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

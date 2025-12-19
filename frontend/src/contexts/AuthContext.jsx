import React, { createContext, useContext, useState, useEffect } from 'react';
import { googleLogout } from '@react-oauth/google';

const AuthContext = createContext(null);

export const useAuth = () => {
    return useContext(AuthContext);
}

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(localStorage.getItem('auth_token'));
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const initAuth = () => {
            if (token) {
                const storedUser = localStorage.getItem('auth_user');
                if (storedUser) {
                    setUser(JSON.parse(storedUser));
                }
            }
            setIsLoading(false);
        };
        initAuth();
    }, [token]);

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


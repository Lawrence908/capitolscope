import React, { createContext, useContext, useReducer, useEffect } from 'react';
import type { ReactNode } from 'react';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

// Types
export interface User {
  id: string;  // Changed from number to string to handle UUIDs
  email: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  display_name: string;
  avatar_url?: string;
  bio?: string;
  location?: string;
  website_url?: string;
  status: string;
  is_verified: boolean;
  is_active: boolean;
  last_login_at?: string;
  subscription_tier: string;
  subscription_status?: string;
  is_premium: boolean;
  is_public_profile: boolean;
  show_portfolio: boolean;
  show_trading_activity: boolean;
  created_at: string;
  updated_at?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  username?: string;
  terms_accepted: boolean;
}

// Action types
type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; tokens: AuthTokens } }
  | { type: 'LOGIN_FAILURE'; payload: string }
  | { type: 'LOGOUT' }
  | { type: 'CLEAR_ERROR' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'UPDATE_USER'; payload: User };

// Initial state
const initialState: AuthState = {
  user: null,
  tokens: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
};

// Reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN_START':
      return {
        ...state,
        isLoading: true,
        error: null,
      };
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        tokens: action.payload.tokens,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      };
    case 'LOGIN_FAILURE':
      return {
        ...state,
        user: null,
        tokens: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload,
      };
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        tokens: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      };
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };
    case 'UPDATE_USER':
      return {
        ...state,
        user: action.payload,
      };
    default:
      return state;
  }
}

// Context
interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider component
interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Check for existing tokens on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const tokens = getStoredTokens();
        if (tokens) {
          // Validate token and get user info
          const user = await validateToken(tokens.access_token);
          if (user) {
            dispatch({
              type: 'LOGIN_SUCCESS',
              payload: { user, tokens },
            });
          } else {
            // Invalid token, clear storage
            clearStoredTokens();
          }
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        clearStoredTokens();
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    checkAuth();
  }, []);

  // Token storage helpers
  const getStoredTokens = (): AuthTokens | null => {
    try {
      const stored = localStorage.getItem('capitolscope_tokens');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  };

  const setStoredTokens = (tokens: AuthTokens) => {
    localStorage.setItem('capitolscope_tokens', JSON.stringify(tokens));
  };

  const clearStoredTokens = () => {
    localStorage.removeItem('capitolscope_tokens');
  };

  // API helpers
  const validateToken = async (token: string): Promise<User | null> => {
    try {
      console.log('Validating token:', token.substring(0, 20) + '...');
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      console.log('Token validation response:', response.status, response.statusText);
      
      if (response.ok) {
        const data = await response.json();
        console.log('User data from token validation:', data);
        return data.data; // The user data is directly in data.data, not data.data.user
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error('Token validation failed:', response.status, errorData);
      }
      return null;
    } catch (error) {
      console.error('Token validation error:', error);
      return null;
    }
  };

  // Auth methods
  const login = async (credentials: LoginCredentials): Promise<void> => {
    dispatch({ type: 'LOGIN_START' });

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      const data = await response.json();

      if (response.ok && data.data) {
        const { user, ...tokens } = data.data;
        
        // Store tokens
        setStoredTokens(tokens);
        
        console.log('Login successful, user data:', user);
        
        dispatch({
          type: 'LOGIN_SUCCESS',
          payload: { user, tokens },
        });
      } else {
        const errorMessage = data.error?.message || data.error || 'Login failed';
        dispatch({ type: 'LOGIN_FAILURE', payload: errorMessage });
      }
    } catch (error) {
      dispatch({
        type: 'LOGIN_FAILURE',
        payload: 'Network error. Please try again.',
      });
    }
  };

  const register = async (data: RegisterData): Promise<void> => {
    dispatch({ type: 'LOGIN_START' });

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      const responseData = await response.json();

      if (response.ok && responseData.data) {
        const { user, ...tokens } = responseData.data;
        
        // Store tokens
        setStoredTokens(tokens);
        
        console.log('Registration successful, user data:', user);
        
        dispatch({
          type: 'LOGIN_SUCCESS',
          payload: { user, tokens },
        });
      } else {
        const errorMessage = responseData.error?.message || responseData.error || 'Registration failed';
        dispatch({ type: 'LOGIN_FAILURE', payload: errorMessage });
      }
    } catch (error) {
      dispatch({
        type: 'LOGIN_FAILURE',
        payload: 'Network error. Please try again.',
      });
    }
  };

  const logout = () => {
    clearStoredTokens();
    dispatch({ type: 'LOGOUT' });
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  const updateUser = (user: User) => {
    dispatch({ type: 'UPDATE_USER', payload: user });
  };

  const value: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    clearError,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Hook
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}; 
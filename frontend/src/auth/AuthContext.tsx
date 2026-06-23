import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type PropsWithChildren,
} from "react";

import { getCurrentUser, login } from "../api/auth";
import type { UserRead } from "../api/types";
import {
  clearStoredAccessToken,
  getStoredAccessToken,
  storeAccessToken,
} from "./session";

interface AuthContextValue {
  user: UserRead | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  loginWithCredentials: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<UserRead | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    clearStoredAccessToken();
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    let isCurrent = true;
    const storedToken = getStoredAccessToken();

    if (!storedToken) {
      setIsLoading(false);
      return () => {
        isCurrent = false;
      };
    }

    const tokenToRestore = storedToken;

    async function restoreSession() {
      try {
        const currentUser = await getCurrentUser(tokenToRestore);
        if (isCurrent && getStoredAccessToken() === tokenToRestore) {
          setToken(tokenToRestore);
          setUser(currentUser);
        }
      } catch {
        if (isCurrent && getStoredAccessToken() === tokenToRestore) {
          clearStoredAccessToken();
          setToken(null);
          setUser(null);
        }
      } finally {
        if (isCurrent) {
          setIsLoading(false);
        }
      }
    }

    void restoreSession();

    return () => {
      isCurrent = false;
    };
  }, []);

  const loginWithCredentials = useCallback(
    async (email: string, password: string) => {
      const response = await login({ email, password });
      storeAccessToken(response.access_token);
      setToken(response.access_token);
      setUser(response.user);
    },
    [],
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: Boolean(user && token),
        loginWithCredentials,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }

  return context;
}

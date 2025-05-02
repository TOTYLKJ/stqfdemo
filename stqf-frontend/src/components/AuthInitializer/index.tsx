import React, { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { getCurrentUser } from '@/api/auth';
import { setAuth } from '@/store/slices/authSlice';

const AuthInitializer: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const dispatch = useDispatch();

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('token');
      const refresh_token = localStorage.getItem('refresh_token');

      if (token) {
        try {
          const user = await getCurrentUser();
          dispatch(
            setAuth({
              user,
              token,
              refresh_token: refresh_token || undefined,
            })
          );
        } catch (error) {
          // If retrieving user information fails, clear locally stored tokens
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
        }
      }
    };

    initializeAuth();
  }, [dispatch]);

  return <>{children}</>;
};

export default AuthInitializer;

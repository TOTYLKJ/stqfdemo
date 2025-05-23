import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { RouterProvider } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import enUS from 'antd/locale/en_US';
import router from './routes';
import { store } from './store';
import AuthInitializer from './components/AuthInitializer';
import './index.css';

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);

root.render(
  <React.StrictMode>
    <Provider store={store}>
      <ConfigProvider locale={enUS}>
        <AuthInitializer>
          <RouterProvider router={router} />
        </AuthInitializer>
      </ConfigProvider>
    </Provider>
  </React.StrictMode>
);

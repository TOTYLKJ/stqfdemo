import React from 'react';
import { DatabaseOutlined } from '@ant-design/icons';
import './style.css';

const Logo: React.FC = () => {
  return (
    <div className='logo-container'>
      <DatabaseOutlined className='logo-icon' />
      <div className='logo-text'>
        <div className='logo-title'>GKO Trajectory Query System</div>
        <div className='logo-subtitle'>
          Privacy-preserving semantic trajectory query system based on GKO tree technology
        </div>
      </div>
    </div>
  );
};

export default Logo;

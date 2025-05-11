import React from 'react';
import { DatabaseOutlined } from '@ant-design/icons';
import './style.css';

const Logo: React.FC = () => {
  return (
    <div className='logo-container'>
      <DatabaseOutlined className='logo-icon' />
      <div className='logo-text'>
        <div className='logo-title'>STQCF</div>
        <div className='logo-subtitle'>
          A System for Privacy-Preserving Semantic Trajectory Query Based on Cloud-Fog Collaboration
        </div>
      </div>
    </div>
  );
};

export default Logo;

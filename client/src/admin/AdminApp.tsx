import { useState } from 'react';
import AdminLayout from './AdminLayout';
import AdminDashboard from './AdminDashboard';
import ChannelManager from './ChannelManager';
import PageManager from './PageManager';
import Settings from './Settings';

export default function AdminApp() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <AdminDashboard />;
      case 'channels':
        return <ChannelManager />;
      case 'pages':
        return <PageManager />;
      case 'settings':
        return <Settings onNavigate={setActiveTab} />;
      default:
        return <AdminDashboard />;
    }
  };

  return (
    <AdminLayout activeTab={activeTab} onTabChange={setActiveTab}>
      {renderContent()}
    </AdminLayout>
  );
}

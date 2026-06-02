import { Navigate } from 'react-router-dom';

interface AdminLayoutProps {
  children: React.ReactNode;
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: 'dashboard', label: 'Home', icon: '🏠' },
  { id: 'channels', label: 'Channels', icon: '📺' },
  { id: 'pages', label: 'Pages', icon: '📄' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
];

export default function AdminLayout({ children, activeTab, onTabChange }: AdminLayoutProps) {
  const token = localStorage.getItem('exhibitos_token');
  if (!token) return <Navigate to="/admin/login" replace />;

  return (
    <div className="min-h-screen bg-gray-50 pb-16 md:pb-0 md:pl-56">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex fixed left-0 top-0 bottom-0 w-56 flex-col bg-[#0B1F3A] text-white z-20">
        <div className="p-4 border-b border-white/10">
          <p className="text-[#C9960C] font-bold text-lg">ExhibitOS</p>
          <p className="text-white/50 text-xs mt-1">VCF Museum @ InfoAge</p>
        </div>
        <nav className="flex-1 p-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`w-full text-left px-4 py-3 rounded-lg mb-1 transition-colors ${
                activeTab === tab.id
                  ? 'bg-white/10 text-[#F2C94C]'
                  : 'text-white/70 hover:bg-white/5 hover:text-white'
              }`}
            >
              <span className="mr-3">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
        <div className="p-4 border-t border-white/10">
          <button
            onClick={() => {
              localStorage.removeItem('exhibitos_token');
              window.location.href = '/admin/login';
            }}
            className="text-white/50 text-sm hover:text-white"
          >
            Log out
          </button>
        </div>
      </aside>

      {/* Mobile bottom tabs */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex z-20">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex-1 py-3 text-center text-xs transition-colors ${
              activeTab === tab.id
                ? 'text-[#0B1F3A] font-bold'
                : 'text-gray-400'
            }`}
          >
            <span className="text-lg block">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="max-w-4xl mx-auto p-4 md:p-8">
        {children}
      </main>
    </div>
  );
}

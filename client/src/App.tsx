import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ChannelDisplay from './display/ChannelDisplay';
import ExhibitCard from './display/ExhibitCard';
import Login from './admin/Login';
import ChangePassword from './admin/ChangePassword';
import AdminApp from './admin/AdminApp';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Display routes — used by Pi kiosk */}
        <Route path="/display/:slug" element={<ChannelDisplay />} />

        {/* Public interpretive card — QR / phone deep-dive target */}
        <Route path="/exhibit/:slug" element={<ExhibitCard />} />

        {/* Admin routes */}
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin/change-password" element={<ChangePassword />} />
        <Route path="/admin" element={<AdminApp />} />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/display/lobby" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

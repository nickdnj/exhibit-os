import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ChannelDisplay from './display/ChannelDisplay';
import ExhibitCard from './display/ExhibitCard';
import ExhibitShow from './display/ExhibitShow';
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

        {/* Rotating kiosk "show" of the whole collection, chronological */}
        <Route path="/show" element={<ExhibitShow />} />

        {/* Admin routes */}
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin/change-password" element={<ChangePassword />} />
        <Route path="/admin" element={<AdminApp />} />

        {/* Default redirect — lead with the museum's own collection */}
        <Route path="/" element={<Navigate to="/show" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

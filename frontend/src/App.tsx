import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { SpecialsV2 } from './pages/SpecialsV2';
import { ComparePage } from './pages/ComparePage';
import { StaplesPage } from './pages/StaplesPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<SpecialsV2 />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="staples" element={<StaplesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

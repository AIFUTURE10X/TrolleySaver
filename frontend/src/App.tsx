import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { SpecialsV2 } from './pages/SpecialsV2';
import { ComparePage } from './pages/ComparePage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<SpecialsV2 />} />
          <Route path="compare" element={<ComparePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

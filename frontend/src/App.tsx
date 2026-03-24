import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Collections from './pages/Collections';
import DocumentViewer from './pages/DocumentViewer';
import Search from './pages/Search';
import Knowledge from './pages/Knowledge';
import Analytics from './pages/Analytics';
import MapPage from './pages/Map';
import Settings from './pages/Settings';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-ivory">
        <nav className="border-b border-parchment bg-white/80 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 flex items-center h-14 gap-8">
            <h1 className="font-heading text-xl font-bold text-slate-ink tracking-tight">
              Luftarchiv
            </h1>
            <div className="flex gap-6 text-sm font-body">
              {[
                ['/', 'Collections'],
                ['/search', 'Search'],
                ['/knowledge', 'Knowledge'],
                ['/analytics', 'Analytics'],
                ['/map', 'Map'],
                ['/settings', 'Settings'],
              ].map(([path, label]) => (
                <NavLink
                  key={path}
                  to={path}
                  end={path === '/'}
                  className={({ isActive }) =>
                    `py-1 border-b-2 transition-colors ${
                      isActive
                        ? 'border-archive-amber text-archive-amber'
                        : 'border-transparent text-slate-ink/60 hover:text-slate-ink'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Collections />} />
            <Route path="/viewer/:collectionId" element={<DocumentViewer />} />
            <Route path="/viewer/:collectionId/:pageNumber" element={<DocumentViewer />} />
            <Route path="/search" element={<Search />} />
            <Route path="/knowledge" element={<Knowledge />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
